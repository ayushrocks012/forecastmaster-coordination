"""Synthetic-only guards for the read-only diagnostic, not DAX execution."""
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
SOURCE = HERE / "CHECK R17.7 PREFLIGHT.py"
spec = importlib.util.spec_from_file_location("preflight_probe_r01", SOURCE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
old_spec = importlib.util.spec_from_file_location("frozen_r177_numeric", HERE.parent / "numeric_check.py")
old = importlib.util.module_from_spec(old_spec)
old_spec.loader.exec_module(old)
PRIVATE = "PRIVATE_SCOPE_FILE_PATH_TOKEN_AND_AMOUNT_987654321.125"


class Frame:
    def __init__(self, rows):
        self.rows = rows

    def to_dict(self, orient):
        assert orient == "records"
        return deepcopy(self.rows)


class FabricAdomdException(Exception):
    pass


class Evaluate:
    def __init__(self, fail_at=None, error=None, value=0.0):
        self.calls = []
        self.fail_at, self.error, self.value = fail_at, error, value
        self.scope = [{"[Country]": PRIVATE + '"Country', "[Cycle]": "2026-10",
                       "[Driver]": PRIVATE + '"Driver'}]

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail_at == len(self.calls):
            raise self.error
        return Frame(self.scope if len(self.calls) == 1 else [{"[Value]": self.value}])


class Tests(unittest.TestCase):
    def run_probe(self, evaluate):
        output = io.StringIO()
        with redirect_stdout(output):
            result = probe.run(evaluate)
        text = output.getvalue()
        self.assertNotIn(PRIVATE, text)
        self.assertNotIn("987654321.125", text)
        self.assertEqual(result, json.loads(text[text.index("{\n"):]))
        return result, text

    def test_four_reads_are_fixed_test_read_only_no_override_or_bundle(self):
        evaluate = Evaluate()
        result, _ = self.run_probe(evaluate)
        self.assertEqual("R177_SMALL_BASELINE_READS_COMPLETED", result["Stage"])
        self.assertEqual(5, len(evaluate.calls))
        self.assertEqual(old.METADATA_QUERY, evaluate.calls[0]["dax_string"])
        for call in evaluate.calls:
            self.assertEqual(probe.TEST_MODEL, call["dataset"])
            self.assertEqual(probe.WORKSPACE, call["workspace"])
            self.assertIs(False, call["use_readwrite_connection"])
            self.assertEqual(0, call["verbose"])
            self.assertNotIn("DEFINE", call["dax_string"])
            self.assertNotIn("UNION", call["dax_string"])
        self.assertIs(False, result["ModelWriteRequested"])
        self.assertIs(False, result["RefreshRequested"])
        self.assertIs(False, result["NumericalParityVerified"])
        self.assertIs(False, result["CandidateOverridesEvaluated"])

    def test_original_suppressed_error_can_be_recovered_without_query(self):
        try:
            try:
                raise FabricAdomdException("Query (17, 3) The syntax for ')' is incorrect. " + PRIVATE)
            except FabricAdomdException:
                raise RuntimeError("Read-only numerical preflight unavailable; no model write. Error type: FabricAdomdException") from None
        except RuntimeError as captured:
            evaluate = Evaluate()
            with patch.object(probe.sys, "last_value", captured, create=True), \
                 patch.object(probe.sys, "last_exc", None, create=True):
                result, _ = self.run_probe(evaluate)
        self.assertEqual("R177_PREFLIGHT_PREVIOUS_ERROR_CAPTURED", result["Stage"])
        self.assertEqual([], evaluate.calls)
        self.assertEqual("QUERY_SYNTAX_OR_DEFINITION", result["PreviousPreflightError"]["Error"]["ErrorCategory"])
        self.assertEqual([], result["Checks"])

    def test_unrelated_or_unclassified_prior_exception_does_not_block_reads(self):
        prefix = "Read-only numerical preflight unavailable; no model write. Error type: FabricAdomdException"
        for captured in (RuntimeError(PRIVATE), RuntimeError(prefix)):
            with patch.object(probe.sys, "last_value", captured, create=True), \
                 patch.object(probe.sys, "last_exc", None, create=True):
                evaluate = Evaluate()
                result, _ = self.run_probe(evaluate)
                self.assertEqual("R177_SMALL_BASELINE_READS_COMPLETED", result["Stage"])
                self.assertEqual(5, len(evaluate.calls))

    def test_each_failure_stops_and_exposes_only_safe_memory_details(self):
        message = ("rsQueryMemoryLimitExceeded. Resource Governance: consumed memory 10240 MB, "
                   "memory limit 10240 MB. " + PRIVATE)
        for fail_at in range(1, 6):
            with self.subTest(fail_at=fail_at):
                evaluate = Evaluate(fail_at=fail_at, error=FabricAdomdException(message))
                result, output = self.run_probe(evaluate)
                self.assertEqual(fail_at, len(evaluate.calls))
                self.assertEqual("R177_PREFLIGHT_DIAGNOSTIC_QUERY_FAILED", result["Stage"])
                check = result["Checks"][-1]
                self.assertEqual("QUERY_FAILED", check["Status"])
                detail = check["Error"]
                self.assertEqual("MEMORY_LIMIT", detail["ErrorCategory"])
                self.assertEqual(["rsQueryMemoryLimitExceeded"], detail["KnownCodes"])
                self.assertEqual({"Value": 10240, "Unit": "MB"}, detail["MemoryLimit"])
                self.assertEqual("FabricAdomdException", detail["ExceptionFamily"])
                self.assertNotIn("Resource Governance:", output)

    def test_nested_dotnet_errors_capture_syntax_positions_without_echo(self):
        outer = FabricAdomdException(PRIVATE)
        inner = RuntimeError(PRIVATE)
        inner.Message = "Query (8, 21) The syntax for ')' is incorrect. " + PRIVATE
        outer.InnerException = inner
        outer.Errors = [inner]
        inner.InnerException = outer
        result = probe.safe_error(outer)
        self.assertEqual("QUERY_SYNTAX_OR_DEFINITION", result["ErrorCategory"])
        self.assertIn({"Line": 8, "Column": 21}, result["QueryPositions"])
        self.assertNotIn(PRIVATE, json.dumps(result))

    def test_timeout_access_processing_throttling_and_unknown(self):
        cases = [("The command timed out", "TIMEOUT"),
                 ("Access is denied", "ACCESS_OR_AUTHENTICATION"),
                 ("This table has not been processed", "PROCESSING_REQUIRED"),
                 ("Requests throttled", "CAPACITY_OR_THROTTLING"),
                 (PRIVATE, "UNCLASSIFIED")]
        for raw, category in cases:
            with self.subTest(category=category):
                evaluate = Evaluate(fail_at=2, error=FabricAdomdException(raw + " " + PRIVATE))
                result, output = self.run_probe(evaluate)
                self.assertEqual(category, result["Checks"][-1]["Error"]["ErrorCategory"])
                self.assertNotIn("Traceback", output)

    def test_suppressed_python_chain_and_unknown_class_name_do_not_leak(self):
        PrivateClass = type(PRIVATE, (Exception,), {})
        outer = PrivateClass(PRIVATE)
        outer.__cause__ = RuntimeError("rsQueryTimeoutExceeded " + PRIVATE)
        outer.__suppress_context__ = True
        result = probe.safe_error(outer)
        self.assertEqual("TIMEOUT", result["ErrorCategory"])
        self.assertEqual("OtherException", result["ExceptionFamily"])
        self.assertNotIn(PRIVATE, json.dumps(result))

    def test_zero_is_numeric_none_nan_are_blank_without_numeric_output(self):
        for value, state in [(0.0, "NUMERIC"), (987654321.125, "NUMERIC"),
                             (None, "BLANK"), (float("nan"), "BLANK")]:
            with self.subTest(state=state, kind=type(value).__name__):
                result, output = self.run_probe(Evaluate(value=value))
                self.assertEqual([state] * 4, [x["ValueState"] for x in result["Checks"][1:]])
                self.assertNotIn(str(987654321.125), output)

    def test_bad_value_or_shape_stops_after_first_scalar(self):
        for value in (True, PRIVATE, float("inf"), complex(1, 2)):
            evaluate = Evaluate(value=value)
            result, _ = self.run_probe(evaluate)
            self.assertEqual("R177_PREFLIGHT_DIAGNOSTIC_UNEXPECTED_RESULT", result["Stage"])
            self.assertEqual(2, len(evaluate.calls))
        self.assertEqual("UNEXPECTED_RESULT_SHAPE", probe.value_state([]))
        self.assertEqual("UNEXPECTED_RESULT_SHAPE", probe.value_state([{"Wrong": PRIVATE}]))

    def test_invalid_metadata_refuses_scalar_reads(self):
        cases = [[], [{"Country": "ZZ"}],
                 [{"Country": "ZZ", "Cycle": "2026-13", "Driver": PRIVATE}],
                 [{"Country": "ZZ", "Cycle": "0000-01", "Driver": PRIVATE}],
                 [{"Country": "ZZ", "Cycle": "9999-01", "Driver": PRIVATE}],
                 [{"Country": None, "Cycle": "2026-10", "Driver": PRIVATE}]]
        for scope in cases:
            evaluate = Evaluate()
            evaluate.scope = scope
            result, _ = self.run_probe(evaluate)
            self.assertEqual("R177_PREFLIGHT_DIAGNOSTIC_SCOPE_UNAVAILABLE", result["Stage"])
            self.assertEqual(1, len(evaluate.calls))

    def test_scalar_filters_match_frozen_baseline_and_escape_scope(self):
        scope = {"Country": 'Syn"Country', "Cycle": "2026-10", "Driver": 'Syn"Driver'}
        original = old.build_query(scope, {})
        for _, measure, future in probe.PROBES:
            dax = probe.scalar_query(scope, measure, future)
            self.assertIn('Syn""Country', dax)
            self.assertIn('Syn""Driver', dax)
            # Each standalone CALCULATE is unchanged from its original ROW member.
            scalar = dax.removeprefix('EVALUATE ROW("Value",').removesuffix(')')
            self.assertIn(scalar, original)
        with self.assertRaisesRegex(ValueError, "Unknown diagnostic measure"):
            probe.scalar_query(scope, PRIVATE, False)

    def test_python310_compatible_and_no_mutating_client_or_file_calls(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"), feature_version=(3, 10))
        blocked = {"post", "put", "delete", "patch", "mkdirs", "write", "write_text", "write_bytes",
                   "refresh_dataset", "refresh_semantic_model", "FabricRestClient"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
                self.assertNotIn(name, blocked)


if __name__ == "__main__":
    unittest.main()
