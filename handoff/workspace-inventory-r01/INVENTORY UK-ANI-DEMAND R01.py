"""ONE NEW ForecastMaster_GM_Setup PySpark cell. Metadata reads only.
No business rows, amount queries, refresh, definition update or OneLake writes.
Return the complete JSON privately in this chat, never in the public Git repo.
Full DAX is metadata but can contain company logic/literals. Review before sharing.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
import time
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlsplit
from uuid import UUID

WORKSPACE = "f5cb5742-9a7c-4337-a4c0-952706dddf0b"
WORKSPACE_NAME = "UK-ANI-Demand"
BASE = "/v1/workspaces/" + WORKSPACE
DATA_ITEMS = {"Lakehouse", "Warehouse", "MirroredDatabase", "MirroredWarehouse", "SQLDatabase"}
OTHER_ENGINES = {"KQLDatabase", "Datamart", "MirroredAzureDatabricksCatalog", "SnowflakeDatabase"}
NO_RETRY = {"total": 0, "allowed_methods": ["GET"], "raise_on_status": False}


class InventoryStopped(RuntimeError):
    def __init__(self, code, status=None):
        self.code, self.status = code, status


def require(ok, code):
    if not ok:
        raise InventoryStopped(code)


def identifier(value):
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise InventoryStopped("INVALID_OBJECT_ID") from None


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def pick(value, names):
    return {key: value[key] for key in names.split() if key in value}


def failure(exc):
    result = {"Reason": exc.code if isinstance(exc, InventoryStopped) else "READ_UNAVAILABLE",
              "ExceptionFamily": type(exc).__name__}
    if isinstance(exc, InventoryStopped) and exc.status is not None:
        result["HTTPStatus"] = exc.status
    # Never stringify an SDK exception: it may embed definitions, URLs or headers.
    return result


def checked(response, expected=(200,)):
    if response.status_code not in expected:
        raise InventoryStopped("HTTP_READ_UNAVAILABLE", int(response.status_code))
    return response


def read_step(target, action):
    start = time.monotonic()
    try:
        action()
        target["Status"] = "READ_COMPLETED"
    except Exception as exc:
        target.update(Status="READ_FAILED", Failure=failure(exc))
    target["ElapsedMs"] = round((time.monotonic() - start) * 1000)
    return target["Status"] == "READ_COMPLETED"


def page_token(body, path, host, continuation_key):
    token = body.get(continuation_key)
    if token:
        require(isinstance(token, str), "PAGINATION_TOKEN_INVALID")
        return token
    uri = body.get("continuationUri")
    if not uri:
        return None
    # Rebuild the next request on the pinned host/path. Never follow a returned URL.
    parsed = urlsplit(uri)
    require(not parsed.username and not parsed.password and not parsed.fragment,
            "PAGINATION_LOCATION_INVALID")
    require((parsed.scheme == "https" and parsed.hostname == host and parsed.port in (None, 443))
            or (not parsed.scheme and not parsed.netloc), "PAGINATION_LOCATION_INVALID")
    require(parsed.path == path, "PAGINATION_SCOPE_CHANGED")
    values = parse_qs(parsed.query).get("continuationToken", [])
    require(len(values) == 1 and bool(values[0]), "PAGINATION_TOKEN_MISSING")
    return values[0]


def pages(get, path, member, target, host="api.fabric.microsoft.com", params=None,
          continuation_key="continuationToken", continuation_param="continuationToken"):
    """Append each successful page immediately; a later failure retains earlier pages."""
    params = dict(params or {})
    seen = set()
    for _ in range(1000):
        query = "?" + urlencode(params) if params else ""
        body = checked(get(path + query)).json()
        require(isinstance(body.get(member), list), "EXPECTED_METADATA_LIST_MISSING")
        target.extend(body[member])
        token = page_token(body, path, host, continuation_key)
        if token is None:
            return
        require(token not in seen, "PAGINATION_LOOP")
        seen.add(token)
        params[continuation_param] = token
    raise InventoryStopped("PAGINATION_LIMIT_REACHED")


def operation_path(headers):
    headers = {key.lower(): value for key, value in headers.items()}
    if headers.get("x-ms-operation-id"):
        return "/v1/operations/" + identifier(headers["x-ms-operation-id"])
    parsed = urlsplit(headers.get("location", ""))
    require(not parsed.query and not parsed.fragment and not parsed.username and not parsed.password,
            "OPERATION_LOCATION_INVALID")
    require((parsed.scheme == "https" and parsed.hostname == "api.fabric.microsoft.com"
             and parsed.port in (None, 443)) or (not parsed.scheme and not parsed.netloc),
            "OPERATION_LOCATION_INVALID")
    for prefix in ("/v1/operations/", "/operations/"):
        if parsed.path.startswith(prefix):
            return "/v1/operations/" + identifier(parsed.path[len(prefix):])
    raise InventoryStopped("OPERATION_HEADER_UNAVAILABLE")


def definition(client, model_id, sleep=time.sleep, clock=time.monotonic):
    # This POST only retrieves metadata. It never invokes updateDefinition or processing.
    path = BASE + "/semanticModels/" + identifier(model_id) + "/getDefinition?format=TMSL"
    response = checked(client.post(path), (200, 202))
    if response.status_code == 202:
        operation = operation_path(response.headers)
        deadline = clock() + 360
        polls = 0
        while clock() < deadline:
            try:
                delay = int(response.headers.get("Retry-After", "5"))
            except (ValueError, TypeError):
                delay = 5
            sleep(min(30, max(1, delay)))
            response = checked(client.get(operation))
            state = response.json().get("status")
            if state == "Succeeded":
                response = checked(client.get(operation + "/result"))
                break
            require(state in {"NotStarted", "Running", "Undefined"}, "DEFINITION_OPERATION_NOT_SUCCEEDED")
            polls += 1
            if polls == 1 or polls % 6 == 0:
                print("Read-only inventory: model definition still being retrieved.", flush=True)
        else:
            raise InventoryStopped("DEFINITION_READ_TIMEOUT")
    parts = response.json()["definition"]["parts"]
    matches = [part for part in parts if part.get("path") == "model.bim"]
    require(len(matches) == 1 and matches[0].get("payloadType") == "InlineBase64",
            "EXPECTED_ONE_INLINE_TMSL_MODEL")
    database = json.loads(base64.b64decode(matches[0]["payload"], validate=True).decode("utf-8-sig"))
    require(isinstance(database.get("model", {}).get("tables"), list), "MODEL_TABLES_MISSING")
    return database


def semantic_catalog(database):
    """Allowlisted logical metadata, with full DAX but no M/SQL/connection payloads."""
    model = database["model"]
    result = {"DefinitionSHA256": digest(database),
              "Properties": pick(model, "culture sourceQueryCulture defaultMode discourageImplicitMeasures"),
              "CompatibilityLevel": database.get("compatibilityLevel"), "Tables": [],
              "Relationships": [], "Roles": [], "NamedExpressions": []}
    for table in model["tables"]:
        item = pick(table, "name isHidden description dataCategory")
        item["Columns"] = []
        for column in table.get("columns", []):
            item["Columns"].append(pick(column, "name dataType type sourceColumn expression formatString "
                "isHidden isKey isUnique isNullable summarizeBy sortByColumn displayFolder dataCategory "
                "isDefaultLabel isDefaultImage isAvailableInMdx"))
        item["Measures"] = []
        for measure in table.get("measures", []):
            selected = pick(measure, "name expression formatString isHidden displayFolder description dataCategory")
            if "formatStringDefinition" in measure:
                selected["formatStringDefinition"] = pick(measure["formatStringDefinition"], "expression")
            if "detailRowsDefinition" in measure:
                selected["detailRowsDefinition"] = pick(measure["detailRowsDefinition"], "expression")
            if "kpi" in measure:
                selected["kpi"] = pick(measure["kpi"], "targetExpression targetFormatString "
                    "statusExpression statusGraphic trendExpression trendGraphic")
            item["Measures"].append(selected)
        item["Hierarchies"] = []
        for hierarchy in table.get("hierarchies", []):
            entry = pick(hierarchy, "name isHidden displayFolder")
            entry["Levels"] = [pick(level, "name column ordinal") for level in hierarchy.get("levels", [])]
            item["Hierarchies"].append(entry)
        item["Partitions"] = []
        for partition in table.get("partitions", []):
            source = partition.get("source", {})
            item["Partitions"].append({**pick(partition, "name mode"),
                "SourceBinding": pick(source, "type entityName schemaName expressionSource dataSource"),
                "SourceExpressionPresent": "expression" in source or "query" in source,
                "SourceSHA256": digest(source)})
        if "calculationGroup" in table:
            group = table["calculationGroup"]
            item["CalculationGroup"] = {**pick(group, "precedence"), "Items": []}
            for calc in group.get("calculationItems", []):
                entry = pick(calc, "name expression ordinal description")
                if "formatStringDefinition" in calc:
                    entry["formatStringDefinition"] = pick(calc["formatStringDefinition"], "expression")
                item["CalculationGroup"]["Items"].append(entry)
        result["Tables"].append(item)
    for relationship in model.get("relationships", []):
        keys = ("name type fromTable fromColumn toTable toColumn fromCardinality toCardinality "
                "isActive crossFilteringBehavior securityFilteringBehavior joinOnDateBehavior "
                "relyOnReferentialIntegrity")
        entry = pick(relationship, keys)
        entry["OtherPropertyNames"] = sorted(set(relationship) - set(keys.split()))
        result["Relationships"].append(entry)
    for role in model.get("roles", []):
        result["Roles"].append({**pick(role, "name modelPermission"),
            "TablePermissions": [{**pick(rule, "name metadataPermission"),
                "FilterExpressionPresent": "filterExpression" in rule}
                for rule in role.get("tablePermissions", [])],
            "MemberCount": len(role.get("members", []))})
    for expression in model.get("expressions", []):
        result["NamedExpressions"].append({**pick(expression, "name kind"), "SHA256": digest(expression)})
    result["Counts"] = {"Tables": len(result["Tables"]),
        "Columns": sum(len(t["Columns"]) for t in result["Tables"]),
        "Measures": sum(len(t["Measures"]) for t in result["Tables"]),
        "Relationships": len(result["Relationships"]), "Roles": len(result["Roles"])}
    return result


def onelake_reader(credentials, session):
    # Existing notebook user identity, storage audience, token held only in memory.
    # No credentials endpoint, token vending, sign-in or permission changes.
    def get(path):
        require(path.startswith("/delta/" + WORKSPACE + "/"), "ONELAKE_SCOPE_CHANGED")
        token = credentials.getToken("storage")
        return session.get("https://onelake.table.fabric.microsoft.com" + path,
            headers={"Authorization": "Bearer " + token}, timeout=(10, 60), allow_redirects=False)
    return get


def onelake_catalog(get, item, output):
    root = "/delta/" + WORKSPACE + "/" + identifier(item["id"]) + "/api/2.1/unity-catalog"
    schemas: list[dict[str, Any]] = []
    output["Schemas"] = []
    listing: dict[str, Any] = {}
    output["SchemaListing"] = listing
    read_step(listing, lambda: pages(get, root + "/schemas", "schemas", schemas,
        host="onelake.table.fabric.microsoft.com", params={"catalog_name": item["id"]},
        continuation_key="next_page_token", continuation_param="page_token"))
    for schema in schemas:
        name = schema["name"]
        catalog_name = schema.get("catalog_name") or item["id"]
        record = {"Name": name, "Tables": []}
        output["Schemas"].append(record)
        def tables_for_schema():
            tables: list[dict[str, Any]] = []
            listing: dict[str, Any] = {}
            record["TableListing"] = listing
            read_step(listing, lambda: pages(get, root + "/tables", "tables", tables,
                    host="onelake.table.fabric.microsoft.com",
                    params={"catalog_name": catalog_name, "schema_name": name},
                    continuation_key="next_page_token", continuation_param="page_token"))
            record["Tables"] = [{"Name": table["name"], "Status": "NOT_READ"} for table in tables]
            for table, entry in zip(tables, record["Tables"]):
                def fields():
                    full = table.get("full_name") or ".".join([catalog_name, name, table["name"]])
                    detail = checked(get(root + "/tables/" + quote(full, safe="") + "?" +
                        urlencode({"catalog_name": catalog_name, "schema_name": name}))).json()
                    require(detail.get("name") == table["name"] and detail.get("schema_name") == name,
                            "TABLE_DETAIL_IDENTITY_CHANGED")
                    columns = detail.get("columns")
                    require(isinstance(columns, list) and bool(columns), "PHYSICAL_COLUMNS_UNAVAILABLE")
                    entry["Properties"] = pick(detail, "table_type data_source_format table_id")
                    entry["Columns"] = [pick(col, "name type_text type_json type_name type_precision "
                        "type_scale position nullable partition_index") for col in columns]
                read_step(entry, fields)
            require(listing["Status"] == "READ_COMPLETED", "TABLE_LISTING_PARTIAL")
        read_step(record, tables_for_schema)
    require(output["SchemaListing"]["Status"] == "READ_COMPLETED" and
            all(s["Status"] == "READ_COMPLETED" and all(t["Status"] == "READ_COMPLETED"
            for t in s["Tables"]) for s in output["Schemas"]), "ONE_OR_MORE_SCHEMAS_OR_FIELDS_UNREAD")


def lakehouse_fallback(client, spark, item, output):
    """Classic Lakehouse only. Spark reads Delta schema, with NO data action."""
    require(spark is not None, "SPARK_SESSION_UNAVAILABLE_FOR_SCHEMA_FALLBACK")
    tables: list[dict[str, Any]] = []
    listing: dict[str, Any] = {}
    output["TableListing"] = listing
    read_step(listing, lambda: pages(client.get, BASE + "/lakehouses/" + identifier(item["id"]) +
        "/tables", "data", tables, params={"maxResults": 100}))
    output["Schemas"] = [{"Name": "UNSCHEMED", "Tables": [
        {"Name": t["name"], "Status": "NOT_READ"} for t in tables]}]
    for table, entry in zip(tables, output["Schemas"][0]["Tables"]):
        def fields():
            require(str(table.get("format", "")).lower() == "delta", "NON_DELTA_SCHEMA_UNAVAILABLE")
            location = table.get("location", "")
            prefix = "abfss://" + WORKSPACE + "@onelake.dfs.fabric.microsoft.com/" + item["id"] + "/Tables/"
            require(location.startswith(prefix) and ".." not in location.split("/"), "TABLE_LOCATION_UNEXPECTED")
            schema = spark.read.format("delta").load(location).schema.jsonValue()
            def clean_type(value):
                if isinstance(value, list):
                    return [clean_type(v) for v in value]
                if isinstance(value, dict):
                    return {k: clean_type(v) for k, v in value.items() if k != "metadata"}
                return value
            entry["Columns"] = clean_type(schema["fields"])
            entry["Properties"] = pick(table, "type format")
        read_step(entry, fields)
    require(listing["Status"] == "READ_COMPLETED" and
            all(t["Status"] == "READ_COMPLETED" for t in output["Schemas"][0]["Tables"]),
            "ONE_OR_MORE_PHYSICAL_FIELDS_UNREAD")
    output["Schemas"][0]["Status"] = "READ_COMPLETED"


def data_catalog(client, lake_get, spark, item):
    result = {"ItemID": item["id"], "Name": item["displayName"], "Type": item["type"], "Attempts": []}
    primary = {"Method": "OneLakeDeltaMetadataAPI"}
    result["Attempts"].append(primary)
    if read_step(primary, lambda: onelake_catalog(lake_get, item, primary)):
        result.update(Status="READ_COMPLETED", Schemas=primary.pop("Schemas"))
    elif item["type"] == "Lakehouse":
        fallback = {"Method": "ClassicLakehouseAPIPlusDeltaSchemaOnly"}
        result["Attempts"].append(fallback)
        if read_step(fallback, lambda: lakehouse_fallback(client, spark, item, fallback)):
            result.update(Status="READ_COMPLETED", Schemas=fallback.pop("Schemas"))
        else:
            result["Status"] = "PARTIAL"
    else:
        result["Status"] = "PARTIAL"
    return result


def item_projection(raw):
    items = [pick(item, "id displayName type workspaceId folderId") for item in raw]
    for item in items:
        identifier(item["id"])
        require(item.get("workspaceId", WORKSPACE) == WORKSPACE, "ITEM_WORKSPACE_CHANGED")
    require(len({i["id"] for i in items}) == len(items), "DUPLICATE_ITEMS_DURING_PAGINATION")
    return sorted(items, key=lambda i: (i["type"], i["displayName"], i["id"]))


def run(client, pbi, lake_get, spark, report=None):
    report = {} if report is None else report
    report.update({"Stage": "UK_ANI_INVENTORY_R01_PARTIAL", "Revision": "R01",
        "StartedUTC": datetime.now(timezone.utc).isoformat(), "WorkspaceID": WORKSPACE,
        "Checks": {}, "WorkspaceItems": [], "DataCatalogs": [], "SemanticModels": [],
        "ReportBindings": [], "UninventoriedTableEngines": [],
        "Boundaries": {"BusinessRowOrAmountQueriesSubmitted": False, "ModelWriteRequested": False,
            "LakehouseWriteRequested": False, "RefreshRequested": False, "ReportPublished": False,
            "FilesWrittenByCell": False, "MetadataDAXExported": True, "RawErrorsOrCredentialsExported": False},
        "ScopeLimits": ["Only objects visible to the notebook user; hidden/inaccessible objects cannot be disproved.",
            "An inventory over time, not an atomic workspace snapshot or data-quality/performance test.",
            "No business rows/counts, stored source records, SQL views/procedures, KQL schemas or effective user access export.",
            "Partition M/SQL/calculated-table source expressions, connection payloads, role members/filters and arbitrary annotations omitted.",
            "Logical TMSL measures include DAX/dynamic formats; engine-internal generated helpers may be absent.",
            "Notebook/pipeline/function code, schedules, source files and capacity settings are not inspected."],
        "NextStep": "Return the entire inventory JSON privately here, including PARTIAL/STOPPED sections. No refresh or updater."})
    checks = report["Checks"]
    def step(name, action):
        print("Read-only inventory: " + name + ".", flush=True)
        checks[name] = {}
        return read_step(checks[name], action)
    def identity():
        workspace = checked(client.get(BASE)).json()
        require(workspace.get("id") == WORKSPACE and workspace.get("displayName") == WORKSPACE_NAME,
                "EXACT_WORKSPACE_NOT_CONFIRMED")
        report["Workspace"] = pick(workspace, "id displayName type capacityId")
    if not step("WorkspaceIdentity", identity):
        report["Stage"] = "UK_ANI_INVENTORY_R01_STOPPED"
        return report
    raw_items: list[dict[str, Any]] = []
    def items():
        try:
            pages(client.get, BASE + "/items", "value", raw_items, params={"recursive": "true"})
        finally:
            report["WorkspaceItems"] = item_projection(raw_items)
    list_ok = step("WorkspaceItems", items)
    for item in report["WorkspaceItems"]:
        if item["type"] in DATA_ITEMS:
            print("Read-only inventory: physical metadata for " + item["displayName"] + ".", flush=True)
            report["DataCatalogs"].append(data_catalog(client, lake_get, spark, item))
        elif item["type"] == "SemanticModel":
            entry = {"ItemID": item["id"], "Name": item["displayName"]}
            report["SemanticModels"].append(entry)
            print("Read-only inventory: logical metadata for " + item["displayName"] + ".", flush=True)
            read_step(entry, lambda: entry.update(Catalog=semantic_catalog(definition(client, item["id"]))))
        elif item["type"] in OTHER_ENGINES:
            report["UninventoriedTableEngines"].append({**item, "Reason": "ENGINE_CATALOG_NOT_SUPPORTED_BY_THIS_CELL"})
    def bindings():
        body = checked(pbi.get("/v1.0/myorg/groups/" + WORKSPACE + "/reports")).json()
        require(isinstance(body.get("value"), list), "REPORT_LIST_MISSING")
        report["ReportBindings"] = [pick(r, "id name reportType datasetId datasetWorkspaceId") for r in body["value"]]
        require(not body.get("@odata.nextLink") and not body.get("continuationToken"), "REPORT_BINDINGS_PAGINATION_UNSUPPORTED")
    step("ReportModelBindings", bindings)
    def end_items():
        final: list[dict[str, Any]] = []
        pages(client.get, BASE + "/items", "value", final, params={"recursive": "true"})
        same = item_projection(final) == report["WorkspaceItems"]
        checks["WorkspaceItemsRecheck"]["SameItemList"] = same
        require(list_ok and same, "WORKSPACE_ITEM_LIST_CHANGED_OR_INITIAL_LIST_PARTIAL")
    step("WorkspaceItemsRecheck", end_items)
    expected_models = {i["id"] for i in report["WorkspaceItems"] if i["type"] == "SemanticModel"}
    expected_data = {i["id"] for i in report["WorkspaceItems"] if i["type"] in DATA_ITEMS}
    report["Completeness"] = {"WorkspaceItemPagesCompleted": list_ok,
        "SemanticModelsDiscovered": len(expected_models), "SemanticModelsRead": sum(
            m["Status"] == "READ_COMPLETED" for m in report["SemanticModels"]),
        "DataItemsDiscovered": len(expected_data), "DataItemsRead": sum(
            m["Status"] == "READ_COMPLETED" for m in report["DataCatalogs"]),
        "OtherTableEnginesUnread": len(report["UninventoriedTableEngines"])}
    if (all(c["Status"] == "READ_COMPLETED" for c in checks.values())
            and all(m["Status"] == "READ_COMPLETED" for m in report["SemanticModels"] + report["DataCatalogs"])
            and not report["UninventoriedTableEngines"]):
        report["Stage"] = "UK_ANI_INVENTORY_R01_COMPLETED_WITHIN_DECLARED_SCOPE"
    report["FinishedUTC"] = datetime.now(timezone.utc).isoformat()
    return report


def emit(report):
    payload = {"Inventory": report, "InventorySHA256": digest(report)}
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    print("BEGIN UK-ANI-DEMAND INVENTORY JSON (private metadata; no business rows)", flush=True)
    print(raw.decode("utf-8"), flush=True)
    print("END UK-ANI-DEMAND INVENTORY JSON | UTF8 bytes=" + str(len(raw)) +
          " | File SHA256=" + hashlib.sha256(raw).hexdigest(), flush=True)
    # Browser-only download of the same in-memory bytes. No server/OneLake file write.
    # Full stdout above remains the fallback if the notebook blocks data-link downloads.
    try:
        from IPython.display import HTML, display
        encoded = base64.b64encode(raw).decode("ascii")
        display(HTML('<a download="UK-ANI-Demand-inventory-R01.json" href="data:application/json;base64,' +
                     encoded + '">Download complete inventory JSON (private metadata)</a>'))
    except Exception:
        print("Download link unavailable; copy the complete BEGIN/END output into a text file.", flush=True)


if __name__ == "__main__":
    inventory_result: dict[str, Any] = {}
    try:
        import notebookutils
        import requests
        import sempy.fabric as fabric
        with requests.Session() as inventory_session:
            run(fabric.FabricRestClient(retry_config=NO_RETRY),
                fabric.PowerBIRestClient(retry_config=NO_RETRY),
                onelake_reader(notebookutils.credentials, inventory_session), globals().get("spark"), inventory_result)
    except (Exception, KeyboardInterrupt) as inventory_error:
        inventory_result.update(Stage="UK_ANI_INVENTORY_R01_STOPPED", Revision="R01",
            Failure=failure(inventory_error), NextStep="Send this JSON; no refresh or update.")
    emit(inventory_result)
