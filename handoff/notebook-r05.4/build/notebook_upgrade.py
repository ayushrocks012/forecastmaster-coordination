"""Install one reviewed current-file worker definition into its existing item ID.

Run only the generated installer cell on the company laptop. Packaging and
local tests never call Fabric. Keeps the pipeline, request ledger and flow IDs.
"""
from __future__ import annotations
import base64
import hashlib
import json
import time
import zlib
from typing import Any

WORKSPACE = "f5cb5742-9a7c-4337-a4c0-952706dddf0b"
NOTEBOOK = "e2e0952d-4317-4936-bf0f-2c34698371dc"
LAKEHOUSE = "d6e33ebd-67b1-420a-8d84-c3a0d04d8b21"
BASE = "https://api.fabric.microsoft.com/v1"
ITEM = f"/workspaces/{WORKSPACE}/notebooks/{NOTEBOOK}"


def api(http: Any, token: Any, method: str, path: str, **kwargs: Any) -> Any:
    result = http.request(method, BASE + path, headers={"Authorization": "Bearer " + token("pbi")}, timeout=60, allow_redirects=False, **kwargs)
    if result.status_code not in {200, 202}:
        raise RuntimeError(f"Notebook update API failed (HTTP {result.status_code}). No replacement item was created.")
    if result.status_code == 200:
        return result
    from uuid import UUID
    operation = str(UUID(result.headers["x-ms-operation-id"]))
    for _ in range(30):
        time.sleep(min(10, max(1, int(result.headers.get("Retry-After", "2")))))
        status = http.request("GET", BASE + "/operations/" + operation, headers={"Authorization": "Bearer " + token("pbi")}, timeout=60, allow_redirects=False)
        if status.status_code != 200:
            raise RuntimeError("Cannot confirm notebook update operation; inspect Fabric before retrying")
        body = status.json()
        if body.get("status") == "Succeeded":
            if path.endswith("getDefinition?format=ipynb"):
                status = http.request("GET", BASE + "/operations/" + operation + "/result", headers={"Authorization": "Bearer " + token("pbi")}, timeout=60, allow_redirects=False)
                if status.status_code != 200:
                    raise RuntimeError("Notebook definition operation result is unavailable")
            return status
        if body.get("status") in {"Failed", "Cancelled"}:
            raise RuntimeError("Notebook update operation did not complete: " + str(body.get("status")))
    raise RuntimeError("Notebook operation remains pending; inspect Fabric before retrying")


def content(definition: dict[str, Any]) -> dict[str, Any]:
    parts = [p for p in definition["parts"] if p["path"] == "notebook-content.ipynb"]
    if len(parts) != 1 or parts[0]["payloadType"] != "InlineBase64":
        raise ValueError("Expected one ipynb notebook definition")
    value = json.loads(base64.b64decode(parts[0]["payload"], validate=True))
    if not isinstance(value, dict):
        raise ValueError("Invalid notebook object")
    return value


def install(http: Any, token: Any, store: Any, notebook: dict[str, Any]) -> None:
    item = api(http, token, "GET", ITEM).json()
    if item.get("displayName") != "ForecastMaster_Refresh" or item.get("id") != NOTEBOOK:
        raise ValueError("The maintained notebook identity has changed; nothing was updated")
    if not store.acquire():
        raise RuntimeError("A refresh writer is active. Wait for completion before installing.")
    try:
        old = api(http, token, "POST", ITEM + "/getDefinition?format=ipynb").json()["definition"]
        before = content(old)
        notebook = json.loads(json.dumps(notebook))
        notebook["metadata"] = before.get("metadata", notebook.get("metadata", {}))
        # Keep the existing attached Lakehouse metadata. Operating parameters are
        # the reviewed Demand root and current-file policy in the new package.
        for c in notebook["cells"]:
            if c["cell_type"] == "code":
                compile("".join(c["source"]), "R05.4", "exec")
        payload = base64.b64encode(json.dumps(notebook).encode()).decode()
        definition = {"format": "ipynb", "parts": [{"path": "notebook-content.ipynb", "payloadType": "InlineBase64", "payload": payload}]}
        from datetime import UTC, datetime
        backup = "upgrades/r054-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
        store.write(backup, {"NotebookID": NOTEBOOK, "Definition": old})
        api(http, token, "POST", ITEM + "/updateDefinition", json={"definition": definition})
        check = api(http, token, "POST", ITEM + "/getDefinition?format=ipynb").json()["definition"]
        saved = content(check)
        def signature(n: dict[str, Any]) -> list[tuple[str, str, tuple[str, ...]]]:
            return [(c["cell_type"], "".join(c["source"]).replace("\r\n", "\n").rstrip(), tuple(c.get("metadata", {}).get("tags", []))) for c in n["cells"]]
        if signature(saved) != signature(notebook):
            raise RuntimeError("Saved notebook verification failed. Retained backup: " + backup)
        print("UPDATED: ForecastMaster_Refresh R05.4 (existing notebook ID retained).")
        print("Backup: Files/ForecastMasterRefreshState/" + backup)
        print("Parameters: FM_RUN_MODE (REQUESTS or HOURLY), FM_METADATA_JSON.")
        print("Close this editor without saving old contents, reopen ForecastMaster_Refresh, and check R05.4 in its title cell.")
        print("NEXT: keep schedules paused. In ForecastMaster_Hourly add this notebook to the True branch with FM_RUN_MODE=HOURLY and FM_METADATA_JSON set to the metadata activity output string. Run once and check the business result before scheduling.")
    finally:
        store.release()


def build_cell(root: Any) -> str:
    notebook = json.loads((root / "ForecastMaster_Refresh.ipynb").read_text())
    encoded = base64.b64encode(zlib.compress(json.dumps(notebook).encode(), 9)).decode()
    worker = base64.b64encode(zlib.compress((root / "Refresh/source/request_worker.py").read_bytes(), 9)).decode()
    module = base64.b64encode(zlib.compress((root / "build/notebook_upgrade.py").read_bytes(), 9)).decode()
    sha = hashlib.sha256(json.dumps(notebook).encode()).hexdigest()
    return f'''# R05.4 ONE-TIME UPDATE. Pause the controller schedule and let active runs finish first.
# Run THIS cell only. It updates the existing notebook; it never creates another worker.
import base64, zlib, json, hashlib, requests, notebookutils
_fm_new_bytes = zlib.decompress(base64.b64decode({encoded!r}))
assert hashlib.sha256(_fm_new_bytes).hexdigest() == {sha!r}
_fm_worker_scope = {{}}
exec(zlib.decompress(base64.b64decode({worker!r})), _fm_worker_scope)
_fm_upgrade_scope = {{}}
exec(zlib.decompress(base64.b64decode({module!r})), _fm_upgrade_scope)
_fm_store = _fm_worker_scope['OneLakeQueueStore']({WORKSPACE!r}, {LAKEHOUSE!r}, notebookutils.credentials.getToken)
_fm_upgrade_scope['install'](requests, notebookutils.credentials.getToken, _fm_store, json.loads(_fm_new_bytes))
notebookutils.notebook.exit('UPDATED: ForecastMaster_Refresh R05.4; close and reopen this notebook.')
'''

if __name__ == "__main__":
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    cell = build_cell(root)
    compile(cell, "Install_R05_3", "exec")
    (root / "INSTALL NOTEBOOK R05.4.txt").write_text(cell)
