# READ ONLY: inspect model metadata. No installer, sales query or refresh.
# Step 2: source-reference metadata only. Paste into ONE NEW setup-notebook cell.
import base64
import json
import re
import time
from uuid import UUID
import sempy.fabric as fabric

MODE = "PROBE"
WORKSPACE = 'f5cb5742-9a7c-4337-a4c0-952706dddf0b'
MODEL = 'e7af2967-7725-4108-a170-9e490d4e35bb'


def read_definition(client):
    path = f"/v1/workspaces/{WORKSPACE}/semanticModels/{MODEL}/getDefinition"
    response = client.post(path + "?format=TMSL")
    response.raise_for_status()
    if response.status_code == 200:
        return response.json()["definition"]
    if response.status_code != 202:
        raise RuntimeError("Unexpected metadata response. No model changes made.")
    operation_id = str(UUID(response.headers["x-ms-operation-id"]))
    operation = "/v1/operations/" + operation_id
    deadline = time.monotonic() + 360
    while time.monotonic() < deadline:
        delay = max(1, min(30, int(response.headers.get("Retry-After", "5"))))
        time.sleep(min(delay, max(0, deadline - time.monotonic())))
        response = client.get(operation)
        response.raise_for_status()
        status = response.json().get("status")
        if status == "Succeeded":
            result = client.get(operation + "/result")
            result.raise_for_status()
            return result.json()["definition"]
        if status in {"Failed", "Cancelled", "Canceled"}:
            raise RuntimeError("Metadata read did not complete: " + status)
    raise TimeoutError("Metadata read timed out. No model changes made.")


def connector_hints(expression):
    if isinstance(expression, list):
        expression = "\n".join(expression)
    known = ("Sql.Database", "Sql.Databases", "OneLake.SqlAnalytics",
             "AzureStorage.DataLake", "Lakehouse.Contents")
    return [name for name in known if isinstance(expression, str)
            and re.search(r"\b" + re.escape(name) + r"\s*\(", expression, re.I)]


def describe_route(definition):
    part = next((p for p in definition["parts"] if p["path"] == "model.bim"), None)
    if part is None:
        raise ValueError("TMSL model.bim was not returned. No changes made.")
    model = json.loads(base64.b64decode(part["payload"]))["model"]
    fact = next((t for t in model.get("tables", [])
                 if t["name"] == "fm_review_facts"), {})
    partitions = fact.get("partitions", [])
    source = partitions[0].get("source", {}) if len(partitions) == 1 else {}
    expressions = []
    for item in model.get("expressions", []):
        expressions.append({
            "ReferencedByFact": bool(source.get("expressionSource"))
                and item.get("name") == source.get("expressionSource"),
            "Kind": item.get("kind") if item.get("kind") in {"m", "calculated"} else "OTHER",
            "ConnectorHints": connector_hints(item.get("expression", ""))})
    data_sources = []
    for item in model.get("dataSources", []):
        details = item.get("connectionDetails") or {}
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except ValueError:
                details = {}
        if not isinstance(details, dict):
            details = {}
        protocol = str(details.get("protocol", "")).lower()
        address = details.get("address") or {}
        data_sources.append({
            "ReferencedByFact": bool(source.get("dataSource"))
                and item.get("name") == source.get("dataSource"),
            "Type": item.get("type") if item.get("type") in {"structured", "provider"} else "OTHER",
            "Protocol": protocol if protocol in {"tds", "sql", "https", "onelake"} else "OTHER",
            "ConnectionDetailKeys": sorted(details),
            "AddressKeys": sorted(address) if isinstance(address, dict) else [],
            "HasConnectionString": bool(item.get("connectionString"))})
    return {"Mode": "PROBE", "ProbeVersion": "SOURCE-ROUTE-R02",
            "FactPartitionCount": len(partitions),
            "StorageModes": [p.get("mode", "UNKNOWN") for p in partitions],
            "EntitySourceKeys": sorted(source),
            "HasExpressionSourceReference": bool(source.get("expressionSource")),
            "HasDataSourceReference": bool(source.get("dataSource")),
            "SchemaIsDbo": source.get("schemaName") == "dbo",
            "EntityMatchesFactName": source.get("entityName") == "fm_review_facts",
            "ExpressionHints": expressions, "DataSourceHints": data_sources,
            "ConnectionValuesPrinted": False, "SourceAmountsRead": False,
            "ModelUpdated": False,
            "NextStep": "Inspect this source shape before adapting the installer."}


if MODE != "PROBE":
    raise ValueError("This file supports read-only source inspection only.")
print("Reading source-reference metadata only. No installation or refresh.")
print(json.dumps(describe_route(read_definition(fabric.FabricRestClient())), indent=2))
