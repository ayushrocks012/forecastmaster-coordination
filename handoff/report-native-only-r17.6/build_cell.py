"""Freeze the self-contained existing-TEST update with full private verification."""
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


MODEL = load("r176_model", HERE / "model.py")
OLD = load("r175_builder", HERE.parent / "report-native-only-r17.5/build_cell.py")
BACKUP, PROBE = OLD.BACKUP, OLD.PROBE


def compare_with_calculated(expected, observed):
    """Only the three allowlisted calculated helpers gain line-array tolerance."""
    right = deepcopy(observed)
    left_db = next(p for p in expected["parts"] if p["path"] == "model.bim")["payload"]
    right_db = next(p for p in right["parts"] if p["path"] == "model.bim")["payload"]
    target_tables = {t["name"]: t for t in right_db["model"]["tables"]}
    representation_count = 0
    for table in left_db["model"]["tables"]:
        if table["name"] not in {"fm_native_columns", "fm_native_start_month", "fm_native_end_month"}:
            continue
        other = target_tables.get(table["name"], {})
        if len(table.get("partitions", [])) != 1 or len(other.get("partitions", [])) != 1:
            continue
        source = table["partitions"][0].get("source", {})
        received = other["partitions"][0].get("source", {})
        if source.get("type") != "calculated" or received.get("type") != "calculated":
            continue
        a, b = source.get("expression"), received.get("expression")
        if type(a) is not type(b):
            try:
                if expression_text(a) == expression_text(b):
                    received["expression"] = deepcopy(a)
                    representation_count += 1
            except CheckStopped:
                pass
    result = compare(expected, right)
    if representation_count:
        key = "IDENTICAL_CALCULATED_HELPER_LINE_REPRESENTATION"
        result["Counts"][key] = representation_count
        result["Total"] += representation_count
    return result


def build():
    source = '''"""Run ONE NEW cell in ForecastMaster_GM_Setup: EXISTING TEST only.
Adds two monthly dictionaries and a flat comparison label; gates display bodies.
Full private backup/readback, no purge, source arithmetic unchanged.
After success, refresh TEST ONCE to process new calculated metadata helpers.
This cell does not request a refresh or publish a report.
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
    for name in ("WORKSPACE", "TEST_MODEL", "TEST_NAME", "ORIGINAL_MODEL", "LAKEHOUSE", "BASE", "ITEM"):
        source += name + " = " + repr(getattr(BACKUP, name)) + "\n"
    for name, value in (("EXPECTED_HASHES", MODEL.fingerprints()), ("EDITS", MODEL.replacements()),
                        ("MONTH_TABLES", MODEL.month_tables()), ("COLUMN_PATCH", MODEL.column_patch()),
                        ("SAFE_KEYS", sorted(PROBE.SAFE_KEYS)), ("DETAIL_LIMIT", 40)):
        source += name + " = " + pprint.pformat(value, width=110, sort_dicts=False) + "\n\n"
    source += "RULES = EXPECTED_HASHES\nclass CheckStopped(RuntimeError):\n    pass\n\n"
    for function in (MODEL.expression_hash, BACKUP.digest, BACKUP.complete, BACKUP.read_definition,
                     BACKUP.database_part, BACKUP.connection_state, BACKUP.verified_backup,
                     PROBE.require, PROBE.parse_json, PROBE.expression_text, PROBE.unpack, PROBE.safe_token, PROBE.compare):
        source += inspect.getsource(function) + "\n\n"
    source += inspect.getsource(compare_with_calculated) + "\n\n"
    patch = inspect.getsource(MODEL.patch_database)
    patch = patch.replace("fingerprints(), replacements()", "EXPECTED_HASHES, EDITS")
    patch = patch.replace("month_tables()", "MONTH_TABLES").replace("column_patch()", "COLUMN_PATCH")
    source += patch + "\n\n"
    run = inspect.getsource(OLD.run).replace("R175", "R176").replace("R17.5", "R17.6")
    run = run.replace("diff = compare(", "diff = compare_with_calculated(")
    run = run.replace('!= 22:', 'not in (22,24):')
    run = run.replace("Native-R176-Chart-Presentation/", "Native-R176-Months-Summaries/")
    run = run.replace('"KnownChartExpressionsConfirmed":True,', '"KnownDisplayExpressionsAndHelpersConfirmed":True,"TESTRefreshRequiredForNewHelpers":True,')
    run = run.replace('"MeasuresChanged":changed,', '"MetadataChanged":changed,"TESTRefreshRequiredForNewHelpers":True,')
    run = run.replace("Open the R17.6 TEST PBIP; no refresh or publication requested.",
                      "Refresh this TEST model once to process new helpers, then open R17.6 TEST PBIP. If already processed, do not repeat refresh.")
    source += run
    return source + '''\n\nif __name__ == "__main__":
    import sempy.fabric as fabric
    import notebookutils
    run(fabric.FabricRestClient(),notebookutils.fs)
'''


if __name__ == "__main__":
    (HERE / "UPDATE EXISTING TEST TO R17.6.py").write_text(build(), encoding="utf-8")
