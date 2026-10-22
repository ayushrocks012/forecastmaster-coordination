"""Synthetic metadata/API tests. Never connects to a company model."""
import base64
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("repair", ROOT / "REPAIR TEST FEED.py")
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)
DAX = "VAR _scopeAllowed = TRUE()\nRETURN IF(_scopeAllowed,\n  42\n)"


def database():
    return {"name": "Synthetic", "compatibilityLevel": 1604, "model": {
        "culture": "en-GB", "roles": [{"name": "SyntheticRole", "modelPermission": "read"}],
        "expressions": [{"name": "Source", "kind": "m", "expression": "PRIVATE_SOURCE"}],
        "relationships": [{"name": "SyntheticRelationship", "fromTable": "fm_native_0"}],
        "tables": [{"name": repair.TABLE, "partitions": [{"mode": "directLake"}],
                    "measures": [{"name": name, "expression": DAX + "\ndisplayFolder: " + repair.FOLDER,
                                  "formatString": "0", "annotations": [{"name": "Keep", "value": "yes"}]}
                                 for name in sorted(repair.NAMES)] + [
                                     {"name": "Unrelated", "expression": "99", "displayFolder": "Keep"}]},
                   {"name": "fm_review_facts", "partitions": [{"mode": "directLake",
                     "source": {"type": "entity", "entityName": "fm_review_facts"}}]}]
                  + [{"name": "fm_native_" + str(i), "measures": [
                      {"name": "N Synthetic " + str(i), "expression": str(i)}]} for i in range(20)]}}


def definition(db):
    return {"parts": [{"path": "model.bim", "payloadType": "InlineBase64",
                       "payload": base64.b64encode(json.dumps(db).encode()).decode()},
                      {"path": "definition.pbism", "payloadType": "InlineBase64", "payload": "e30="},
                      {"path": ".platform", "payloadType": "InlineBase64", "payload": "PRIVATE_ID"}]}


class Response:
    def __init__(self, body=None, status=200, headers=None):
        self.body, self.status_code, self.headers = body, status, headers or {}
    def json(self):
        if self.body is None:
            raise ValueError("Empty response body")
        return deepcopy(self.body)


class Client:
    def __init__(self):
        self.db, self.calls, self.reads, self.connection_reads = database(), [], 0, 0
        self.connections = [{"id": "SYNTHETIC_ID", "connectivityType": "ShareableCloud",
                             "connectionDetails": {"type": "AzureDataLakeStorage", "path": "PRIVATE"}}]
        self.identity = {"id": repair.TEST_MODEL, "displayName": repair.TEST_NAME, "type": "SemanticModel"}
        self.concurrent, self.connection_change, self.reject, self.asynchronous = False, False, False, False
        self.connection_failure, self.bad_readback = False, False
        self.op = "11111111-2222-4333-8444-555555555555"
    def get(self, path):
        self.calls.append(("GET", path, None))
        if path == repair.ITEM:
            return Response(self.identity)
        if path == repair.ITEM + "/connections":
            self.connection_reads += 1
            if self.connection_failure:
                return Response(status=403)
            values = deepcopy(self.connections)
            if self.connection_change and self.connection_reads > 1:
                values[0]["id"] = "CHANGED"
            return Response({"value": values})
        if path == "/v1/operations/" + self.op:
            return Response({"status": "Succeeded"})
        raise AssertionError("Unexpected GET " + path)
    def post(self, path, json=None):
        self.calls.append(("POST", path, deepcopy(json)))
        if path == repair.BASE + "/getDefinition?format=TMSL":
            self.reads += 1
            db = deepcopy(self.db)
            if self.concurrent and self.reads > 1:
                db["model"]["culture"] = "en-US"
            return Response({"definition": definition(db)})
        if path == repair.BASE + "/updateDefinition":
            if self.reject:
                return Response({"PRIVATE": "SERVER_ERROR"}, status=400)
            self.db = repair.database_part(json["definition"])
            if self.bad_readback:
                self.db["model"]["culture"] = "en-US"
            return Response(status=202, headers={"x-ms-operation-id": self.op, "Retry-After": "0"}) \
                if self.asynchronous else Response()
        raise AssertionError("Unexpected POST " + path)


class FileSystem:
    def __init__(self):
        self.files, self.fail = {}, False
    def mkdirs(self, path):
        pass
    def put(self, path, raw, overwrite):
        assert not overwrite and path not in self.files
        self.files[path] = raw
    def head(self, path, size):
        return "CORRUPT" if self.fail else self.files[path]


def writes(client):
    return [(path, body) for verb, path, body in client.calls
            if verb == "POST" and not path.endswith("getDefinition?format=TMSL")]


class RepairTests(unittest.TestCase):
    def test_existing_public_feed_templates_keep_their_complete_dax(self):
        baseline = ROOT.parents[1] / "report-cycle-cache-r04.2" / "baseline"
        sys.path.insert(0, str(baseline))
        previous_bytecode = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            feed_spec = importlib.util.spec_from_file_location("original_feed", baseline / "visual_feed.py")
            feed = importlib.util.module_from_spec(feed_spec)
            feed_spec.loader.exec_module(feed)
        finally:
            sys.path.remove(str(baseline))
            sys.dont_write_bytecode = previous_bytecode
        db = database()
        for measure in db["model"]["tables"][0]["measures"][:9]:
            measure["expression"] = feed.M[measure["name"]]["expression"] + "\ndisplayFolder: " + repair.FOLDER
        fixed, names = repair.repair_database(db)
        self.assertEqual(len(names), 9)
        for measure in fixed["model"]["tables"][0]["measures"][:9]:
            self.assertEqual(measure["expression"], feed.M[measure["name"]]["expression"])

    def test_nine_expressions_and_folder_only(self):
        db = database()
        before = deepcopy(db)
        fixed, names = repair.repair_database(db)
        self.assertEqual(db, before)
        self.assertEqual(len(names), 9)
        expected = deepcopy(before)
        for measure in expected["model"]["tables"][0]["measures"][:9]:
            measure["expression"] = DAX
            measure["displayFolder"] = repair.FOLDER
        self.assertEqual(fixed, expected)

    def test_line_array_crlf_and_existing_folder(self):
        db = database()
        measure = db["model"]["tables"][0]["measures"][0]
        measure["expression"] = measure["expression"].splitlines()
        measure["displayFolder"] = repair.FOLDER
        db["model"]["tables"][0]["measures"][1]["expression"] += "\r\n"
        fixed, names = repair.repair_database(db)
        self.assertEqual(len(names), 9)
        self.assertEqual(fixed["model"]["tables"][0]["measures"][0]["expression"], DAX.splitlines())

    def test_idempotent_no_second_write(self):
        client, fs = Client(), FileSystem()
        with patch("builtins.print"):
            repair.run(client, fs)
            result = repair.run(client, fs)
        self.assertEqual(result["Stage"], "TEST_FEED_ALREADY_CLEAN")
        self.assertEqual(len(writes(client)), 1)

    def test_partial_already_clean_preserved(self):
        db = database()
        first = db["model"]["tables"][0]["measures"][0]
        first["expression"], first["displayFolder"] = DAX, "Existing folder"
        fixed, names = repair.repair_database(db)
        self.assertEqual(len(names), 8)
        self.assertEqual(fixed["model"]["tables"][0]["measures"][0], first)

    def test_unexpected_suffix_or_metadata_refused(self):
        for suffix in ("DifferentFolder", repair.FOLDER + "\nformatString: 0", repair.FOLDER + " extra"):
            db = database()
            db["model"]["tables"][0]["measures"][0]["expression"] = DAX + "\ndisplayFolder: " + suffix
            with self.assertRaises(ValueError):
                repair.repair_database(db)

    def test_conflicting_folder_refused(self):
        db = database()
        db["model"]["tables"][0]["measures"][0]["displayFolder"] = "Other"
        with self.assertRaises(ValueError):
            repair.repair_database(db)

    def test_terminal_text_inside_string_or_comment_refused(self):
        for prefix in ('RETURN "unfinished\n)', "RETURN /* unfinished\n)", "RETURN 'unfinished\n)"):
            db = database()
            db["model"]["tables"][0]["measures"][0]["expression"] = prefix + "\ndisplayFolder: " + repair.FOLDER
            with self.assertRaises(ValueError):
                repair.repair_database(db)

    def test_escaped_dax_literals_and_comments(self):
        text = 'VAR x = "a""b" // comment\nVAR y = \'O\'\'Brien\'[A] /* block */\nRETURN IF(TRUE(), x)'
        self.assertTrue(repair.normal_dax_at_end(text))

    def test_missing_or_duplicate_expected_measure_refused(self):
        for duplicate in (False, True):
            db = database()
            measures = db["model"]["tables"][0]["measures"]
            measures.pop(0) if not duplicate else measures.append(deepcopy(measures[0]))
            with self.assertRaises(ValueError):
                repair.repair_database(db)

    def test_api_target_backup_readback_and_privacy(self):
        client, fs = Client(), FileSystem()
        before = deepcopy(client.db)
        with patch("builtins.print") as printed:
            result = repair.run(client, fs)
        self.assertEqual(result["Stage"], "TEST_FEED_REPAIRED")
        self.assertEqual(result["MeasuresChanged"], 9)
        self.assertTrue(result["CloudConnectionPreserved"])
        self.assertFalse(result["OriginalModelWriteRequested"])
        self.assertFalse(result["SourceAmountsQueried"])
        self.assertEqual(len(writes(client)), 1)
        path, request = writes(client)[0]
        self.assertEqual(path, repair.BASE + "/updateDefinition")
        self.assertFalse(request["options"]["allowPurgeData"])
        stored = json.loads(next(v for k, v in fs.files.items() if k.endswith("definition-before.json")))
        self.assertEqual(repair.database_part(stored), before)
        self.assertEqual(len(fs.files), 4)
        self.assertNotIn("PRIVATE_SOURCE", str(printed.call_args_list))
        self.assertNotIn("SYNTHETIC_ID", str(printed.call_args_list))
        self.assertTrue(all(repair.ORIGINAL_MODEL not in p for _, p, _ in client.calls))

    def test_wrong_item_identity_or_helper_count_no_write(self):
        for wrong_name in (True, False):
            client, fs = Client(), FileSystem()
            if wrong_name:
                client.identity["displayName"] = "Production"
            else:
                client.db["model"]["tables"].pop()
            with self.assertRaises(ValueError):
                repair.run(client, fs)
            self.assertEqual(writes(client), [])

    def test_bad_backup_prevents_write(self):
        client, fs = Client(), FileSystem()
        fs.fail = True
        with self.assertRaises(RuntimeError):
            repair.run(client, fs)
        self.assertEqual(writes(client), [])

    def test_concurrent_metadata_or_connection_change_no_write(self):
        for change in ("concurrent", "connection_change"):
            client, fs = Client(), FileSystem()
            setattr(client, change, True)
            with patch("builtins.print"), self.assertRaises(RuntimeError):
                repair.run(client, fs)
            self.assertEqual(writes(client), [])

    def test_mapping_unavailable_or_automatic_no_write(self):
        for unavailable in (True, False):
            client, fs = Client(), FileSystem()
            if unavailable:
                client.connection_failure = True
            else:
                client.connections[0]["connectivityType"] = "Automatic"
            with self.assertRaises((ValueError, RuntimeError)):
                repair.run(client, fs)
            self.assertEqual(writes(client), [])

    def test_update_error_retains_backup_and_never_retries(self):
        client, fs = Client(), FileSystem()
        client.reject = True
        with patch("builtins.print"), self.assertRaises(RuntimeError) as error:
            repair.run(client, fs)
        self.assertEqual(len(writes(client)), 1)
        self.assertEqual(len(fs.files), 3)
        self.assertNotIn("SERVER_ERROR", str(error.exception))

    def test_async_empty_update_response_succeeds(self):
        client, fs = Client(), FileSystem()
        client.asynchronous = True
        with patch("builtins.print"), patch.object(repair.time, "sleep"):
            result = repair.run(client, fs)
        self.assertEqual(result["Stage"], "TEST_FEED_REPAIRED")
        self.assertEqual(len(writes(client)), 1)

    def test_different_readback_stops(self):
        client, fs = Client(), FileSystem()
        client.bad_readback = True
        with patch("builtins.print"), self.assertRaises(RuntimeError):
            repair.run(client, fs)
        self.assertEqual(len(writes(client)), 1)

    def test_notebook_same_readable_code_empty_outputs(self):
        code = (ROOT / "REPAIR TEST FEED.py").read_text()
        notebook = json.loads((ROOT / "ForecastMaster TEST Feed Repair R01.ipynb").read_text())
        cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        self.assertEqual(len(cells), 1)
        self.assertEqual("".join(cells[0]["source"]), code)
        self.assertEqual(cells[0]["outputs"], [])
        self.assertLess(len(code.encode()), 16000)
        self.assertLess(max(map(len, code.splitlines())), 150)


if __name__ == "__main__":
    result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(RepairTests))
    (ROOT / "VALIDATION.json").write_text(json.dumps({
        "Tests": result.testsRun, "Passed": result.wasSuccessful(),
        "Evidence": "Synthetic metadata and mocked API/filesystem only; no company execution.",
        "ActualCompanyRepair": "PENDING", "ActualRefreshWithoutWarnings": "PENDING",
        "GitNexusImpact": "UNKNOWN: Coordination unregistered; edit-impact AUTHORITY_DRIFT_BLOCKS_CONCLUSION",
        "Fallback": "Direct create-model/feed source tracing and bounded preservation/API tests",
        "ProductionModelWriteRequestedByLocalTests": False,
        "NumericBusinessLogicChanged": False}, indent=2) + "\n")
    raise SystemExit(not result.wasSuccessful())
