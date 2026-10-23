"""Fabric-free synthetic checks of read-only recovery, preservation and redaction."""
import ast
import base64
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load("probe_builder", HERE / "build_probe.py")
probe = load("readonly_probe", HERE / "CHECK R17.4 READBACK.py")
updater = load("frozen_updater", HERE.parent / "UPDATE EXISTING TEST TO R17.4.py")
PRIVATE = "COMPANY_PRIVATE_VALUE_à_💼_DO_NOT_PRINT"


def database():
    return {"name": "Synthetic", "compatibilityLevel": 1604, "model": {
        "culture": "en-GB", "roles": [{"name": PRIVATE, "modelPermission": "read"}],
        "expressions": [{"name": "Source", "kind": "m", "expression": PRIVATE * 3000}],
        "relationships": [{"name": "Rel", "fromTable": "A", "toTable": "B"}],
        "tables": [{"name": "fm_native_measures", "measures": deepcopy(list(updater.EXPECTED.values()))}]
                  + [{"name": "fm_native_stub" + str(i)} for i in range(21)]
                  + [{"name": "fm_review_facts", "partitions": [{"name": "Fact", "mode": "directLake",
                        "source": {"type": "entity", "expressionSource": "Source", "entityName": "Fact"}}]}]}}


def pack(db, pretty=False):
    return {"parts": [{"path": "model.bim", "payloadType": "InlineBase64",
                       "payload": base64.b64encode(json.dumps(db, ensure_ascii=False,
                                                              indent=2 if pretty else None).encode()).decode()},
                      {"path": ".platform", "payloadType": "InlineBase64", "payload": "e30="}]}


class Response:
    def __init__(self, body=None, status=200, headers=None):
        self.body, self.status_code, self.headers = body, status, headers or {}

    def json(self):
        return deepcopy(self.body)


class Client:
    def __init__(self, candidate):
        self.calls, self.reads = [], 0
        self.identity = {"id": probe.TEST_MODEL, "displayName": probe.TEST_NAME, "type": "SemanticModel"}
        self.snapshots = [deepcopy(candidate), deepcopy(candidate)]
        self.mapping = [{"id": PRIVATE, "connectivityType": "ShareableCloud"}]
        self.second_mapping = None
        self.connection_reads = 0
        self.async_reads = False

    def post(self, path):
        self.calls.append(("POST", path))
        assert path == probe.BASE + "/getDefinition?format=TMSL", "A mutation was attempted"
        value = {"definition": self.snapshots[min(self.reads, 1)]}
        self.reads += 1
        if self.async_reads:
            self.pending = value
            return Response(status=202, headers={"x-ms-operation-id": "00000000-0000-0000-0000-000000000001",
                                                  "Retry-After": "0"})
        return Response(value)

    def get(self, path):
        self.calls.append(("GET", path))
        if path == probe.ITEM:
            return Response(self.identity)
        if path == probe.ITEM + "/connections":
            value = self.second_mapping if self.connection_reads and self.second_mapping is not None else self.mapping
            self.connection_reads += 1
            return Response({"value": value})
        if path == "/v1/operations/00000000-0000-0000-0000-000000000001":
            return Response({"status": "Succeeded"})
        if path == "/v1/operations/00000000-0000-0000-0000-000000000001/result":
            return Response(self.pending)
        raise AssertionError("Unknown API call")


class FileSystem:
    def __init__(self, before, candidate, mapping):
        self.files = {name: json.dumps(value, ensure_ascii=False).encode()
                      for name, value in zip(probe.BACKUP_FILES, (before, candidate, mapping))}
        self.copies = []
        self.truncate, self.copy_false, self.change_second_copy = False, False, False

    def ls(self, path):
        assert path == probe.BACKUP
        return [SimpleNamespace(name=name, size=len(raw)) for name, raw in self.files.items()]

    def cp(self, source, destination, recursive):
        assert source.startswith(probe.BACKUP + "/") and destination.startswith("file:") and not recursive
        self.copies.append((source, destination))
        if self.copy_false:
            return False
        raw = self.files[source.rsplit("/", 1)[-1]]
        if self.truncate:
            raw = raw[:100]
        elif self.change_second_copy and len(self.copies) % 2 == 0:
            raw = raw.replace(b'"parts"', b'"pzrts"', 1)
        Path(unquote(urlparse(destination).path)).write_bytes(raw)
        return True


def fixture():
    old = database()
    new, _ = updater.patch_database(old)
    client = Client(pack(new))
    return client, FileSystem(pack(old), pack(new), client.mapping), new


def execute(client=None, fs=None):
    if client is None:
        client, fs, _ = fixture()
    output = io.StringIO()
    with redirect_stdout(output), patch.object(probe.time, "sleep", lambda _: None):
        result = probe.safe_run(client, fs)
    assert PRIVATE not in output.getvalue()
    return result, output.getvalue(), client, fs


class Tests(unittest.TestCase):
    def test_frozen_cell_reproducible_and_compiles(self):
        source = (HERE / "CHECK R17.4 READBACK.py").read_text(encoding="utf-8")
        self.assertEqual(source, builder.build())
        compile(source, "read_only_probe", "exec")
        self.assertEqual(len(probe.RULES), 49)
        self.assertEqual(sum(len(hashes) == 2 for fields in probe.RULES.values() for hashes in fields.values()), 21)

    def test_exact_candidate_and_mapping_verify_without_writes(self):
        result, _, client, fs = execute()
        self.assertEqual(result["Stage"], "TEST_R174_READBACK_VERIFIED")
        self.assertTrue(result["CloudConnectionMatchesBackup"])
        self.assertTrue(result["BackupCandidateContainsOnlyDeclaredRepair"])
        self.assertTrue(result["KnownNativeExpressionAndFormatFingerprintsMatch"])
        self.assertEqual(client.reads, 2)
        self.assertEqual(client.connection_reads, 2)
        self.assertEqual(len(fs.copies), 6)
        self.assertTrue(all(Path(unquote(urlparse(dst).path)).exists() is False for _, dst in fs.copies))
        self.assertTrue(all(path.endswith("/getDefinition?format=TMSL") for method, path in client.calls if method == "POST"))
        for field in ("ModelWriteRequested", "CompanyAmountsQueried", "RefreshRequested", "ReportPublished"):
            self.assertFalse(result[field])

    def test_json_whitespace_transport_does_not_mask_metadata_change(self):
        client, fs, new = fixture()
        client.snapshots = [pack(new, pretty=True)] * 2
        result, *_ = execute(client, fs)
        self.assertFalse(result["RawDefinitionMatch"])
        self.assertTrue(result["ModelJsonExactMatch"])
        self.assertEqual(result["Stage"], "TEST_R174_READBACK_VERIFIED")

    def test_identical_lines_do_not_hide_another_metadata_change(self):
        client, fs, new = fixture()
        measure = new["model"]["tables"][0]["measures"][0]
        measure["expression"] = measure["expression"].split("\n")
        new["model"]["roles"][0]["modelPermission"] = "none"
        client.snapshots = [pack(new)] * 2
        result, *_ = execute(client, fs)
        self.assertEqual(result["Stage"], "TEST_R174_READBACK_NEEDS_REVIEW")
        self.assertTrue(result["KnownNativeExpressionAndFormatFingerprintsMatch"])
        self.assertEqual(result["DifferenceSummary"]["Counts"]["IDENTICAL_DAX_LINE_REPRESENTATION"], 1)

    def test_current_missing_helper_or_measure_inventory_reports_review(self):
        for kind in ("table", "measure"):
            client, fs, new = fixture()
            if kind == "table": new["model"]["tables"].pop(1)
            else: new["model"]["tables"][0]["measures"].pop()
            client.snapshots = [pack(new)] * 2
            result, *_ = execute(client, fs)
            self.assertEqual(result["Stage"], "TEST_R174_READBACK_NEEDS_REVIEW")
            self.assertFalse(result["NativeInventoryMatchesExpected"])
            self.assertGreater(result["DifferenceSummary"]["Unexplained"], 0)

    def test_dax_string_to_identical_lines_is_classified_without_ignoring_properties(self):
        client, fs, new = fixture()
        for measure in new["model"]["tables"][0]["measures"]:
            measure["expression"] = measure["expression"].split("\n")
            if "formatStringDefinition" in measure:
                fmt = measure["formatStringDefinition"]
                fmt["expression"] = fmt["expression"].split("\n")
        client.snapshots = [pack(new)] * 2
        result, *_ = execute(client, fs)
        self.assertFalse(result["ModelJsonExactMatch"])
        self.assertEqual(result["DifferenceSummary"]["Counts"], {"IDENTICAL_DAX_LINE_REPRESENTATION": 69})
        self.assertEqual(result["Stage"], "TEST_R174_READBACK_VERIFIED")

    def test_structural_source_security_format_and_order_changes_never_pass(self):
        modes = ("source", "role", "relationship", "numeric", "format", "annotation", "helper",
                 "extra_property", "part", "table_order", "measure_order", "line_endings", "bool_vs_int")
        for mode in modes:
            with self.subTest(mode=mode):
                client, fs, new = fixture()
                model = new["model"]
                if mode == "source": model["tables"][-1]["partitions"][0]["source"]["entityName"] = PRIVATE
                elif mode == "role": model["roles"][0]["modelPermission"] = PRIVATE
                elif mode == "relationship": model["relationships"][0]["toTable"] = PRIVATE
                elif mode == "numeric": model["tables"][0]["measures"][0]["expression"] = PRIVATE
                elif mode == "format":
                    measure = next(m for m in model["tables"][0]["measures"] if "formatStringDefinition" in m)
                    measure["formatStringDefinition"]["expression"] = PRIVATE
                elif mode == "annotation": model["tables"][0]["measures"][0]["annotations"] = [{"name": PRIVATE, "value": PRIVATE}]
                elif mode == "helper": model["tables"][1]["columns"] = [{"name": PRIVATE}]
                elif mode == "extra_property": new[PRIVATE] = PRIVATE
                elif mode == "table_order": model["tables"].reverse()
                elif mode == "measure_order": model["tables"][0]["measures"].reverse()
                elif mode == "line_endings":
                    measure = next(m for m in model["tables"][0]["measures"] if "\n" in m["expression"])
                    measure["expression"] = measure["expression"].replace("\n", "\r\n")
                elif mode == "bool_vs_int": new["compatibilityLevel"] = True
                current = pack(new)
                if mode == "part": current["parts"][1]["payload"] = base64.b64encode(PRIVATE.encode()).decode()
                client.snapshots = [current] * 2
                result, output, *_ = execute(client, fs)
                self.assertEqual(result["Stage"], "TEST_R174_READBACK_NEEDS_REVIEW")
                self.assertGreater(result["DifferenceSummary"]["Unexplained"], 0)
                self.assertNotIn(PRIVATE, output)

    def test_not_installed_candidate_does_not_pass(self):
        client, fs, _ = fixture()
        client.snapshots = [pack(database())] * 2
        result, *_ = execute(client, fs)
        self.assertEqual(result["Stage"], "TEST_R174_READBACK_NEEDS_REVIEW")

    def test_changed_mapping_is_reported_even_when_model_matches(self):
        client, fs, _ = fixture()
        client.mapping = [{"id": PRIVATE + "CHANGED", "connectivityType": "ShareableCloud"}]
        result, *_ = execute(client, fs)
        self.assertEqual(result["Stage"], "TEST_R174_READBACK_NEEDS_REVIEW")
        self.assertTrue(result["ModelJsonExactMatch"])
        self.assertFalse(result["CloudConnectionMatchesBackup"])

    def test_concurrent_definition_or_connection_change_prevents_pass(self):
        for mapping in (False, True):
            client, fs, _ = fixture()
            if mapping:
                client.second_mapping = []
            else:
                client.snapshots[0] = pack(database())
            result, *_ = execute(client, fs)
            self.assertFalse(result["TwoMetadataSnapshotsStable"])
            self.assertEqual(result["Stage"], "TEST_R174_READBACK_NEEDS_REVIEW")

    def test_backups_reject_unknown_candidate_or_before_and_non_model_parts(self):
        for which in (0, 1):
            for kind in ("source", "expression", "part", "missing_format", "format_metadata"):
                with self.subTest(which=which, kind=kind):
                    client, fs, _ = fixture()
                    name = probe.BACKUP_FILES[which]
                    obj = json.loads(fs.files[name])
                    db = probe.unpack(obj)[1]
                    if kind == "source": db["model"]["roles"][0]["modelPermission"] = PRIVATE
                    elif kind == "expression": db["model"]["tables"][0]["measures"][0]["expression"] = PRIVATE
                    elif kind in {"missing_format", "format_metadata"}:
                        measure = next(m for m in db["model"]["tables"][0]["measures"] if "formatStringDefinition" in m)
                        if kind == "missing_format": del measure["formatStringDefinition"]
                        else: measure["formatStringDefinition"]["extra"] = PRIVATE
                    obj = pack(db)
                    if kind == "part": obj["parts"][1]["payload"] = base64.b64encode(PRIVATE.encode()).decode()
                    fs.files[name] = json.dumps(obj).encode()
                    result, _, client, _ = execute(client, fs)
                    self.assertEqual(result["Stage"], "TEST_R174_READBACK_CHECK_STOPPED")
                    self.assertEqual(client.reads, 0)

    def test_no_preview_read_and_full_length_stable_copy_required(self):
        for mode in ("truncate", "copy_false", "change_second_copy"):
            client, fs, _ = fixture()
            setattr(fs, mode, True)
            result, _, client, _ = execute(client, fs)
            self.assertEqual(result["Stage"], "TEST_R174_READBACK_CHECK_STOPPED")
            self.assertEqual(client.reads, 0)

    def test_bad_identity_or_backup_cannot_read_model_or_write(self):
        for mode in ("identity", "missing_backup", "bad_json", "duplicate_key", "bad_base64", "duplicate_part"):
            client, fs, _ = fixture()
            if mode == "identity": client.identity["id"] = "WRONG"
            elif mode == "missing_backup": del fs.files[probe.BACKUP_FILES[0]]
            elif mode == "bad_json": fs.files[probe.BACKUP_FILES[0]] = b"{broken"
            elif mode == "duplicate_key": fs.files[probe.BACKUP_FILES[0]] = b'{"parts":[],"parts":[]}'
            else:
                obj = json.loads(fs.files[probe.BACKUP_FILES[0]])
                if mode == "bad_base64": obj["parts"][0]["payload"] = "INVALID_BASE64"
                else: obj["parts"].append(deepcopy(obj["parts"][0]))
                fs.files[probe.BACKUP_FILES[0]] = json.dumps(obj).encode()
            result, _, client, _ = execute(client, fs)
            self.assertEqual(result["Stage"], "TEST_R174_READBACK_CHECK_STOPPED")
            self.assertEqual(client.reads, 0)

    def test_readonly_route_allowlist_blocks_writes_and_other_models(self):
        client, _, _ = fixture()
        reader = probe.MetadataReader(client)
        for path in (probe.BASE + "/updateDefinition", probe.BASE + "/refreshes", "/v1/workspaces/OTHER/items"):
            with self.assertRaises(probe.CheckStopped): reader.post(path)
            with self.assertRaises(probe.CheckStopped): reader.get(path)
        self.assertEqual(client.calls, [])
        source = (HERE / "CHECK R17.4 READBACK.py").read_text(encoding="utf-8")
        calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute)]
        self.assertFalse(any(node.func.attr in {"put", "head", "delete", "patch", "mkdirs"} for node in calls))

    def test_difference_output_is_bounded_without_skipping_total_or_leaking_values(self):
        expected = {"private " + str(i): PRIVATE for i in range(200)}
        result = probe.compare(expected, {})
        self.assertEqual(result["Total"], 200)
        self.assertEqual(result["Unexplained"], 200)
        self.assertEqual(len(result["Details"]), probe.DETAIL_LIMIT)
        self.assertTrue(result["DetailsTruncated"])
        self.assertNotIn("private", json.dumps(result))
        self.assertNotIn(PRIVATE, json.dumps(result))

    def test_real_difference_is_prioritized_over_many_representation_details(self):
        client, fs, new = fixture()
        for measure in new["model"]["tables"][0]["measures"]:
            measure["expression"] = measure["expression"].split("\n")
        new["model"]["tables"][-1]["partitions"][0]["source"]["expressionSource"] = PRIVATE
        client.snapshots = [pack(new)] * 2
        result, *_ = execute(client, fs)
        self.assertEqual(result["Stage"], "TEST_R174_READBACK_NEEDS_REVIEW")
        self.assertEqual(result["DifferenceSummary"]["Total"], 50)
        self.assertEqual(result["DifferenceSummary"]["Details"][0]["Kind"], "VALUE_CHANGED")

    def test_type_diagnostics_show_only_type_names(self):
        result = probe.compare({"expression": PRIVATE}, {"expression": [PRIVATE]})
        detail = result["Details"][0]
        self.assertEqual(detail["Kind"], "TYPE_CHANGED")
        self.assertEqual((detail["ExpectedType"], detail["ObservedType"]), ("str", "list"))
        self.assertNotIn(PRIVATE, json.dumps(result))

    def test_exceptions_do_not_print_private_api_bodies(self):
        client, fs, _ = fixture()
        client.get = lambda path: (_ for _ in ()).throw(RuntimeError(PRIVATE))
        result, output, *_ = execute(client, fs)
        self.assertEqual(result["ReasonCode"], "METADATA_OR_BACKUP_READ_FAILED")
        self.assertNotIn(PRIVATE, output)

    def test_async_metadata_reads_still_make_zero_updates(self):
        client, fs, _ = fixture()
        client.async_reads = True
        result, _, client, _ = execute(client, fs)
        self.assertEqual(result["Stage"], "TEST_R174_READBACK_VERIFIED")
        self.assertEqual(len([1 for method, _ in client.calls if method == "POST"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
