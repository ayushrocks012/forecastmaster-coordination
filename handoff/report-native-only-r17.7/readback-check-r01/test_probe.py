"""Synthetic tests for read-only whole-definition and inferred-name verification."""
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
spec = importlib.util.spec_from_file_location("r177_readback_builder_tests", HERE / "build_probe.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
probe = builder.load("r177_readonly_probe_tests", HERE / "CHECK R17.7 READBACK.py")
legacy = builder.load("r174_readonly_fixtures_for_r177", HERE.parent.parent / "report-native-only-r17.4/readback-check-r01/test_probe.py")
legacy.probe = probe
fixture = builder.load("r177_model_fixture_for_readback", HERE.parent / "test_revision.py")
PRIVATE = legacy.PRIVATE


def receipt():
    return {"Revision": "R03", "Checks": 72, "NumericComparisons": 72, "BlankComparisons": 0, "Mismatches": 0,
            "DirectOriginalScalarReads": 54, "DerivedOriginalVarianceComparisons": 18,
            "ActualCandidateScalarReads": 72, "OriginalVarianceFormulaVerified": True,
            "OriginalVariancePercentMeasureExecuted": False, "NumericBenchmarks": 18,
            "NumericFutureTrends": 9, "ScalarQueries": 126, "MetadataQueries": 3,
            "SourceSelectionMetadataStable": True, "CompanyAmountValuesPrintedOrStored": False,
            "ValidationMethod": "54_DIRECT_BASELINE_AND_18_VERIFIED_FORMULA_EXPECTATIONS_VS_72_ACTUAL_CANDIDATES",
            "ComparisonCountsByMetric": {m: {"Numeric": 24, "Blank": 0} for m in ("market", "ef", "share")}}


def sample():
    before = fixture.database()
    before["model"]["expressions"][0]["expression"] = PRIVATE * 6000
    candidate = builder.UPDATE.patch_database(before)[0]
    observed = deepcopy(candidate)
    for table in observed["model"]["tables"]:
        if table["name"] == "fm_native_measures":
            for measure in table["measures"]:
                if measure["name"] in set(probe.EDIT_HASHES) | set(probe.FIT_OBJECT_HASHES):
                    measure["expression"] = measure["expression"].split("\n")
        if table["name"] in probe.HELPER_SPECS:
            table["partitions"][0]["source"]["expression"] = table["partitions"][0]["source"]["expression"].split("\n")
            for col in table["columns"]:
                if col["name"] in {c["name"] for c in probe.HELPER_SPECS[table["name"]]["Columns"]}:
                    col["isNameInferred"] = True
    client = legacy.Client(legacy.pack(observed))
    fs = legacy.FileSystem(legacy.pack(before), legacy.pack(candidate), client.mapping)
    fs.files["numerical-check-summary.json"] = json.dumps(receipt()).encode()
    return client, fs, candidate, observed


def column(database, table="fm_native_files", name="FileChoiceLabel"):
    return next(c for t in database["model"]["tables"] if t["name"] == table for c in t["columns"] if c["name"] == name)


def execute(client=None, fs=None):
    legacy.probe = probe
    if client is None:
        client, fs, _, _ = sample()
    output = io.StringIO()
    with redirect_stdout(output), patch.object(probe.time, "sleep", lambda _: None):
        result = probe.safe_run(client, fs)
    assert PRIVATE not in output.getvalue()
    return result, client, fs, output.getvalue()


class Tests(unittest.TestCase):
    def test_generated_cell_python310_hash_mapping_and_no_amount_query_or_writers(self):
        source = (HERE / "CHECK R17.7 READBACK.py").read_text()
        self.assertEqual(builder.build(), source)
        tree = ast.parse(source, feature_version=(3, 10))
        self.assertEqual("id:d89bc9cf5133", "id:" + probe.hashlib.sha256(b"isNameInferred").hexdigest()[:12])
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
                self.assertNotIn(name, {"put", "mkdirs", "head", "evaluate_dax", "refresh_dataset", "refresh_semantic_model"})
        self.assertNotIn("updateDefinition", source)
        self.assertEqual(49, len(probe.INPUT_HASHES))
        self.assertEqual(2, len(probe.FIT_OBJECT_HASHES))

    def test_exact_reported_3_additions_and_19_representations_verify_read_only(self):
        result, client, fs, output = execute()
        self.assertEqual("TEST_R177_READBACK_VERIFIED", result["Stage"])
        self.assertEqual(3, result["RawUnexplainedDifferenceCount"])
        self.assertEqual(0, result["DifferenceSummaryAfterStrictCheck"]["Unexplained"])
        self.assertEqual(19, result["DifferenceSummaryAfterStrictCheck"]["Total"])
        self.assertEqual(3, len(result["InferredNameMetadata"]))
        self.assertTrue(all(row["Accepted"] and row["ObservedBoolean"] is True for row in result["InferredNameMetadata"]))
        self.assertTrue(result["TwoMetadataSnapshotsStable"] and result["CloudConnectionMatchesBackup"])
        self.assertTrue(result["BackupPairVerifiedAgainstFrozenR177"] and result["NumericalPreflightReceiptVerified"])
        self.assertEqual(2, client.reads)
        self.assertEqual(8, len(fs.copies))
        self.assertTrue(all(path.endswith("/getDefinition?format=TMSL") for method, path in client.calls if method == "POST"))
        for key in ("ModelWriteRequested", "OriginalModelWriteRequested", "CompanyAmountsQueried", "RefreshRequested", "ReportPublished"):
            self.assertIs(False, result[key])
        self.assertNotIn("PRIVATE", output)

    def test_false_nonboolean_and_wrong_column_shape_are_not_normalized(self):
        for mode in ("false", "integer", "string", "source", "type"):
            with self.subTest(mode=mode):
                client, fs, _, observed = sample()
                col = column(observed)
                if mode == "false": col["isNameInferred"] = False
                if mode == "integer": col["isNameInferred"] = 1
                if mode == "string": col["isNameInferred"] = PRIVATE
                if mode == "source": col["sourceColumn"] = PRIVATE
                if mode == "type": col["type"] = "data"
                client.snapshots = [legacy.pack(observed)] * 2
                result, *_ = execute(client, fs)
                self.assertEqual("TEST_R177_READBACK_NEEDS_REVIEW", result["Stage"])
                self.assertGreater(result["DifferenceSummaryAfterStrictCheck"]["Unexplained"], 0)

    def test_flags_elsewhere_and_source_security_formula_format_order_changes_never_pass(self):
        for mode in ("other_flag", "role", "source", "formula", "format", "sort", "order", "helper", "part"):
            with self.subTest(mode=mode):
                client, fs, _, observed = sample()
                model = observed["model"]
                if mode == "other_flag":
                    old_col = next(t for t in model["tables"] if t["name"] == "fm_native_files")["columns"][0]
                    old_col["isNameInferred"] = not old_col.get("isNameInferred", False)
                if mode == "role": model["roles"][0]["modelPermission"] = PRIVATE
                if mode == "source": model["expressions"][0]["expression"] = PRIVATE
                if mode == "formula": model["tables"][0]["measures"][0]["expression"] = PRIVATE
                if mode == "format": column(observed, name="ImportedAtUTC")["formatString"] = PRIVATE
                if mode == "sort": column(observed)["sortByColumn"] = PRIVATE
                if mode == "order": model["tables"].reverse()
                if mode == "helper": next(t for t in model["tables"] if t["name"] == "fm_native_files")["partitions"][0]["source"]["expression"] = PRIVATE
                packed = legacy.pack(observed)
                if mode == "part": packed["parts"][-1]["payload"] = "UFJJVkFURQ=="
                client.snapshots = [packed] * 2
                result, *_ = execute(client, fs)
                self.assertEqual("TEST_R177_READBACK_NEEDS_REVIEW", result["Stage"])

    def test_backup_candidate_or_preflight_tampering_stops_without_metadata_acceptance(self):
        for mode in ("source", "column", "fit", "body", "receipt", "bool_vs_int"):
            with self.subTest(mode=mode):
                client, fs, candidate, _ = sample()
                if mode == "source": candidate["model"]["roles"][0]["modelPermission"] = PRIVATE
                if mode == "column": column(candidate)["isNameInferred"] = True
                if mode == "fit": candidate["model"]["tables"][0]["measures"][-1]["isHidden"] = False
                if mode == "body": candidate["model"]["tables"][0]["measures"][0]["expression"] = PRIVATE
                fs.files["definition-candidate.json"] = json.dumps(legacy.pack(candidate)).encode()
                if mode in {"receipt", "bool_vs_int"}:
                    value = receipt()
                    if mode == "receipt": value["Mismatches"] = 1
                    else: value["SourceSelectionMetadataStable"] = 1
                    fs.files["numerical-check-summary.json"] = json.dumps(value).encode()
                result, *_ = execute(client, fs)
                self.assertEqual("TEST_R177_READBACK_CHECK_STOPPED", result["Stage"])
                self.assertEqual(0, client.reads)

    def test_two_snapshot_instability_or_changed_cloud_mapping_refuses_verification(self):
        for mode in ("model", "mapping"):
            client, fs, _, observed = sample()
            if mode == "model":
                observed["model"]["culture"] = "en-US"
                client.snapshots[1] = legacy.pack(observed)
            else:
                client.second_mapping = [{"id": PRIVATE + "CHANGED", "connectivityType": "ShareableCloud"}]
            result, *_ = execute(client, fs)
            self.assertEqual("TEST_R177_READBACK_NEEDS_REVIEW", result["Stage"])
            self.assertFalse(result["TwoMetadataSnapshotsStable"])

    def test_full_utf8_backup_reads_reject_truncation_failure_change_and_missing_files(self):
        for mode in ("truncate", "copy_false", "change_second_copy", "missing"):
            client, fs, _, _ = sample()
            if mode == "missing": fs.files.pop("numerical-check-summary.json")
            else: setattr(fs, mode, True)
            result, *_ = execute(client, fs)
            self.assertEqual("TEST_R177_READBACK_CHECK_STOPPED", result["Stage"])
            self.assertEqual(0, client.reads)

    def test_identity_and_forbidden_routes_fail_closed_and_async_metadata_works(self):
        client, fs, _, _ = sample()
        client.identity["id"] = "e7af2967-7725-4108-a170-9e490d4e35bb"
        result, *_ = execute(client, fs)
        self.assertEqual("TEST_IDENTITY_MISMATCH", result["ReasonCode"])
        self.assertFalse(fs.copies)
        reader = probe.MetadataReader(client)
        with self.assertRaises(probe.CheckStopped): reader.post(probe.BASE + "/updateDefinition")
        with self.assertRaises(probe.CheckStopped): reader.get(probe.BASE + "/refreshes")
        client, fs, _, _ = sample()
        client.async_reads = True
        result, *_ = execute(client, fs)
        self.assertEqual("TEST_R177_READBACK_VERIFIED", result["Stage"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
