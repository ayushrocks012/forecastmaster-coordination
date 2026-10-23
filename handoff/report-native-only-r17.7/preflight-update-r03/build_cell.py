"""Preserve the model patch; replace only R02's numerical evidence method."""
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


OLD = load("r177_r02_builder_for_r03", HERE.parent / "preflight-update-r02/build_cell.py")
CHECK = load("r177_r03_check", HERE / "numeric_check.py")


def build():
    source = OLD.build()
    if source != (HERE.parent / "preflight-update-r02/UPDATE EXISTING TEST TO R17.7 R02.py").read_text(encoding="utf-8"):
        raise AssertionError("Frozen R02 updater changed; no build.")
    old_verify = inspect.getsource(OLD.CHECK.verify_numeric)
    support = "VARIANCE_CONTRACT = " + repr(CHECK.VARIANCE_CONTRACT) + "\n\n"
    for function in (CHECK.verify_variance_contract, CHECK.expected_variance_percent, CHECK.verify_numeric):
        support += inspect.getsource(function) + "\n\n"
    assert source.count(old_verify) == 1
    source = source.replace(old_verify, support, 1)
    source = source.replace("R02 compares the same 72 pairs using one scalar per read-only query.",
                            "R03 checks 72 candidate results against direct inputs and verified-formula expectations.", 1)
    target = "numeric = verify_numeric(evaluate, WORKSPACE, TEST_MODEL, NUMERIC_OVERRIDES)"
    assert source.count(target) == 1
    source = source.replace(target, "numeric = verify_numeric(evaluate, WORKSPACE, TEST_MODEL, NUMERIC_OVERRIDES, database)", 1)
    source = source.replace('"UpdaterRevision": "R02"', '"UpdaterRevision": "R03"')
    source = source.replace("Native-R177-Performance-Files-R02/", "Native-R177-Performance-Files-R03/", 1)
    target = '''"NextStep": ("Refresh ONLY this existing TEST once for new metadata columns, then open R17.7 and compare report timings." if ok'''
    replacement = '''"NextStep": ("Send this JSON for review of direct/derived preflight evidence. Do not refresh, open R17.7 or publish yet." if ok'''
    assert source.count(target) == 1
    return source.replace(target, replacement, 1)


if __name__ == "__main__":
    (HERE / "UPDATE EXISTING TEST TO R17.7 R03.py").write_text(build(), encoding="utf-8")
