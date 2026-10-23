"""Build read-only verification with frozen public-code fingerprints only."""
import importlib.util
import inspect
import hashlib
from pathlib import Path
import pprint
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


OLD = load("r174_reader_for_r177", HERE.parent.parent / "report-native-only-r17.4/readback-check-r01/probe.py")
UPDATE = load("r177_r03_frozen_for_readback", HERE.parent / "preflight-update-r03/UPDATE EXISTING TEST TO R17.7 R03.py")
PROBE = load("r177_readback_r01", HERE / "probe.py")
BACKUP = (
    "abfss://f5cb5742-9a7c-4337-a4c0-952706dddf0b@onelake.dfs.fabric.microsoft.com/"
    "d6e33ebd-67b1-420a-8d84-c3a0d04d8b21/Files/ForecastMasterRefreshState/"
    "report-upgrades/Native-R177-Performance-Files-R03/"
    "20261023T185452-34a80b74-e9c7-4749-af9f-d5a835b23e5e"
)


def build():
    source = '''"""ONE NEW cell in ForecastMaster_GM_Setup. Already-updated TEST metadata only.
Read exact R03 backup and verify three inferred-name flags plus the WHOLE model.
No model/backup write, amount query, refresh, rollback, publishing or retries.
"""
import base64
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import quote
from uuid import UUID

'''
    def exact_hash(value):
        return hashlib.sha256(OLD.expression_text(value).encode("utf-8")).hexdigest()

    helper_specs = {name: {"InputHash": OLD.known_expression_hash(before),
                           "OutputHash": exact_hash(after), "Columns": columns}
                    for name, (before, after, columns) in UPDATE.HELPER_PATCHES.items()}
    fits = {name: OLD.digest({"name": name, "expression": body, "displayFolder": "Native performance", "isHidden": True})
            for name, body in UPDATE.FITS.items()}
    constants = {name: getattr(UPDATE, name) for name in ("WORKSPACE", "TEST_MODEL", "TEST_NAME", "BASE", "ITEM")}
    constants.update(BACKUP=BACKUP, BACKUP_FILES=("definition-before.json", "definition-candidate.json",
                     "connections-before.json", "numerical-check-summary.json"), MAX_BACKUP_BYTES=64*1024*1024,
                     DETAIL_LIMIT=40, INPUT_HASHES=UPDATE.EXPECTED_HASHES,
                     EDIT_HASHES={name: exact_hash(body) for name, body in UPDATE.EDITS.items()},
                     FIT_OBJECT_HASHES=fits, HELPER_SPECS=helper_specs,
                     RULES={name: {} for name in set(UPDATE.EXPECTED_HASHES) | set(UPDATE.FITS)},
                     SAFE_KEYS=sorted(OLD.SAFE_KEYS | {"isNameInferred", "fm_native_files", "fm_native_lines",
                                                       "ImportedAtUTC", "FileChoiceLabel", "SeriesLabel"}))
    for name, value in constants.items():
        source += name + " = " + pprint.pformat(value, width=110, sort_dicts=True) + "\n\n"
    source += "class CheckStopped(RuntimeError):\n    pass\n\n"
    for function in (OLD.require, OLD.digest, OLD.parse_json, OLD.expression_text, OLD.known_expression_hash,
                     OLD.MetadataReader, OLD.definition, OLD.connections, OLD.read_backups, OLD.unpack,
                     OLD.safe_token, OLD.compare, UPDATE.compare_with_calculated,
                     PROBE.named, PROBE.exact_expression_hash, PROBE.verify_backup_pair, PROBE.verify_preflight,
                     PROBE.inferred_name_normalization, PROBE.run, PROBE.safe_run):
        source += inspect.getsource(function).replace('prefix="fm-r174-readonly-"', 'prefix="fm-r177-readback-"') + "\n\n"
    return source + '''if __name__ == "__main__":
    import sempy.fabric as fabric
    import notebookutils
    safe_run(fabric.FabricRestClient(), notebookutils.fs)
'''


if __name__ == "__main__":
    (HERE / "CHECK R17.7 READBACK.py").write_text(build(), encoding="utf-8")
