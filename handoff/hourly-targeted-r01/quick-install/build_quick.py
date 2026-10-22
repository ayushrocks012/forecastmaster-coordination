"""Package the reviewed patch for one setup cell and one Functions paste."""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
HANDOFF = PACKAGE.parent


def packed(value: bytes) -> str:
    return base64.b64encode(zlib.compress(value, 9)).decode()


def function_segment(text: str, name: str) -> str:
    tree = ast.parse(text)
    node = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    return str(ast.get_source_segment(text, node))


def build() -> None:
    original = json.loads(
        (HANDOFF / "notebook-r05.4/ForecastMaster_Refresh.ipynb").read_text(
            encoding="utf-8"
        )
    )
    changed = json.loads(
        (PACKAGE / "candidate/ForecastMaster_Refresh.ipynb").read_text(encoding="utf-8")
    )
    patches = [
        {
            "Name": f"cell-{index:02d}",
            "Before": "".join(original["cells"][index]["source"]),
            "After": "".join(changed["cells"][index]["source"]),
        }
        for index in (4, 8, 10, 12)
    ]
    payload = json.dumps(patches, ensure_ascii=False).encode()
    installer = (ROOT / "install_hourly.py").read_bytes()
    worker = (HANDOFF / "notebook-r05.4/Refresh/source/request_worker.py").read_bytes()
    cell = f"""# HOURLY TARGETED R01 - run in a separate blank setup notebook, one cell only.
import base64, hashlib, json, zlib, requests, notebookutils
_fm_patch_bytes = zlib.decompress(base64.b64decode({packed(payload)!r}))
assert hashlib.sha256(_fm_patch_bytes).hexdigest() == {hashlib.sha256(payload).hexdigest()!r}
_fm_setup = {{"__name__": "hourly_setup"}}
exec(zlib.decompress(base64.b64decode({packed(worker)!r})), _fm_setup)
exec(zlib.decompress(base64.b64decode({packed(installer)!r})), _fm_setup)
_fm_store = _fm_setup["OneLakeQueueStore"](_fm_setup["WORKSPACE"], _fm_setup["LAKEHOUSE"], notebookutils.credentials.getToken)
_fm_result = _fm_setup["install"](requests, notebookutils.credentials.getToken, _fm_store, json.loads(_fm_patch_bytes))
notebookutils.notebook.exit(json.dumps(_fm_result))
"""
    compile(cell, "QUICK NOTEBOOK UPDATE", "exec")
    (ROOT / "01 - UPDATE HOURLY NOTEBOOK.txt").write_text(cell, encoding="utf-8")
    functions = (
        HANDOFF / "native-adhoc-r01/ForecastMaster-Actions-R06-native.txt"
    ).read_text(encoding="utf-8")
    old = function_segment(functions, "prepareMetadataDecision")
    new = (
        (PACKAGE / "paste-cells/detector-prepareMetadataDecision.py")
        .read_text(encoding="utf-8")
        .rstrip()
    )
    if functions.count(old) != 1:
        raise ValueError("Functions helper source differs")
    functions = functions.replace(old, new)
    line = '        baseline = readControlJson(files, "metadata-success.json")\n'
    if functions.count(line) != 1:
        raise ValueError("Functions baseline-read source differs")
    functions = functions.replace(
        line,
        (PACKAGE / "paste-cells/detector-read-baseline.py").read_text(encoding="utf-8"),
    )
    functions = functions.replace(
        "# R06-NATIVE-R01: unchanged R05.2 helpers followed by a native request producer.",
        "# R06-NATIVE-R01 + hourly targeted R01: native producer preserved; baseline recovery patched.",
        1,
    )
    compile(functions, "QUICK FUNCTIONS UPDATE", "exec")
    (ROOT / "02 - PASTE CURRENT FUNCTIONS.txt").write_text(functions, encoding="utf-8")


if __name__ == "__main__":
    build()
