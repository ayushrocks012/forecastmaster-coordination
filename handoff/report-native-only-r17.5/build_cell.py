"""Freeze one readable two-measure TEST update with qualified backup/readback."""
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


MODEL = load("r175_model", HERE / "model.py")
BACKUP = load("backup_r02", HERE.parent / "report-native-onelake-r17.1/measure-repair-r02/REPAIR TEST FEED.py")
PROBE = load("readonly_r01", HERE.parent / "report-native-only-r17.4/readback-check-r01/CHECK R17.4 READBACK.py")


def run(client, fs):
    if TEST_MODEL == ORIGINAL_MODEL or not BASE.endswith("/" + TEST_MODEL):
        raise ValueError("Invalid TEST target; no write.")
    identity_response = client.get(ITEM)
    if identity_response.status_code != 200:
        raise RuntimeError("TEST identity unavailable; no write.")
    identity = identity_response.json()
    if any(identity.get(key) != value for key,value in {
            "id":TEST_MODEL,"displayName":TEST_NAME,"type":"SemanticModel"}.items()):
        raise ValueError("TEST identity mismatch; no write.")
    before = read_definition(client)
    database = database_part(before)
    if sum(t["name"].startswith("fm_native_") for t in database["model"]["tables"]) != 22:
        raise ValueError("Unexpected helper inventory; no write.")
    fixed, changed = patch_database(database)
    connections = connection_state(client)
    if not any(c.get("connectivityType") == "ShareableCloud" for c in connections):
        raise ValueError("Explicit TEST cloud mapping missing; no write.")
    if not changed:
        result = {"Stage":"TEST_R175_ALREADY_INSTALLED","TestModelID":TEST_MODEL,
                  "ModelWriteRequested":False,"KnownChartExpressionsConfirmed":True,
                  "RefreshRequested":False,"ReportPublished":False,
                  "NextStep":"Open the R17.5 TEST PBIP; no refresh or publication requested."}
        print(json.dumps(result,indent=2),flush=True)
        return result
    after = deepcopy(before)
    part = next(p for p in after["parts"] if p["path"] == "model.bim")
    part["payload"] = base64.b64encode(json.dumps(fixed,ensure_ascii=False).encode()).decode()
    folder = (f"abfss://{WORKSPACE}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE}/Files/"
              "ForecastMasterRefreshState/report-upgrades/Native-R175-Chart-Presentation/"
              + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + str(uuid4()))
    fs.mkdirs(folder)
    for name, value in (("definition-before.json",before),("definition-candidate.json",after),
                        ("connections-before.json",connections)):
        verified_backup(fs,folder+"/"+name,value)
    print("Verified private TEST backup: "+folder,flush=True)
    if digest(read_definition(client)) != digest(before) or connection_state(client) != connections:
        raise RuntimeError("TEST changed concurrently; no write.")
    complete(client,client.post(BASE+"/updateDefinition",json={"definition":after,"options":{"allowPurgeData":False}}))
    received = read_definition(client)
    diff = compare(unpack(after)[0],unpack(received)[0])
    mapping_ok = connection_state(client) == connections
    ok = diff["Unexplained"] == 0 and mapping_ok
    result = {"Stage":"TEST_R175_UPDATED" if ok else "TEST_R175_READBACK_NEEDS_REVIEW",
              "TestModelID":TEST_MODEL,"MeasuresChanged":changed,
              "FullDefinitionMatchesApartFromIdenticalDaxLineRepresentation":diff["Unexplained"] == 0,
              "DifferenceSummary":diff,"CloudConnectionPreserved":mapping_ok,
              "PrivateBackup":folder,"ModelWriteRequested":True,
              "SourceAmountsQueried":False,"OriginalModelWriteRequested":False,
              "RefreshRequested":False,"ReportPublished":False,
              "NextStep":("Open the R17.5 TEST PBIP; no refresh or publication requested." if ok else
                          "Keep backup and send this result. Do not retry, refresh or publish.")}
    if ok:
        fs.put(folder+"/success.json",json.dumps(result,indent=2),False)
    print(json.dumps(result,indent=2),flush=True)
    return result


def build():
    source = '''"""ONE NEW cell: fix chart window selection and forecast join on EXISTING TEST.
Full private backup; exactly two chart expressions; source/amount logic unchanged.
No explicit refresh, new model, connection edit, purge or publication.
"""
import base64
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import quote
from uuid import UUID, uuid4

'''
    for name in ("WORKSPACE","TEST_MODEL","TEST_NAME","ORIGINAL_MODEL","LAKEHOUSE","BASE","ITEM"):
        source += name+" = "+repr(getattr(BACKUP,name))+"\n"
    for name,value in (("EXPECTED_HASHES",MODEL.fingerprints()),("EDITS",MODEL.replacements()),
                       ("SAFE_KEYS",sorted(PROBE.SAFE_KEYS)),("DETAIL_LIMIT",40)):
        source += name+" = "+pprint.pformat(value,width=110,sort_dicts=False)+"\n\n"
    source += "RULES = EXPECTED_HASHES\n"
    source += "class CheckStopped(RuntimeError):\n    pass\n\n"
    for function in (MODEL.expression_hash,BACKUP.digest,BACKUP.complete,BACKUP.read_definition,
                     BACKUP.database_part,BACKUP.connection_state,BACKUP.verified_backup,
                     PROBE.require,PROBE.parse_json,PROBE.expression_text,PROBE.unpack,PROBE.safe_token,PROBE.compare):
        source += inspect.getsource(function)+"\n\n"
    source += inspect.getsource(MODEL.patch_database).replace(
        "expected, edits = fingerprints(), replacements()", "expected, edits = EXPECTED_HASHES, EDITS")+"\n\n"
    source += inspect.getsource(run)
    return source+'\n\nif __name__ == "__main__":\n    import sempy.fabric as fabric\n    import notebookutils\n    run(fabric.FabricRestClient(),notebookutils.fs)\n'


if __name__ == "__main__":
    (HERE / "UPDATE EXISTING TEST TO R17.5.py").write_text(build(),encoding="utf-8")
