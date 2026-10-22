"""Source-preservation/API-scope tests. No company calls or data."""
import base64
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_candidate as build
import onelake_model as om


def source_model():
    return {"name": "Original", "compatibilityLevel": 1604, "model": {
        "culture": "en-GB", "roles": [{"name": "Existing", "modelPermission": "read"}],
        "expressions": [{"name": "OriginalSource", "kind": "m",
                         "expression": 'AzureStorage.DataLake("PRIVATE_ENDPOINT")'}],
        "tables": [{"name": "fm_review_facts", "partitions": [{"name": "OriginalPartition",
            "mode": "directLake", "source": {"type": "entity", "expressionSource": "OriginalSource",
            "entityName": "fm_review_facts", "schemaName": "dbo"}}]},
            {"name": "OtherTable", "annotations": [{"name": "Owner", "value": "Keep"}]}],
        "relationships": [{"name": "ExistingRelationship", "fromTable": "OtherTable"}]}}


def definition(database):
    return {"parts": [{"path": "model.bim", "payloadType": "InlineBase64",
                       "payload": base64.b64encode(json.dumps(database).encode()).decode()},
                      {"path": "definition.pbism", "payload": "e30=", "payloadType": "InlineBase64"},
                      {"path": ".platform", "payload": "PRIVATE_ITEM_ID"}]}


class Response:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self.body, self.headers = status, body, headers or {}
    def json(self):
        return deepcopy(self.body)


class Client:
    def __init__(self, db=None, duplicate=False, reject=False, changed=False, asynchronous=False):
        self.db, self.duplicate = db or source_model(), duplicate
        self.reject, self.changed, self.asynchronous = reject, changed, asynchronous
        self.calls, self.created, self.reads = [], None, 0
        self.test_id = "11111111-2222-4333-8444-555555555555"
        self.op_id = "99999999-2222-4333-8444-555555555555"
    def get(self, path):
        self.calls.append(("GET", path))
        if path.endswith("/semanticModels"):
            return Response(200, {"value": [{"displayName": "ForecastMaster Native OneLake R17.1 - TEST"}]
                                          if self.duplicate else []})
        if path.endswith("/result"):
            return Response(200, {"id": self.test_id})
        if path.startswith("/v1/operations/"):
            return Response(200, {"status": "Succeeded"})
        raise AssertionError("Unexpected GET " + path)
    def post(self, path, json=None):
        self.calls.append(("POST", path))
        if path.endswith("/getDefinition?format=TMSL"):
            if self.test_id in path:
                return Response(200, {"definition": self.created})
            self.reads += 1
            db = deepcopy(self.db)
            if self.changed and self.reads > 1:
                db["model"]["culture"] = "en-US"
            return Response(200, {"definition": definition(db)})
        if path.endswith("/semanticModels"):
            if self.reject:
                return Response(400, {"secret": "PRIVATE_SERVER_ERROR"})
            self.created = json["definition"]
            if self.asynchronous:
                return Response(202, {}, {"x-ms-operation-id": self.op_id, "Retry-After": "0"})
            return Response(201, {"id": self.test_id})
        raise AssertionError("Unexpected POST " + path)


def runtime():
    module = types.ModuleType("candidate_under_test")
    sempy = types.ModuleType("sempy")
    fabric = types.ModuleType("sempy.fabric")
    with patch.dict(sys.modules, {"sempy": sempy, "sempy.fabric": fabric}):
        exec(compile(build.render(), "readable-candidate", "exec"), module.__dict__)
    return module


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = runtime()

    def test_all_original_json_values_preserved(self):
        before = source_model()
        snapshot = deepcopy(before)
        after = om.extend_onelake(before)
        self.assertEqual(before, snapshot)
        self.assertEqual(after["model"]["tables"][:2], before["model"]["tables"])
        self.assertEqual(after["model"]["roles"], before["model"]["roles"])
        self.assertEqual(after["model"]["expressions"], before["model"]["expressions"])
        self.assertEqual(after["model"]["relationships"][0], before["model"]["relationships"][0])
        self.assertEqual(len(after["model"]["tables"]), 22)
        before["model"]["relationships"][0]["name"] = "NativeR17-Lines-State"
        after = om.extend_onelake(before)
        self.assertEqual(after["model"]["relationships"][0], before["model"]["relationships"][0])

    def test_source_modes_are_never_converted(self):
        for connector, mode in [("Sql.Database", "directLake"), ("AzureStorage.DataLake", "import")]:
            db = source_model()
            db["model"]["expressions"][0]["expression"] = connector + '("PRIVATE")'
            db["model"]["tables"][0]["partitions"][0]["mode"] = mode
            with self.assertRaises(ValueError):
                om.extend_onelake(db)

    def test_existing_native_objects_refused(self):
        db = source_model()
        db["model"]["tables"].append({"name": "fm_native_state"})
        with self.assertRaises(ValueError):
            om.extend_onelake(db)

    def test_compact_chart_keeps_table_rank_selection(self):
        after = om.extend_onelake(source_model())
        tables = {t["name"]: t for t in after["model"]["tables"]}
        self.assertNotIn("fm_native_state", om.LINES)
        self.assertIn("fm_native_catalog", om.LINES)
        self.assertEqual(len(om.nm.static_tables()["rows"]), 7560)
        self.assertNotIn("NativeR17-Lines-State", {r["name"] for r in after["model"]["relationships"]})
        chart = next(m for m in tables["fm_native_measures"]["measures"] if m["name"] == "N Chart Monthly")
        self.assertIn("[RowID]=_row", chart["expression"])
        self.assertIn("[Display]=_display", chart["expression"])

    def test_no_sales_columns_in_metadata_dependencies(self):
        for expression in om.EXPRESSIONS.values():
            for forbidden in ("[Amount]", "[MissingCells]", "[NumericCells]", "SUM(", "AVERAGE("):
                self.assertNotIn(forbidden, expression)
        self.assertEqual(set(om.EXPRESSIONS), {"files", "scope", "groups", "scenario", "lines"})

    def test_business_measures_other_than_selection_unchanged(self):
        after = om.extend_onelake(source_model())
        measures = next(t for t in after["model"]["tables"] if t["name"] == "fm_native_measures")["measures"]
        before = {m["name"]: m for m in om.nm.measures()}
        for measure in measures:
            if measure["name"] != "N Chart Monthly":
                self.assertEqual(measure, before[measure["name"]])

    def test_created_model_only_and_platform_not_copied(self):
        client = Client()
        with patch("builtins.print"):
            result = self.runtime.create_test_model(client)
        self.assertTrue(result["OriginalModelUnchanged"])
        self.assertFalse(result["RefreshRequested"])
        self.assertEqual(result["NativeCalculatedHelpers"], 20)
        self.assertEqual([p["path"] for p in client.created["parts"]], ["model.bim", "definition.pbism"])
        writes = [p for verb, p in client.calls if verb == "POST" and "getDefinition" not in p]
        self.assertEqual(writes, [f"/v1/workspaces/{self.runtime.WORKSPACE}/semanticModels"])
        self.assertNotIn("PRIVATE_ENDPOINT", json.dumps(result))

    def test_duplicate_and_concurrent_change_do_not_create(self):
        for client in (Client(duplicate=True), Client(changed=True)):
            with self.subTest(client=client), self.assertRaises((ValueError, RuntimeError)):
                self.runtime.create_test_model(client)
            self.assertIsNone(client.created)

    def test_creation_rejection_never_retries_or_echoes_response(self):
        client = Client(reject=True)
        with patch("builtins.print"), self.assertRaises(RuntimeError) as error:
            self.runtime.create_test_model(client)
        self.assertNotIn("PRIVATE_SERVER_ERROR", str(error.exception))
        self.assertEqual(sum(p.endswith("/semanticModels") for verb, p in client.calls if verb == "POST"), 1)

    def test_creation_lro_succeeds_without_duplicate_post(self):
        client = Client(asynchronous=True)
        with patch("builtins.print"), patch.object(self.runtime.time, "sleep"):
            result = self.runtime.create_test_model(client)
        self.assertEqual(result["TestModelID"], client.test_id)
        self.assertEqual(sum(p.endswith("/semanticModels") for verb, p in client.calls if verb == "POST"), 1)

    def test_generated_python_and_notebook_match_and_have_no_output(self):
        code = (ROOT / "CREATE ONELAKE TEST MODEL.py").read_text()
        self.assertEqual(code, build.render())
        notebook = json.loads((ROOT / "ForecastMaster OneLake Test - CREATE ONLY.ipynb").read_text())
        cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        self.assertEqual(len(cells), 1)
        self.assertEqual("".join(cells[0]["source"]), code)
        self.assertEqual(cells[0]["outputs"], [])
        self.assertEqual(len({c["id"] for c in notebook["cells"]}), len(notebook["cells"]))
        self.assertLess(len(code.encode()), 75000)
        self.assertLess(max(map(len, code.splitlines())), 600)
        for forbidden in ("updateDefinition", "saveAsTable", "getToken(", "requests.post", "refreshes"):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CandidateTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    (ROOT / "VALIDATION-CANDIDATE.json").write_text(json.dumps({
        "Tests": result.testsRun, "Passed": result.wasSuccessful(),
        "Evidence": "Local synthetic metadata and mocked Fabric API only.",
        "CompanyCreatedOrUpdated": False, "DirectLakePreviewProcessing": "UNVERIFIED",
        "BusinessParityWithR166": "NOT COMPLETE"}, indent=2) + "\n")
    raise SystemExit(not result.wasSuccessful())
