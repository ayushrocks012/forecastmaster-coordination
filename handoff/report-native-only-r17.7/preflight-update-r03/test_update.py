"""Synthetic-only coverage for definition-checked variance and TEST guards."""
import ast
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("r177_r03_builder_tests", HERE / "build_cell.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
cell = builder.load("r177_r03_cell_tests", HERE / "UPDATE EXISTING TEST TO R17.7 R03.py")
old_tests = builder.load("r177_r02_tests_for_r03", HERE.parent / "preflight-update-r02/test_update.py")
fixture = old_tests.fixture
PRIVATE = old_tests.PRIVATE


class Evaluate(old_tests.Evaluate):
    def __call__(self, **kwargs):
        dax = kwargs["dax_string"]
        if not dax.startswith("DEFINE\n") and 'ROW("Value",CALCULATE([N Variance %]' in dax:
            raise AssertionError("Legacy combined variance must not be queried or reported passed.")
        if self.mode == "cancelled" and len(self.scalars) + 1 == self.fail_scalar and dax.startswith(("EVALUATE ROW", "DEFINE\n")):
            self.calls.append(kwargs)
            self.scalars.append(kwargs)
            raise old_tests.FabricAdomdException("The operation was cancelled. " + PRIVATE)
        frame = super().__call__(**kwargs)
        if self.mode == "variance_mismatch" and dax.startswith("DEFINE\n") and 'ROW("Value",CALCULATE([N Variance %]' in dax:
            return fixture.Frame([{"[Value]": 52.0}])
        return frame


class Tests(unittest.TestCase):
    def run_cell(self, client=None, fs=None, evaluate=None):
        fixture.mock.repair = cell
        client, fs, evaluate = client or fixture.Client(), fs or fixture.mock.FileSystem(), evaluate or Evaluate()
        stream = io.StringIO()
        with redirect_stdout(stream), patch.object(cell.time, "sleep", lambda _: None):
            result = cell.run(client, fs, evaluate)
        self.assertNotIn(PRIVATE, stream.getvalue())
        return result, client, fs, evaluate, stream.getvalue()

    def test_generated_cell_python310_and_frozen_model_patch_equivalence(self):
        source = (HERE / "UPDATE EXISTING TEST TO R17.7 R03.py").read_text()
        self.assertEqual(builder.build(), source)
        tree = ast.parse(source, feature_version=(3, 10))
        old_tree = ast.parse((HERE.parent / "preflight-update-r02/UPDATE EXISTING TEST TO R17.7 R02.py").read_text())
        old_functions = {n.name: ast.dump(n) for n in old_tree.body if isinstance(n, ast.FunctionDef)}
        new_functions = {n.name: ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef)}
        self.assertEqual(["run", "verify_numeric"], sorted(n for n in old_functions if old_functions[n] != new_functions[n]))
        for name in ("EDITS", "EXPECTED_HASHES", "FITS", "HELPER_PATCHES", "RELATIONSHIP", "NUMERIC_OVERRIDES"):
            self.assertEqual(getattr(old_tests.cell, name), getattr(cell, name))

    def test_exact_original_variance_definitions_required_and_line_arrays_allowed(self):
        database = fixture.database()
        cell.verify_variance_contract(database)
        measures = database["model"]["tables"][0]["measures"]
        for name in cell.VARIANCE_CONTRACT:
            measure = next(m for m in measures if m["name"] == name)
            text = measure["expression"]
            measure["expression"] = text.splitlines()
            cell.verify_variance_contract(database)
            measure["expression"] = text + " + 0"
            with self.assertRaises(cell.PreflightStopped):
                cell.verify_variance_contract(database)
            measure["expression"] = text
        with self.assertRaises(cell.PreflightStopped):
            cell.verify_variance_contract({"model": {"tables": []}})

    def test_variance_contract_blank_zero_sign_and_zero_result_boundaries(self):
        cases = [(None, 100., None), (100., None, None), (None, 0., None),
                 (100., 0., None), (-100., -0., None), (100., -100., 2.),
                 (-100., 100., -2.), (-50., -100., 0.5), (0., -100., 1.),
                 (0., 100., -1.), (100., 100., 0.), (-100., -100., 0.)]
        for plan, benchmark, expected in cases:
            with self.subTest(plan=plan, benchmark=benchmark):
                self.assertEqual(expected, cell.expected_variance_percent(plan, benchmark, {}))
        with self.assertRaises(cell.PreflightStopped):
            cell.expected_variance_percent(1e308, -1e308, {})

    def test_54_direct_18_derived_vs_72_actual_candidates_before_single_write(self):
        result, client, fs, evaluate, output = self.run_cell()
        self.assertEqual("TEST_R177_UPDATED", result["Stage"])
        self.assertEqual("R03", result["UpdaterRevision"])
        evidence = result["NumericalPreflight"]
        self.assertEqual((72, 54, 18, 72, 126, 3), tuple(evidence[k] for k in (
            "Checks", "DirectOriginalScalarReads", "DerivedOriginalVarianceComparisons",
            "ActualCandidateScalarReads", "ScalarQueries", "MetadataQueries")))
        self.assertIs(False, evidence["OriginalVariancePercentMeasureExecuted"])
        self.assertTrue(evidence["OriginalVarianceFormulaVerified"])
        self.assertEqual(129, len(evaluate.calls))
        self.assertEqual(54, sum(not c["dax_string"].startswith("DEFINE\n") for c in evaluate.scalars))
        self.assertEqual(18, sum('ROW("Value",CALCULATE([N Variance %]' in c["dax_string"] for c in evaluate.scalars))
        self.assertTrue(all(c["dataset"] == cell.TEST_MODEL and c["workspace"] == cell.WORKSPACE
                            and c["use_readwrite_connection"] is False for c in evaluate.calls))
        writes = fixture.mock.writes(client)
        self.assertEqual(1, len(writes))
        self.assertEqual({"allowPurgeData": False}, writes[0][1]["options"])
        self.assertEqual(cell.patch_database(fixture.database())[0], client.db)
        self.assertFalse(result["RefreshRequested"] or result["ReportPublished"] or result["OriginalModelWriteRequested"])
        self.assertIn("Do not refresh", result["NextStep"])
        self.assertNotIn("1000.0", output)
        self.assertNotIn("-20.0", output)
        receipt = next(json.loads(v) for k, v in fs.files.items() if k.endswith("numerical-check-summary.json"))
        self.assertEqual(evidence, receipt)

    def test_candidate_variance_error_is_not_derived_or_ignored(self):
        result, client, fs, evaluate, _ = self.run_cell(evaluate=Evaluate("variance_mismatch"))
        self.assertEqual("TEST_R177_PREFLIGHT_STOPPED", result["Stage"])
        self.assertEqual("NUMERICAL_MISMATCH", result["Preflight"]["Reason"])
        self.assertEqual(3, result["Preflight"]["Checkpoint"]["CheckIndex"])
        self.assertEqual("VERIFIED_FORMULA_FROM_P_B", result["Preflight"]["Checkpoint"]["BaselineEvidence"])
        self.assertEqual(5, len(evaluate.scalars))
        self.assertFalse(fixture.mock.writes(client) or fs.files)

    def test_derived_variance_blank_and_zero_results_remain_distinct_in_live_comparison(self):
        class VarianceBoundary(Evaluate):
            def __init__(self, benchmark, percent):
                super().__init__()
                self.benchmark, self.percent = benchmark, percent

            def __call__(self, **kwargs):
                frame = super().__call__(**kwargs)
                dax = kwargs["dax_string"]
                if 'ROW("Value",CALCULATE([N Benchmark]' in dax:
                    return fixture.Frame([{"[Value]": self.benchmark}])
                if 'ROW("Value",CALCULATE([N Variance %]' in dax:
                    return fixture.Frame([{"[Value]": self.percent}])
                return frame

        for benchmark, percent in ((0.0, 0.0), (1000.0, None)):
            result, client, fs, _, _ = self.run_cell(evaluate=VarianceBoundary(benchmark, percent))
            self.assertEqual("NUMERICAL_MISMATCH", result["Preflight"]["Reason"])
            self.assertEqual(3, result["Preflight"]["Checkpoint"]["CheckIndex"])
            self.assertFalse(fixture.mock.writes(client) or fs.files)
        result, _, _, _, _ = self.run_cell(evaluate=VarianceBoundary(1000.0, 0.0))
        self.assertEqual("TEST_R177_UPDATED", result["Stage"])

    def test_any_cancellation_stops_before_backup_or_write_and_reports_elapsed(self):
        for index in (1, 2, 5, 47, 126):
            with self.subTest(index=index):
                result, client, fs, evaluate, output = self.run_cell(evaluate=Evaluate("cancelled", index))
                self.assertEqual("TEST_R177_PREFLIGHT_STOPPED", result["Stage"])
                self.assertEqual(index, len(evaluate.scalars))
                self.assertEqual("CANCELLED", result["Preflight"]["Error"]["ErrorCategory"])
                self.assertGreaterEqual(result["Preflight"]["ElapsedMs"], 0)
                self.assertFalse(fixture.mock.writes(client) or fs.files)
                self.assertNotIn("Traceback", output)

    def test_bad_results_and_source_metadata_change_never_write(self):
        for mode in ("bad_scope", "mismatch", "all_blank", "blank_to_zero", "plans_only",
                     "incomplete", "infinity", "boolean", "string", "source_changed"):
            with self.subTest(mode=mode):
                result, client, fs, _, _ = self.run_cell(evaluate=Evaluate(mode))
                self.assertEqual("TEST_R177_PREFLIGHT_STOPPED", result["Stage"])
                self.assertFalse(fixture.mock.writes(client) or fs.files)

    def test_partial_known_new_variance_body_refuses_derived_baseline_before_queries(self):
        client = fixture.Client()
        measure = next(m for m in client.db["model"]["tables"][0]["measures"] if m["name"] == "N Variance %")
        measure["expression"] = cell.EDITS["N Variance %"]
        result, client, fs, evaluate, _ = self.run_cell(client)
        self.assertEqual("TEST_R177_PREFLIGHT_STOPPED", result["Stage"])
        self.assertEqual("BASELINE_VARIANCE_CONTRACT_CHANGED", result["Preflight"]["Reason"])
        self.assertFalse(evaluate.calls or fixture.mock.writes(client) or fs.files)

    def test_identity_mapping_definition_concurrency_and_backup_guards_preserved(self):
        for mode in ("identity", "unknown_expression", "missing_cloud", "concurrent", "connection_change", "truncated", "put_false", "copy_false"):
            with self.subTest(mode=mode):
                client, fs = fixture.Client(), fixture.mock.FileSystem()
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
                    self.run_cell(client, fs)
                self.assertFalse(fixture.mock.writes(client))

    def test_full_readback_and_already_installed_do_not_retry_or_refresh(self):
        for mode in ("bad_readback", "mapping_after_write"):
            client = fixture.Client()
            setattr(client, mode, True)
            result, client, fs, _, _ = self.run_cell(client)
            self.assertEqual("TEST_R177_READBACK_NEEDS_REVIEW", result["Stage"])
            self.assertEqual(1, len(fixture.mock.writes(client)))
            self.assertFalse(any(k.endswith("success.json") for k in fs.files))
        client = fixture.Client()
        client.arrays = True
        self.assertEqual("TEST_R177_UPDATED", self.run_cell(client)[0]["Stage"])
        client = fixture.Client()
        client.db, _ = cell.patch_database(client.db)
        result, client, _, evaluate, _ = self.run_cell(client)
        self.assertEqual("TEST_R177_ALREADY_INSTALLED", result["Stage"])
        self.assertFalse(evaluate.calls or fixture.mock.writes(client))


if __name__ == "__main__":
    unittest.main(verbosity=2)
