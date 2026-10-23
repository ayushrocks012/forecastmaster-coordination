"""Generate a self-contained R02 cell while preserving the frozen R17.7 patch."""
import importlib.util
import inspect
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


FROZEN = load("frozen_r177_builder_r02", HERE.parent / "build_cell.py")
CHECK = load("r177_split_numeric_r02", HERE / "numeric_check.py")
DIAGNOSTIC = load("r177_diagnostic_r01", HERE.parent / "preflight-check-r01/CHECK R17.7 PREFLIGHT.py")


def build():
    source = FROZEN.build()
    if source != (HERE.parent / "UPDATE EXISTING TEST TO R17.7.py").read_text(encoding="utf-8"):
        raise AssertionError("Frozen R17.7 updater changed; do not build from unknown bytes.")
    source = source.replace("First compares 72 aggregate results using read-only virtual DAX measures.",
                            "R02 compares the same 72 pairs using one scalar per read-only query.", 1)
    source = source.replace("import math\n", "import math\nfrom numbers import Number\nimport re\n", 1)
    support = "MEMBERS = " + repr(CHECK.MEMBERS) + "\n\n"
    for function in (CHECK.PreflightStopped, DIAGNOSTIC.safe_error, DIAGNOSTIC.valid_scope,
                     CHECK.text_filter, CHECK.build_scalar, CHECK.source_metadata_query,
                     CHECK.source_metadata_digest, CHECK.scalar_value):
        support += inspect.getsource(function) + "\n\n"
    old_query = inspect.getsource(FROZEN.CHECK.build_query)
    old_verify = inspect.getsource(FROZEN.CHECK.verify_numeric)
    assert source.count(old_query) == 1 and source.count(old_verify) == 1
    source = source.replace(old_query, support, 1).replace(old_verify, inspect.getsource(CHECK.verify_numeric), 1)
    target = "    numeric = verify_numeric(evaluate, WORKSPACE, TEST_MODEL, NUMERIC_OVERRIDES)"
    replacement = '''    try:
        numeric = verify_numeric(evaluate, WORKSPACE, TEST_MODEL, NUMERIC_OVERRIDES)
    except PreflightStopped as exc:
        result = {"Stage": "TEST_R177_PREFLIGHT_STOPPED", "UpdaterRevision": "R02",
                  "TestModelID": TEST_MODEL, "Preflight": exc.detail,
                  "ModelWriteRequested": False, "OriginalModelWriteRequested": False,
                  "CompanyAmountValuesPrintedOrStored": False,
                  "RefreshRequested": False, "ReportPublished": False,
                  "NextStep": "Send this JSON. Do not retry, refresh, open R17.7 as installed or publish."}
        print(json.dumps(result, indent=2), flush=True)
        return result'''
    assert source.count(target) == 1
    source = source.replace(target, replacement, 1)
    source = source.replace("Native-R177-Performance-Files/", "Native-R177-Performance-Files-R02/", 1)
    source = source.replace('result = {"Stage": "TEST_R177_ALREADY_INSTALLED",',
                            'result = {"Stage": "TEST_R177_ALREADY_INSTALLED", "UpdaterRevision": "R02",', 1)
    source = source.replace('"NextStep": "If new helper columns were already processed, open R17.7. Otherwise refresh TEST once."',
                            '"NextStep": "Send this JSON; confirm prior update and processing before any further action."', 1)
    source = source.replace('"MetadataChanged": changed, "NumericalPreflight": numeric,',
                            '"UpdaterRevision": "R02", "MetadataChanged": changed, "NumericalPreflight": numeric,', 1)
    return source


if __name__ == "__main__":
    (HERE / "UPDATE EXISTING TEST TO R17.7 R02.py").write_text(build(), encoding="utf-8")
