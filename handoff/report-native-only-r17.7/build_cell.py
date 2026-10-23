"""Build one guarded cell; numerical comparison precedes any TEST write."""
import importlib.util
import inspect
from pathlib import Path
import pprint

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODEL = load("r177_model", HERE / "model.py")
OLD = load("r176_builder", HERE.parent / "report-native-only-r17.6/build_cell.py")
CHECK = load("r177_check", HERE / "numeric_check.py")
BACKUP, PROBE = OLD.BACKUP, OLD.PROBE


def run(client, fs, evaluate):
    if TEST_MODEL == ORIGINAL_MODEL or not BASE.endswith("/" + TEST_MODEL):
        raise ValueError("Invalid TEST target; no write.")
    response = client.get(ITEM)
    if response.status_code != 200:
        raise RuntimeError("TEST identity unavailable; no write.")
    identity = response.json()
    if any(identity.get(key) != value for key, value in {
            "id": TEST_MODEL, "displayName": TEST_NAME, "type": "SemanticModel"}.items()):
        raise ValueError("TEST identity mismatch; no write.")
    before = read_definition(client)
    database = database_part(before)
    fixed, changed = patch_database(database)
    connections = connection_state(client)
    if not any(c.get("connectivityType") == "ShareableCloud" for c in connections):
        raise ValueError("Explicit TEST cloud mapping missing; no write.")
    if not changed:
        result = {"Stage": "TEST_R177_ALREADY_INSTALLED", "ModelWriteRequested": False,
                  "RefreshRequested": False, "ReportPublished": False,
                  "NextStep": "If new helper columns were already processed, open R17.7. Otherwise refresh TEST once."}
        print(json.dumps(result, indent=2), flush=True)
        return result
    # Virtual DEFINE MEASURE overrides do not update the model. Any inability
    # to compare, all-blank result, mismatch or compile failure refuses a write.
    numeric = verify_numeric(evaluate, WORKSPACE, TEST_MODEL, NUMERIC_OVERRIDES)
    after = deepcopy(before)
    part = next(p for p in after["parts"] if p["path"] == "model.bim")
    part["payload"] = base64.b64encode(json.dumps(fixed, ensure_ascii=False).encode()).decode()
    folder = (f"abfss://{WORKSPACE}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE}/Files/"
              "ForecastMasterRefreshState/report-upgrades/Native-R177-Performance-Files/"
              + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + str(uuid4()))
    fs.mkdirs(folder)
    for name, value in (("definition-before.json", before), ("definition-candidate.json", after),
                        ("connections-before.json", connections), ("numerical-check-summary.json", numeric)):
        verified_backup(fs, folder + "/" + name, value)
    print("Verified private TEST backup: " + folder, flush=True)
    if digest(read_definition(client)) != digest(before) or connection_state(client) != connections:
        raise RuntimeError("TEST changed concurrently; no model write.")
    complete(client, client.post(BASE + "/updateDefinition", json={"definition": after, "options": {"allowPurgeData": False}}))
    received = read_definition(client)
    diff = compare_with_calculated(unpack(after)[0], unpack(received)[0])
    mapping_ok = connection_state(client) == connections
    ok = diff["Unexplained"] == 0 and mapping_ok
    result = {"Stage": "TEST_R177_UPDATED" if ok else "TEST_R177_READBACK_NEEDS_REVIEW", "TestModelID": TEST_MODEL,
              "MetadataChanged": changed, "NumericalPreflight": numeric,
              "FullDefinitionMatchesApartFromIdenticalDaxLineRepresentation": diff["Unexplained"] == 0,
              "DifferenceSummary": diff, "CloudConnectionPreserved": mapping_ok, "PrivateBackup": folder,
              "ModelWriteRequested": True, "OriginalModelWriteRequested": False,
              "ReadOnlyCompanyAggregateChecks": True, "CompanyAmountValuesPrintedOrStored": False,
              "RefreshRequested": False, "ReportPublished": False,
              "NextStep": ("Refresh ONLY this existing TEST once for new metadata columns, then open R17.7 and compare report timings." if ok
                           else "Keep backup and send this result. Do not retry, refresh or publish.")}
    if ok: fs.put(folder + "/success.json", json.dumps(result, indent=2), False)
    print(json.dumps(result, indent=2), flush=True)
    return result


def build():
    source = '''"""ONE NEW cell in ForecastMaster_GM_Setup: EXISTING TEST only.
First compares 72 aggregate results using read-only virtual DAX measures.
No model write on unavailable/incomplete/mismatching/blank-only checks.
Company values stay in notebook memory; output/backups contain check counts only.
Then verified private backup, scoped update, full readback; no purge or publish.
"""
import base64
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import quote
from uuid import UUID, uuid4

'''
    for name in ("WORKSPACE", "TEST_MODEL", "TEST_NAME", "ORIGINAL_MODEL", "LAKEHOUSE", "BASE", "ITEM"):
        source += name + " = " + repr(getattr(BACKUP, name)) + "\n"
    overrides = MODEL.performance_edits() | MODEL.fit_measures()
    for name, value in (("EXPECTED_HASHES", MODEL.fingerprints()), ("EDITS", MODEL.replacements()),
                        ("FITS", MODEL.fit_measures()), ("HELPER_PATCHES", MODEL.helper_patches()),
                        ("RELATIONSHIP", MODEL.RELATIONSHIP), ("NUMERIC_OVERRIDES", overrides),
                        ("METADATA_QUERY", CHECK.METADATA_QUERY), ("SAFE_KEYS", sorted(PROBE.SAFE_KEYS)), ("DETAIL_LIMIT", 40)):
        source += name + " = " + pprint.pformat(value, width=110, sort_dicts=False) + "\n\n"
    source += "RULES = EXPECTED_HASHES\nclass CheckStopped(RuntimeError):\n    pass\n\n"
    for function in (MODEL.expression_hash, BACKUP.digest, BACKUP.complete, BACKUP.read_definition,
                     BACKUP.database_part, BACKUP.connection_state, BACKUP.verified_backup,
                     PROBE.require, PROBE.parse_json, PROBE.expression_text, PROBE.unpack, PROBE.safe_token, PROBE.compare,
                     CHECK.build_query, CHECK.records, CHECK.verify_numeric):
        source += inspect.getsource(function) + "\n\n"
    compare = inspect.getsource(OLD.compare_with_calculated).replace(
        '{"fm_native_columns", "fm_native_start_month", "fm_native_end_month"}',
        '{"fm_native_columns", "fm_native_start_month", "fm_native_end_month", "fm_native_files", "fm_native_lines"}')
    source += compare + "\n\n"
    patch = inspect.getsource(MODEL.patch_database).replace("fingerprints(), replacements(), fit_measures()", "EXPECTED_HASHES, EDITS, FITS")
    patch = patch.replace("helper_patches().items()", "HELPER_PATCHES.items()")
    source += patch + "\n\n" + inspect.getsource(run)
    return source + '''\n\nif __name__ == "__main__":
    import sempy.fabric as fabric
    import notebookutils
    run(fabric.FabricRestClient(),notebookutils.fs,fabric.evaluate_dax)
'''


if __name__ == "__main__":
    (HERE / "UPDATE EXISTING TEST TO R17.7.py").write_text(build(), encoding="utf-8")
