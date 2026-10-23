"""Synthetic metadata/API tests. No Fabric credentials, company model or rows."""
import ast
import base64
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

SOURCE = Path(__file__).with_name("INVENTORY UK-ANI-DEMAND R01.py")
SPEC = importlib.util.spec_from_file_location("inventory_cell", SOURCE)
assert SPEC is not None and SPEC.loader is not None
cell = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cell)
LH, M1, M2, RID = ["00000000-0000-0000-0000-" + str(n).zfill(12) for n in range(1, 5)]
OP = "00000000-0000-0000-0000-000000000009"
SECRET = "SYNTHETIC-CONNECTION-SECRET-DO-NOT-EXPORT"


class Response:
    def __init__(self, data=None, status=200, headers=None):
        self.status_code, self.data, self.headers = status, data, headers or {}

    def json(self):
        return self.data


def model():
    return {"compatibilityLevel": 1604, "model": {"culture": "en-GB", "tables": [
        {"name": "Fact", "columns": [{"name": "Units", "dataType": "double", "sourceColumn": "Units"},
            {"name": "Computed", "type": "calculated", "dataType": "int64", "expression": "1 + 1",
             "isHidden": True, "formatString": "0"}], "measures": [
            {"name": "Amount", "expression": ["SUM('Fact'[Units])"], "formatString": "#,0",
             "formatStringDefinition": {"expression": "IF(TRUE(),\"0\",\"0.0\")"},
             "detailRowsDefinition": {"expression": "'Fact'"}, "isHidden": True,
             "kpi": {"statusExpression": "1", "trendExpression": "0"}}],
         "partitions": [{"name": "Fact", "mode": "directLake", "source": {
             "type": "entity", "entityName": "fact_units", "schemaName": "dbo", "expressionSource": "DatabaseQuery",
             "connectionString": SECRET}}]},
        {"name": "Dimension", "isHidden": True,
         "columns": [{"name": "Key", "dataType": "int64", "isKey": True}], "measures": [],
         "hierarchies": [{"name": "Hierarchy", "levels": [{"name": "Key", "column": "Key", "ordinal": 0}]}],
         "partitions": [{"name": "Dimension", "mode": "import", "source": {
             "type": "m", "expression": SECRET}}], "calculationGroup": {"precedence": 1,
             "calculationItems": [{"name": "Current", "expression": "SELECTEDMEASURE()",
                "formatStringDefinition": {"expression": "\"0\""}}]}}],
        "relationships": [{"name": "FactDimension", "fromTable": "Fact", "fromColumn": "Computed",
            "toTable": "Dimension", "toColumn": "Key", "isActive": False, "fromCardinality": "many",
            "toCardinality": "one", "crossFilteringBehavior": "bothDirections",
            "securityFilteringBehavior": "oneDirection", "annotations": [{"name": "Secret", "value": SECRET}]}],
        "roles": [{"name": "Reader", "modelPermission": "read", "members": [{"memberName": SECRET}],
            "tablePermissions": [{"name": "Fact", "filterExpression": SECRET}]}],
        "expressions": [{"name": "DatabaseQuery", "kind": "m", "expression": SECRET}],
        "dataSources": [{"connectionString": SECRET}], "annotations": [{"value": SECRET}]}}


def definition_response(database=None):
    return Response({"definition": {"parts": [{"path": "model.bim", "payloadType": "InlineBase64",
        "payload": base64.b64encode(json.dumps(database or model()).encode()).decode()}]}})


def item(kind, key, name):
    return {"id": key, "type": kind, "displayName": name, "workspaceId": cell.WORKSPACE}


class Fabric:
    def __init__(self, items=None):
        self.items = items if items is not None else [item("Lakehouse", LH, "SyntheticLake"),
            item("SemanticModel", M1, "Alpha"), item("SemanticModel", M2, "Beta"), item("Report", RID, "Report")]
        self.calls = []
        self.denied = set()
        self.changed = False
        self.list_starts = 0

    def get(self, path):
        self.calls.append(("GET", path))
        parsed = urlsplit(path)
        if path == cell.BASE:
            return Response({"id": cell.WORKSPACE, "displayName": cell.WORKSPACE_NAME})
        if parsed.path == cell.BASE + "/items":
            query = parse_qs(parsed.query)
            if "continuationToken" not in query:
                self.list_starts += 1
                return Response({"value": self.items[:1], "continuationToken": "page + two"})
            assert query["continuationToken"] == ["page + two"]
            changed = self.items + [item("Notebook", OP, "Extra")] if self.changed and self.list_starts > 1 else self.items
            return Response({"value": changed[1:]})
        if parsed.path == cell.BASE + "/lakehouses/" + LH + "/tables":
            return Response({"data": [{"name": "Table", "format": "Delta", "type": "Managed",
                "location": "abfss://" + cell.WORKSPACE + "@onelake.dfs.fabric.microsoft.com/" + LH + "/Tables/Table"}]})
        raise AssertionError("Unexpected Fabric GET route")

    def post(self, path):
        self.calls.append(("POST", path))
        assert path in {cell.BASE + "/semanticModels/" + key + "/getDefinition?format=TMSL" for key in (M1, M2)}
        if any(key in path for key in self.denied):
            return Response(status=403)
        return definition_response()


class Pbi:
    def get(self, path):
        assert path == "/v1.0/myorg/groups/" + cell.WORKSPACE + "/reports"
        return Response({"value": [{"id": RID, "name": "Report", "datasetId": M1, "embedUrl": SECRET}]})


class Lake:
    def __init__(self):
        self.calls = []
        self.denied = False
        self.bad_field = False
        self.table_page_fails = False

    def __call__(self, path):
        self.calls.append(path)
        parsed = urlsplit(path)
        query = parse_qs(parsed.query)
        if self.denied:
            return Response(status=403)
        if parsed.path.endswith("/schemas"):
            if "page_token" in query:
                assert query["page_token"] == ["next"]
                return Response({"schemas": [{"name": "second", "catalog_name": LH}]})
            return Response({"schemas": [{"name": "dbo", "catalog_name": LH}], "next_page_token": "next"})
        if parsed.path.endswith("/tables"):
            if "page_token" in query:
                return Response(status=429)
            body: dict[str, Any] = {"tables": [{"name": "Table"}]}
            if self.table_page_fails:
                body["next_page_token"] = "badnext"
            return Response(body)
        if "/tables/" in parsed.path:
            schema = query["schema_name"][0]
            if self.bad_field and schema == "second":
                return Response(status=403)
            return Response({"name": "Table", "schema_name": schema, "data_source_format": "DELTA",
                "columns": [{"name": "Column", "type_name": "decimal", "type_precision": 12,
                             "type_scale": 3, "nullable": False, "position": 0, "comment": SECRET}],
                "storage_location": SECRET, "properties": {"secret": SECRET}})
        raise AssertionError("Unexpected OneLake metadata route")


class SchemaOnlySpark:
    class Reader:
        def format(self, name):
            assert name == "delta"
            return self

        def load(self, path):
            assert path.startswith("abfss://" + cell.WORKSPACE)
            schema = {"fields": [{"name": "Nested", "nullable": True, "metadata": {"secret": SECRET},
                "type": {"type": "struct", "fields": [{"name": "Child", "type": "string",
                "nullable": True, "metadata": {"secret": SECRET}}]}}]}
            return SimpleNamespace(schema=SimpleNamespace(jsonValue=lambda: deepcopy(schema)))

    read = Reader()


class InventoryTests(unittest.TestCase):
    def execute(self, fabric=None, lake=None, pbi=None, spark=None):
        with redirect_stdout(io.StringIO()):
            return cell.run(fabric or Fabric(), pbi or Pbi(), lake or Lake(), spark)

    def test_all_models_and_schema_pages_and_bindings(self):
        report = self.execute()
        self.assertEqual(report["Stage"], "UK_ANI_INVENTORY_R01_COMPLETED_WITHIN_DECLARED_SCOPE")
        self.assertEqual(len(report["WorkspaceItems"]), 4)
        self.assertEqual(len(report["SemanticModels"]), 2)
        self.assertEqual(report["SemanticModels"][0]["Catalog"]["Counts"],
                         {"Tables": 2, "Columns": 3, "Measures": 1, "Relationships": 1, "Roles": 1})
        self.assertEqual(len(report["DataCatalogs"][0]["Schemas"]), 2)
        self.assertEqual(report["ReportBindings"][0]["datasetId"], M1)

    def test_private_connections_partition_code_members_and_annotations_excluded(self):
        report = self.execute()
        self.assertNotIn(SECRET, json.dumps(report))
        self.assertFalse(any(report["Boundaries"][key] for key in (
            "BusinessRowOrAmountQueriesSubmitted", "ModelWriteRequested", "LakehouseWriteRequested",
            "RefreshRequested", "ReportPublished", "FilesWrittenByCell")))

    def test_full_dax_hidden_columns_formats_hierarchies_and_calc_groups(self):
        catalog = cell.semantic_catalog(model())
        fact, dimension = catalog["Tables"]
        self.assertEqual(fact["Measures"][0]["expression"], ["SUM('Fact'[Units])"])
        self.assertIn("expression", fact["Measures"][0]["formatStringDefinition"])
        self.assertTrue(fact["Columns"][1]["isHidden"])
        self.assertEqual(fact["Columns"][1]["expression"], "1 + 1")
        self.assertTrue(dimension["isHidden"])
        self.assertEqual(dimension["Hierarchies"][0]["Levels"][0]["column"], "Key")
        self.assertEqual(dimension["CalculationGroup"]["Items"][0]["expression"], "SELECTEDMEASURE()")

    def test_inactive_bidirectional_relationship_preserved(self):
        relation = cell.semantic_catalog(model())["Relationships"][0]
        self.assertFalse(relation["isActive"])
        self.assertEqual(relation["crossFilteringBehavior"], "bothDirections")
        self.assertEqual(relation["OtherPropertyNames"], ["annotations"])

    def test_one_denied_model_keeps_other_model_and_physical_fields(self):
        fabric = Fabric()
        fabric.denied = {M1}
        report = self.execute(fabric=fabric)
        self.assertEqual(report["Stage"], "UK_ANI_INVENTORY_R01_PARTIAL")
        self.assertEqual(report["SemanticModels"][0]["Failure"]["HTTPStatus"], 403)
        self.assertEqual(report["SemanticModels"][1]["Status"], "READ_COMPLETED")
        self.assertEqual(report["DataCatalogs"][0]["Status"], "READ_COMPLETED")

    def test_unread_physical_column_does_not_block_other_schema(self):
        lake = Lake()
        lake.bad_field = True
        report = self.execute(lake=lake)
        attempts = report["DataCatalogs"][0]["Attempts"]
        self.assertEqual(report["Stage"], "UK_ANI_INVENTORY_R01_PARTIAL")
        self.assertEqual(attempts[0]["Schemas"][0]["Tables"][0]["Status"], "READ_COMPLETED")
        self.assertEqual(attempts[0]["Schemas"][1]["Tables"][0]["Status"], "READ_FAILED")

    def test_known_tables_fields_retained_after_later_page_failure(self):
        lake = Lake()
        lake.table_page_fails = True
        report = self.execute(lake=lake)
        attempt = report["DataCatalogs"][0]["Attempts"][0]
        self.assertEqual(attempt["Status"], "READ_FAILED")
        self.assertEqual(attempt["Schemas"][0]["TableListing"]["Failure"]["HTTPStatus"], 429)
        self.assertEqual(attempt["Schemas"][0]["Tables"][0]["Status"], "READ_COMPLETED")

    def test_classic_fallback_only_accesses_delta_schema_not_rows(self):
        lake = Lake()
        lake.denied = True
        report = self.execute(lake=lake, spark=SchemaOnlySpark())
        self.assertEqual(report["Stage"], "UK_ANI_INVENTORY_R01_COMPLETED_WITHIN_DECLARED_SCOPE")
        catalog = report["DataCatalogs"][0]
        self.assertEqual(catalog["Attempts"][0]["SchemaListing"]["Failure"]["HTTPStatus"], 403)
        self.assertEqual(catalog["Attempts"][1]["Status"], "READ_COMPLETED")
        self.assertEqual(catalog["Schemas"][0]["Tables"][0]["Columns"][0]["name"], "Nested")
        self.assertNotIn(SECRET, json.dumps(report))

    def test_fallback_refuses_foreign_location(self):
        fabric = Fabric()
        old = fabric.get
        def get(path):
            if "/lakehouses/" in path:
                return Response({"data": [{"name": "Table", "format": "Delta", "location": "abfss://foreign"}]})
            return old(path)
        output: dict[str, Any] = {}
        with patch.object(fabric, "get", side_effect=get), self.assertRaises(cell.InventoryStopped):
            cell.lakehouse_fallback(fabric, SchemaOnlySpark(), item("Lakehouse", LH, "L"), output)
        self.assertEqual(output["Schemas"][0]["Tables"][0]["Failure"]["Reason"], "TABLE_LOCATION_UNEXPECTED")

    def test_item_change_not_reported_complete(self):
        fabric = Fabric()
        fabric.changed = True
        report = self.execute(fabric=fabric)
        self.assertEqual(report["Stage"], "UK_ANI_INVENTORY_R01_PARTIAL")
        self.assertFalse(report["Checks"]["WorkspaceItemsRecheck"]["SameItemList"])

    def test_exact_workspace_guard_refuses_before_any_definition_or_schema(self):
        fabric = Fabric()
        with patch.object(fabric, "get", return_value=Response({"id": cell.WORKSPACE, "displayName": "Wrong"})):
            report = self.execute(fabric=fabric)
        self.assertEqual(report["Stage"], "UK_ANI_INVENTORY_R01_STOPPED")
        self.assertEqual(report["SemanticModels"], [])
        self.assertEqual(report["DataCatalogs"], [])

    def test_unsupported_engine_explicit_gap(self):
        fabric = Fabric([item("KQLDatabase", M1, "SyntheticKQL")])
        report = self.execute(fabric=fabric)
        self.assertEqual(report["Stage"], "UK_ANI_INVENTORY_R01_PARTIAL")
        self.assertEqual(report["Completeness"]["OtherTableEnginesUnread"], 1)

    def test_foreign_workspace_item_guard(self):
        record = item("SemanticModel", M1, "Model")
        record["workspaceId"] = M2
        with self.assertRaises(cell.InventoryStopped):
            cell.item_projection([record])

    def test_duplicate_item_pagination_refused(self):
        record = item("SemanticModel", M1, "Model")
        with self.assertRaises(cell.InventoryStopped):
            cell.item_projection([record, record])

    def test_page_token_query_is_encoded_and_arbitrary_uri_not_followed(self):
        paths = []
        def get(path):
            paths.append(path)
            if len(paths) == 1:
                return Response({"value": [1], "continuationToken": "+RID=#&x=bad",
                                 "continuationUri": "https://evil.example/steal"})
            return Response({"value": [2]})
        output: list[int] = []
        cell.pages(get, cell.BASE + "/items", "value", output)
        self.assertEqual(output, [1, 2])
        self.assertEqual(parse_qs(urlsplit(paths[1]).query)["continuationToken"], ["+RID=#&x=bad"])
        self.assertNotIn("evil", paths[1])

    def test_uri_only_continuation_uses_canonical_path(self):
        path = cell.BASE + "/items"
        uri = "https://api.fabric.microsoft.com:443" + path + "?continuationToken=next"
        self.assertEqual(cell.page_token({"continuationUri": uri}, path, "api.fabric.microsoft.com", "continuationToken"), "next")

    def test_unsafe_uri_only_continuations_refused(self):
        for uri in ("https://evil.example/items?continuationToken=x",
                    "https://api.fabric.microsoft.com/v1/workspaces/other/items?continuationToken=x",
                    "https://user@api.fabric.microsoft.com" + cell.BASE + "/items?continuationToken=x"):
            with self.subTest(uri=uri), self.assertRaises(cell.InventoryStopped):
                cell.page_token({"continuationUri": uri}, cell.BASE + "/items", "api.fabric.microsoft.com", "continuationToken")

    def test_pagination_loop_retains_read_items_and_fails(self):
        output: list[int] = []
        with self.assertRaises(cell.InventoryStopped):
            cell.pages(lambda path: Response({"value": [1], "continuationToken": "again"}),
                       cell.BASE + "/items", "value", output)
        self.assertEqual(output, [1, 1])

    def test_no_raw_error_in_failure(self):
        result = cell.failure(RuntimeError(SECRET))
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertEqual(result["ExceptionFamily"], "RuntimeError")

    def test_interruption_preserves_completed_metadata_in_callers_result(self):
        saved: dict[str, Any] = {}
        fabric = Fabric()
        original = fabric.post
        def post(path):
            if M2 in path:
                raise KeyboardInterrupt()
            return original(path)
        with patch.object(fabric, "post", side_effect=post), redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
            cell.run(fabric, Pbi(), Lake(), None, saved)
        self.assertEqual(saved["SemanticModels"][0]["Status"], "READ_COMPLETED")
        self.assertEqual(len(saved["DataCatalogs"][0]["Schemas"]), 2)

    def test_async_timeout_is_read_failure_without_resubmission(self):
        ticks = iter([0, 0, 400])
        client = SimpleNamespace(post=lambda path: Response(status=202, headers={"x-ms-operation-id": OP}),
                                 get=lambda path: Response({"status": "Running"}))
        with redirect_stdout(io.StringIO()), self.assertRaises(cell.InventoryStopped) as error:
            cell.definition(client, M1, sleep=lambda seconds: None, clock=lambda: next(ticks))
        self.assertEqual(error.exception.code, "DEFINITION_READ_TIMEOUT")

    def test_async_definition_reads_only_own_operation_and_result(self):
        calls = []
        states = iter([Response({"status": "Running"}), Response({"status": "Succeeded"})])
        def get(path):
            calls.append(path)
            return definition_response() if path.endswith("/result") else next(states)
        client = SimpleNamespace(post=lambda path: Response(status=202,
            headers={"x-ms-operation-id": OP, "Location": "https://evil.example"}), get=get)
        with redirect_stdout(io.StringIO()):
            result = cell.definition(client, M1, sleep=lambda seconds: None)
        self.assertEqual(len(result["model"]["tables"]), 2)
        self.assertEqual(calls, ["/v1/operations/" + OP] * 2 + ["/v1/operations/" + OP + "/result"])

    def test_async_cancel_does_not_retry_post(self):
        posts = []
        def post(path):
            posts.append(path)
            return Response(status=202, headers={"Location": "/operations/" + OP})
        client = SimpleNamespace(post=post, get=lambda path: Response({"status": "Cancelled"}))
        with self.assertRaises(cell.InventoryStopped):
            cell.definition(client, M1, sleep=lambda seconds: None)
        self.assertEqual(len(posts), 1)

    def test_operation_foreign_host_and_result_suffix_refused(self):
        for value in ("https://evil.example/v1/operations/" + OP, "/v1/operations/" + OP + "/result"):
            with self.assertRaises(cell.InventoryStopped):
                cell.operation_path({"Location": value})

    def test_missing_tmsl_not_invented_empty_catalog(self):
        client = SimpleNamespace(post=lambda path: Response({"definition": {"parts": []}}))
        with self.assertRaises(cell.InventoryStopped):
            cell.definition(client, M1)

    def test_storage_identity_not_exported_and_redirects_disabled(self):
        calls = []
        credentials = SimpleNamespace(getToken=lambda audience: SECRET if audience == "storage" else None)
        def get(url, **kwargs):
            calls.append((url, kwargs))
            return Response({})
        session = SimpleNamespace(get=get)
        read = cell.onelake_reader(credentials, session)
        read("/delta/" + cell.WORKSPACE + "/" + LH + "/api/2.1/unity-catalog/schemas")
        self.assertFalse(calls[0][1]["allow_redirects"])
        self.assertEqual(calls[0][1]["headers"]["Authorization"], "Bearer " + SECRET)
        with self.assertRaises(cell.InventoryStopped):
            read("/delta/foreign/item")
        self.assertEqual(len(calls), 1)

    def test_output_utf8_hash_and_download_are_the_same_complete_bytes(self):
        report = self.execute()
        report["SyntheticUnicode"] = "Sélection – 月"
        output, html = io.StringIO(), []
        module = SimpleNamespace(HTML=lambda value: value, display=lambda value: html.append(value))
        with patch.dict(sys.modules, {"IPython.display": module}), redirect_stdout(output):
            cell.emit(report)
        text = output.getvalue()
        raw = text.split("\n", 1)[1].split("\nEND UK-ANI-DEMAND INVENTORY JSON", 1)[0].encode("utf-8")
        payload = json.loads(raw)
        self.assertEqual(payload["InventorySHA256"], cell.digest(payload["Inventory"]))
        self.assertIn(hashlib.sha256(raw).hexdigest(), text)
        encoded = html[0].split("base64,", 1)[1].split('"', 1)[0]
        self.assertEqual(base64.b64decode(encoded), raw)
        self.assertIn("UTF8 bytes=" + str(len(raw)), text)

    def test_receiving_cell_python310_and_mutation_surface(self):
        tree = ast.parse(SOURCE.read_text(), feature_version=(3, 10))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        self.assertEqual(len([node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "post"]), 1)
        forbidden = {"put", "patch", "delete", "write", "write_text", "write_bytes", "putSecret", "mkdirs", "rm",
                     "save", "saveAsTable", "collect", "count", "toPandas", "evaluate_dax", "refresh_dataset"}
        self.assertFalse([node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr in forbidden])
        self.assertFalse([node for node in calls if isinstance(node.func, ast.Name) and node.func.id in {"open", "exec", "eval"}])
        report = self.execute(fabric := Fabric())
        self.assertIn("COMPLETED", report["Stage"])
        self.assertTrue(all(path.endswith("/getDefinition?format=TMSL") for method, path in fabric.calls if method == "POST"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
