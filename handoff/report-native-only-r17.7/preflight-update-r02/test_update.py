"""Synthetic guards for split comparisons and the unchanged TEST write boundary."""
import ast
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
import importlib.util
spec = importlib.util.spec_from_file_location("r177_r02_builder_tests", HERE / "build_cell.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
cell = builder.load("r177_r02_cell_tests", HERE / "UPDATE EXISTING TEST TO R17.7 R02.py")
fixture = builder.load("r177_frozen_tests_for_r02", HERE.parent / "test_revision.py")
frozen = fixture.cell
fixture.mock.repair = cell
PRIVATE = "SYNTHETIC_PRIVATE_SCOPE_PATH_AND_TOKEN"


class FabricAdomdException(Exception):
    pass


class Evaluate:
    def __init__(self, mode="ok", fail_scalar=1):
        self.calls, self.scalars, self.metadata_snapshots = [], [], 0
        self.mode, self.fail_scalar = mode, fail_scalar

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        assert kwargs["use_readwrite_connection"] is False
        dax = kwargs["dax_string"]
        if dax == cell.METADATA_QUERY:
            rows = [{"[Country]": PRIVATE + '"Country', "[Cycle]": "2026-10", "[Driver]": PRIVATE + '"Driver'}]
            return fixture.Frame([] if self.mode == "bad_scope" else rows)
        if dax.startswith("EVALUATE CALCULATETABLE(SELECTCOLUMNS"):
            self.metadata_snapshots += 1
            revision = PRIVATE + ("CHANGED" if self.mode == "source_changed" and self.metadata_snapshots > 1 else "REVISION")
            return fixture.Frame([{"[Revision]": revision, "[Priority]": 1, "[Rank]": 1, "[Ties]": 1}])
        self.scalars.append(kwargs)
        candidate = dax.startswith("DEFINE\n")
        field = re.search(r'ROW\("Value",CALCULATE\(\[(N Plan|N Benchmark|N Variance %|N Trend Monthly)\]', dax).group(1)
        value = {"N Plan": 1000.0, "N Benchmark": -20.0, "N Variance %": 51.0, "N Trend Monthly": 0.0}[field]
        if self.mode == "query_error" and len(self.scalars) == self.fail_scalar:
            raise FabricAdomdException("rsQueryMemoryLimitExceeded consumed memory 10240 MB, memory limit 10240 MB " + PRIVATE)
        if self.mode == "syntax_error" and candidate:
            raise FabricAdomdException("Query (7, 3) The syntax for ')' is incorrect. " + PRIVATE)
        if self.mode == "mismatch" and candidate:
            value += 1
        if self.mode == "within_tolerance" and candidate:
            value += 1e-8
        if self.mode in {"all_blank", "blank_to_zero"}:
            value = None if self.mode == "all_blank" or not candidate else 0.0
        if self.mode == "plans_only" and field != "N Plan":
            value = None
        if self.mode == "infinity":
            value = float("inf")
        if self.mode == "boolean":
            value = False
        if self.mode == "string":
            value = PRIVATE
        if self.mode == "incomplete":
            return fixture.Frame([])
        return fixture.Frame([{"[Value]": value}])


class Tests(unittest.TestCase):
    def run_cell(self, client=None, fs=None, evaluate=None):
        fixture.mock.repair = cell
        client, fs, evaluate = client or fixture.Client(), fs or fixture.mock.FileSystem(), evaluate or Evaluate()
        stream = io.StringIO()
        with redirect_stdout(stream), patch.object(cell.time, "sleep", lambda _: None):
            result = cell.run(client, fs, evaluate)
        self.assertNotIn(PRIVATE, stream.getvalue())
        return result, client, fs, evaluate, stream.getvalue()

    def test_generated_cell_python310_and_identical_metadata_patch(self):
        source = (HERE / "UPDATE EXISTING TEST TO R17.7 R02.py").read_text()
        self.assertEqual(builder.build(), source)
        tree = ast.parse(source, feature_version=(3, 10))
        for name in ("build_scalar", "verify_numeric"):
            function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
            self.assertFalse("UNION(" in ast.get_source_segment(source, function))
        for name in ("EXPECTED_HASHES", "EDITS", "FITS", "HELPER_PATCHES", "RELATIONSHIP", "NUMERIC_OVERRIDES",
                     "WORKSPACE", "TEST_MODEL", "ORIGINAL_MODEL", "LAKEHOUSE"):
            self.assertEqual(getattr(frozen, name), getattr(cell, name))
        old_tree = ast.parse((HERE.parent / "UPDATE EXISTING TEST TO R17.7.py").read_text())
        for name in ("patch_database", "verified_backup", "connection_state", "compare_with_calculated"):
            old_fn = next(n for n in old_tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
            new_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
            self.assertEqual(ast.dump(old_fn), ast.dump(new_fn))
        # Numeric virtual overrides must compile against the existing helpers.
        self.assertNotIn("FileChoiceLabel", "\n".join(cell.NUMERIC_OVERRIDES.values()))

    def test_every_scalar_preserves_original_expression_filters_and_coverage(self):
        scope = {"Country": 'Syn"Country', "Cycle": "2026-10", "Driver": 'Syn"Driver'}
        old_query = fixture.check.build_query(scope, {})
        cases = set()
        for metric in ("market", "ef", "share"):
            for window in (6, 12, 24):
                for year in (2026, 2027):
                    for field, _ in cell.MEMBERS:
                        query = cell.build_scalar(scope, {}, metric, window, year, field)
                        scalar = query.removeprefix('EVALUATE ROW("Value",').removesuffix(')')
                        self.assertIn(scalar, old_query)
                        cases.add((metric, window, year, field))
        self.assertEqual(72, len(cases))

    def test_72_pairs_read_only_then_one_guarded_write_and_verified_private_backup(self):
        result, client, fs, evaluate, output = self.run_cell()
        self.assertEqual("TEST_R177_UPDATED", result["Stage"])
        self.assertEqual("R02", result["UpdaterRevision"])
        preflight = result["NumericalPreflight"]
        self.assertEqual((72, 144, 3, 1), tuple(preflight[k] for k in ("Checks", "ScalarQueries", "MetadataQueries", "MaximumValuesPerQuery")))
        self.assertEqual(72, preflight["NumericComparisons"])
        self.assertEqual(147, len(evaluate.calls))
        self.assertTrue(preflight["SourceSelectionMetadataStable"])
        for index, call in enumerate(evaluate.scalars):
            self.assertEqual(index % 2 == 1, call["dax_string"].startswith("DEFINE\n"))
        self.assertTrue(all(c["dataset"] == cell.TEST_MODEL and c["workspace"] == cell.WORKSPACE
                            and c["use_readwrite_connection"] is False for c in evaluate.calls))
        writes = fixture.mock.writes(client)
        self.assertEqual(1, len(writes))
        self.assertEqual({"allowPurgeData": False}, writes[0][1]["options"])
        self.assertFalse(result["RefreshRequested"] or result["ReportPublished"] or result["OriginalModelWriteRequested"])
        self.assertTrue(result["CloudConnectionPreserved"])
        self.assertEqual(cell.patch_database(fixture.database())[0], client.db)
        self.assertIn("comparisons 69-72/72", output)
        self.assertNotIn("1000.0", output)
        self.assertNotIn("-20.0", output)
        receipt = next(json.loads(v) for k, v in fs.files.items() if k.endswith("numerical-check-summary.json"))
        self.assertEqual(preflight, receipt)
        self.assertFalse(any(cell.ORIGINAL_MODEL in path for _, path, _ in client.calls))

    def test_query_failures_and_syntax_stop_before_backup_or_write_with_safe_details(self):
        for ordinal in (1, 2, 73, 144):
            result, client, fs, evaluate, output = self.run_cell(evaluate=Evaluate("query_error", ordinal))
            self.assertEqual("TEST_R177_PREFLIGHT_STOPPED", result["Stage"])
            self.assertEqual("MEMORY_LIMIT", result["Preflight"]["Error"]["ErrorCategory"])
            self.assertEqual(ordinal, len(evaluate.scalars))
            self.assertFalse(fixture.mock.writes(client) or fs.files)
            self.assertNotIn("Traceback", output)
            self.assertFalse(result["ModelWriteRequested"])
        result, client, fs, evaluate, _ = self.run_cell(evaluate=Evaluate("syntax_error"))
        self.assertEqual("Candidate", result["Preflight"]["QueryKind"])
        self.assertEqual("QUERY_SYNTAX_OR_DEFINITION", result["Preflight"]["Error"]["ErrorCategory"])
        self.assertEqual(2, len(evaluate.scalars))
        self.assertFalse(fixture.mock.writes(client) or fs.files)

    def test_bad_blank_mismatch_incomplete_and_nonfinite_never_write(self):
        for mode in ("bad_scope", "mismatch", "all_blank", "blank_to_zero", "plans_only", "incomplete", "infinity", "boolean", "string", "source_changed"):
            with self.subTest(mode=mode):
                result, client, fs, _, _ = self.run_cell(evaluate=Evaluate(mode))
                self.assertEqual("TEST_R177_PREFLIGHT_STOPPED", result["Stage"])
                self.assertFalse(fixture.mock.writes(client) or fs.files)
        result, _, _, _, _ = self.run_cell(evaluate=Evaluate("within_tolerance"))
        self.assertEqual("TEST_R177_UPDATED", result["Stage"])

    def test_nan_and_none_blank_match_zero_stays_numeric(self):
        self.assertIsNone(cell.scalar_value([{"Value": None}], {}))
        self.assertIsNone(cell.scalar_value([{"Value": float("nan")}], {}))
        self.assertEqual(0.0, cell.scalar_value([{"Value": 0}], {}))
        for rows in ([], [{"Wrong": PRIVATE}], [{"Value": 0}, {"Value": 1}]):
            with self.assertRaises(cell.PreflightStopped):
                cell.scalar_value(rows, {})

    def test_source_snapshot_is_order_independent_and_rejects_missing_or_nan(self):
        rows = [{"Revision": PRIVATE + str(i), "Priority": 1, "Rank": 1, "Ties": 1} for i in range(2)]
        self.assertEqual(cell.source_metadata_digest(rows), cell.source_metadata_digest(rows[::-1]))
        for bad in ([], [{"Revision": None}], [{"Revision": PRIVATE, "Priority": float("nan"), "Rank": 1, "Ties": 1}]):
            with self.assertRaises(cell.PreflightStopped):
                cell.source_metadata_digest(bad)

    def test_identity_expression_mapping_concurrency_backup_guards_are_preserved(self):
        for mode in ("identity", "unknown_expression", "missing_cloud", "concurrent", "connection_change", "truncated", "put_false", "copy_false"):
            with self.subTest(mode=mode):
                client, fs, evaluate = fixture.Client(), fixture.mock.FileSystem(), Evaluate()
                if mode == "identity":
                    client.identity["id"] = cell.ORIGINAL_MODEL
                elif mode == "unknown_expression":
                    client.db["model"]["tables"][0]["measures"][0]["expression"] = "UNKNOWN"
                elif mode == "missing_cloud":
                    client.connections = []
                elif mode in ("concurrent", "connection_change"):
                    setattr(client, mode, True)
                else:
                    setattr(fs, mode, True)
                    if mode == "truncated":
                        client.db["model"]["expressions"][0]["expression"] = "SYNTHETIC é" * 20000
                with self.assertRaises((RuntimeError, ValueError)):
                    self.run_cell(client, fs, evaluate)
                self.assertFalse(fixture.mock.writes(client))

    def test_readback_ambiguity_never_retries_or_refreshes_and_already_installed_does_not_write(self):
        for mode in ("bad_readback", "mapping_after_write"):
            client = fixture.Client()
            setattr(client, mode, True)
            result, client, fs, _, _ = self.run_cell(client)
            self.assertEqual("TEST_R177_READBACK_NEEDS_REVIEW", result["Stage"])
            self.assertEqual(1, len(fixture.mock.writes(client)))
            self.assertFalse(any(k.endswith("success.json") for k in fs.files))
            self.assertFalse(result["RefreshRequested"] or result["ReportPublished"])
        client = fixture.Client()
        client.arrays = True
        self.assertEqual("TEST_R177_UPDATED", self.run_cell(client)[0]["Stage"])
        client = fixture.Client()
        client.db, _ = cell.patch_database(client.db)
        result, client, _, evaluate, _ = self.run_cell(client)
        self.assertEqual("TEST_R177_ALREADY_INSTALLED", result["Stage"])
        self.assertFalse(fixture.mock.writes(client) or evaluate.calls)
        client = fixture.Client()
        client.reject = True
        with self.assertRaises(RuntimeError):
            self.run_cell(client)
        self.assertEqual(1, len(fixture.mock.writes(client)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
