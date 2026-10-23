"""Synthetic metadata-only updater checks; never calls a company endpoint."""
import base64
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import model
import build_cell


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cell = load("r174_update", HERE / "UPDATE EXISTING TEST TO R17.4.py")
mock = load("r174_mock", HERE.parent / "report-native-onelake-r17.1/measure-repair-r02/tests/check_repair.py")
mock.repair = cell


def database():
    return {"name": "Synthetic", "compatibilityLevel": 1604, "model": {
      "culture": "en-GB", "roles": [{"name": "KeepRole", "modelPermission": "read"}],
      "expressions": [{"name": "KeepSource", "kind": "m", "expression": "PRIVATE FIXTURE"}],
      "relationships": [{"name": "KeepRelationship", "fromTable": "KeepA", "toTable": "KeepB"}],
      "tables": [{"name": "fm_native_measures", "measures": list(model.BASELINE.revised_measures().values())}]
        + [{"name": "fm_native_stub"+str(i)} for i in range(21)]
        + [{"name": "fm_review_facts", "partitions": [{"mode": "directLake", "source": {
            "type": "entity", "entityName": "fm_review_facts", "expressionSource": "KeepSource"}}]},
           {"name": "fm_review_measures", "measures": [{"name": "KeepFeed", "expression": "42"}]}]}}


class Client(mock.Client):
    def __init__(self):
        with patch.object(mock, "database", database):
            super().__init__()


class Tests(unittest.TestCase):
    def run_cell(self, client=None, fs=None):
        client, fs = client or Client(), fs or mock.FileSystem()
        with redirect_stdout(io.StringIO()), patch.object(cell.time, "sleep", lambda _: None):
            result = cell.run(client, fs)
        return result, client, fs

    def test_cell_reproducible_and_compiles(self):
        source = (HERE / "UPDATE EXISTING TEST TO R17.4.py").read_text()
        self.assertEqual(source, build_cell.build())
        compile(source, "r174_cell", "exec")

    def test_allowed_changes_preserve_all_numeric_definitions(self):
        before = database()
        after, changed = cell.patch_database(before)
        self.assertTrue(changed)
        self.assertEqual(before, database())
        old, new = before["model"]["tables"][0], after["model"]["tables"][0]
        self.assertEqual(before["model"]["tables"][1:], after["model"]["tables"][1:])
        for key in ("roles", "expressions", "relationships"):
            self.assertEqual(before["model"][key], after["model"][key])
        old_by = {m["name"]: m for m in old["measures"]}
        for m in new["measures"]:
            original = old_by[m["name"]]
            if m["name"] == "N Summary Cell":
                self.assertTrue(m["expression"].endswith(original["expression"] + ")"), "Leaf arithmetic must be unchanged")
                self.assertIn("HASONEVALUE('fm_native_columns'[ColumnKey])", m["expression"])
                self.assertIn("NOT ISINSCOPE('fm_native_columns'[Comparison])", m["expression"])
            else:
                self.assertEqual(m["expression"], original["expression"], m["name"])
        self.assertEqual(cell.patch_database(after), (after, []))

    def test_only_the_declared_format_properties_change(self):
        before = database()
        after, _ = cell.patch_database(before)
        for m in after["model"]["tables"][0]["measures"]:
            if "formatStringDefinition" not in m:
                continue
            expression = m["formatStringDefinition"]["expression"]
            self.assertIn('#,0,,.00', expression)
            self.assertIn('#,0,.0', expression)
            self.assertNotIn('#,0.00,,', expression)
            self.assertIn('"0.0%;−0.0%;0.0%"', expression)
            self.assertIn('_symbol&"0"', expression)

    def test_success_exactly_one_test_update_no_refresh_no_publish(self):
        result, c, fs = self.run_cell()
        self.assertEqual(result["Stage"], "TEST_R174_UPDATED")
        self.assertEqual(len(mock.writes(c)), 1)
        path, body = mock.writes(c)[0]
        self.assertEqual(path, cell.BASE + "/updateDefinition")
        self.assertEqual(body["options"], {"allowPurgeData": False})
        self.assertTrue(result["CloudConnectionPreserved"])
        self.assertFalse(result["SourceAmountsQueried"])
        self.assertFalse(result["RefreshRequested"])
        self.assertFalse(result["ReportPublished"])
        self.assertFalse(any(cell.ORIGINAL_MODEL in path for _, path, _ in c.calls))
        self.assertTrue(any("definition-before" in path for path in fs.files))
        c.calls = []
        result, _, _ = self.run_cell(c)
        self.assertEqual(result["Stage"], "TEST_R174_ALREADY_INSTALLED")
        self.assertFalse(mock.writes(c))

    def test_prewrite_guards_fail_closed(self):
        for mode in ("wrong_identity", "bad_source_count", "unknown_expression", "unknown_format", "unknown_inventory",
                     "missing_cloud", "concurrent", "connection_change", "connection_failure", "bad_backup", "bad_copy", "bad_put"):
            with self.subTest(mode=mode):
                c, fs = Client(), mock.FileSystem()
                if mode == "wrong_identity": c.identity["id"] = cell.ORIGINAL_MODEL
                elif mode == "bad_source_count": c.db["model"]["tables"].pop(1)
                elif mode == "unknown_expression": c.db["model"]["tables"][0]["measures"][0]["expression"] = "UNKNOWN"
                elif mode == "unknown_format":
                    m = next(m for m in c.db["model"]["tables"][0]["measures"] if "formatStringDefinition" in m)
                    m["formatStringDefinition"]["expression"] = '"UNKNOWN"'
                elif mode == "unknown_inventory": c.db["model"]["tables"][0]["measures"].pop()
                elif mode == "missing_cloud": c.connections = []
                elif mode == "bad_backup": fs.same_length_corruption = True
                elif mode == "bad_copy": fs.copy_false = True
                elif mode == "bad_put": fs.put_false = True
                else: setattr(c, mode, True)
                with self.assertRaises((ValueError, RuntimeError)):
                    self.run_cell(c, fs)
                self.assertFalse(mock.writes(c))

    def test_unknown_format_does_not_mutate_input(self):
        db = database()
        m = next(x for x in db["model"]["tables"][0]["measures"] if "formatStringDefinition" in x)
        m["formatStringDefinition"]["expression"] = '"UNKNOWN"'
        before = deepcopy(db)
        with self.assertRaises(ValueError):
            cell.patch_database(db)
        self.assertEqual(db, before)

    def test_failed_request_is_not_retried(self):
        c = Client()
        c.reject = True
        with self.assertRaises(RuntimeError): self.run_cell(c)
        self.assertEqual(len(mock.writes(c)), 1)

    def test_failed_readback_keeps_backup(self):
        c, fs = Client(), mock.FileSystem()
        c.bad_readback = True
        with self.assertRaises(RuntimeError): self.run_cell(c, fs)
        self.assertEqual(len(mock.writes(c)), 1)
        self.assertTrue(fs.files)

    def test_async_update(self):
        c = Client()
        c.asynchronous = True
        result, c, _ = self.run_cell(c)
        self.assertEqual(result["Stage"], "TEST_R174_UPDATED")
        self.assertEqual(len(mock.writes(c)), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
