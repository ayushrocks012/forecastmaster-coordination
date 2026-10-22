"""Produce the standalone readable Fabric code cell from reviewed local sources."""
import importlib.util
import inspect
import json
import pprint
from pathlib import Path
import model

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("r02",HERE.parent/"report-native-onelake-r17.1/measure-repair-r02/REPAIR TEST FEED.py")
r02=importlib.util.module_from_spec(spec);spec.loader.exec_module(r02)


def build():
    source='''"""One NEW Fabric cell: upgrade ONLY the existing native TEST to R17.2.
Back up and verify the whole definition privately, preserve the cloud connection,
update native reporting measures/helpers. No company sales query, explicit refresh,
source change, production write, report publish or model recreation.
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
    for name in ("WORKSPACE","TEST_MODEL","TEST_NAME","ORIGINAL_MODEL","LAKEHOUSE","BASE","ITEM"):
        source+=name+" = "+repr(getattr(r02,name))+"\n"
    baseline={n:model.expression_hash(m["expression"]) for n,m in model.original_measures().items()}
    for name,value in (("BASELINE_HASHES",baseline),("REVISED",model.revised_measures()),
                       ("HELPERS",[model.period_table(),model.headline_table()])):
        source+='\n'+name+' = '+pprint.pformat(value,width=100,sort_dicts=False)+'\n'
    for function in (model.expression_hash,r02.digest,r02.complete,r02.read_definition,r02.database_part,r02.connection_state,r02.verified_backup):
        source+=inspect.getsource(function)+"\n\n"
    patch=inspect.getsource(model.patch_database).replace('old = original_measures()','old = BASELINE_HASHES')
    patch=patch.replace('revised = revised_measures()','revised = REVISED')
    patch=patch.replace('expression_hash(old[name]["expression"])','old[name]')
    patch=patch.replace('(period_table(),headline_table())','HELPERS')
    source+=patch+'\n\n'
    run=inspect.getsource(r02.run)
    run=run.replace('sum(t["name"].startswith("fm_native_") for t in tables) != 20',
                    'sum(t["name"].startswith("fm_native_") for t in tables) not in {20,22}')
    run=run.replace('fixed, changed = repair_database(database)','fixed, changed = patch_database(database)')
    run=run.replace('TEST_FEED_ALREADY_CLEAN','TEST_R172_ALREADY_INSTALLED').replace('TEST_FEED_REPAIRED','TEST_R172_UPDATED')
    run=run.replace('"RepairVersion": "R02"','"Revision": "R17.2"')
    run=run.replace('"MeasuresChanged": len(changed)','"NativeObjectsChanged": len(changed)')
    run=run.replace('Native-R171-Feed-R02/','Native-R172/')
    run=run.replace('NEXT: Refresh now ONCE on this TEST semantic model, then send its history result.',
                    'NEXT: Refresh this TEST semantic model ONCE. If Completed without warnings, open the NEW R17.2 TEST report. Keep production R16.6 unchanged.')
    source+=run+'\n\nif __name__ == "__main__":\n    import sempy.fabric as fabric\n    import notebookutils\n    run(fabric.FabricRestClient(), notebookutils.fs)\n'
    return source


if __name__=="__main__":
    path=HERE/"UPDATE EXISTING TEST TO R17.2.py"
    path.write_text(build(),encoding="utf-8")
    print(path)
