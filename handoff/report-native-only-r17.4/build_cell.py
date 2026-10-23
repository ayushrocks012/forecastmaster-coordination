"""Freeze one readable TEST-only cell, reusing the qualified R02 backup guards."""
import importlib.util
import inspect
from pathlib import Path
import pprint
import model

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("r174_backup", HERE.parent / "report-native-onelake-r17.1/measure-repair-r02/REPAIR TEST FEED.py")
R02 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R02)


def build():
    source = '''"""One NEW cell: native R17.4 formatting/summary-display repair, EXISTING TEST only.
No source amounts, arithmetic rewrite, new helpers, connection change or publication.
Full private backup and cloud/concurrency guards are retained from R02.
"""
import base64
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
        source += name + " = " + repr(getattr(R02, name)) + "\n"
    old, revised = model.repairs()
    for name, value in (("EXPECTED", old), ("REPLACEMENTS", revised)):
        source += "\n" + name + " = " + pprint.pformat(value, width=110, sort_dicts=False) + "\n"
    for function in (model.BASELINE.expression_hash, R02.digest, R02.complete, R02.read_definition,
                     R02.database_part, R02.connection_state, R02.verified_backup):
        source += inspect.getsource(function) + "\n\n"
    patch = inspect.getsource(model.patch_database).replace("expected, replacements = repairs()", "expected, replacements = EXPECTED, REPLACEMENTS")
    source += patch + "\n\n"
    run = inspect.getsource(R02.run)
    run = run.replace('sum(t["name"].startswith("fm_native_") for t in tables) != 20',
                      'sum(t["name"].startswith("fm_native_") for t in tables) != 22')
    run = run.replace("Expected existing R17.1 TEST helper tables", "Expected existing R17.2/R17.3 TEST helper tables")
    run = run.replace("repair_database(database)", "patch_database(database)")
    run = run.replace("TEST_FEED_ALREADY_CLEAN", "TEST_R174_ALREADY_INSTALLED").replace("TEST_FEED_REPAIRED", "TEST_R174_UPDATED")
    run = run.replace('"RepairVersion": "R02"', '"Revision": "R17.4"')
    run = run.replace("Native-R171-Feed-R02/", "Native-R174-Format-Display/")
    run = run.replace("NEXT: Refresh now ONCE on this TEST semantic model, then send its history result.",
                      "NEXT: Open the NEW R17.4 TEST PBIP. No source-data refresh or Publish step is requested. Keep production R16.6 unchanged.")
    source += run + '\n\nif __name__ == "__main__":\n    import sempy.fabric as fabric\n    import notebookutils\n    run(fabric.FabricRestClient(), notebookutils.fs)\n'
    return source


if __name__ == "__main__":
    path = HERE / "UPDATE EXISTING TEST TO R17.4.py"
    path.write_text(build(), encoding="utf-8")
    print(path)
