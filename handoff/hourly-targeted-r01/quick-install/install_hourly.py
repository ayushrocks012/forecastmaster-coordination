"""Install exactly the four reviewed hourly cells into the existing notebook."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

WORKSPACE = "f5cb5742-9a7c-4337-a4c0-952706dddf0b"
NOTEBOOK = "e2e0952d-4317-4936-bf0f-2c34698371dc"
LAKEHOUSE = "d6e33ebd-67b1-420a-8d84-c3a0d04d8b21"
BASE = "https://api.fabric.microsoft.com/v1"
ITEM = f"/workspaces/{WORKSPACE}/notebooks/{NOTEBOOK}"


def api(http: Any, token: Any, method: str, path: str, **kwargs: Any) -> Any:
    """Issue a mutation once and confirm any operation without reissuing it."""
    response = http.request(
        method,
        BASE + path,
        headers={"Authorization": "Bearer " + token("pbi")},
        timeout=60,
        allow_redirects=False,
        **kwargs,
    )
    if response.status_code not in {200, 202}:
        raise RuntimeError(f"Hourly updater API: HTTP {response.status_code} at {path}")
    if response.status_code == 200:
        return response
    operation = str(UUID(response.headers["x-ms-operation-id"]))
    for _ in range(30):
        time.sleep(min(30, max(1, int(response.headers.get("Retry-After", "2")))))
        response = http.request(
            "GET",
            BASE + "/operations/" + operation,
            headers={"Authorization": "Bearer " + token("pbi")},
            timeout=60,
            allow_redirects=False,
        )
        if response.status_code != 200:
            raise RuntimeError("Cannot confirm update operation: " + operation)
        status = response.json().get("status")
        if status == "Succeeded":
            if path.endswith("getDefinition?format=ipynb"):
                response = http.request(
                    "GET",
                    BASE + "/operations/" + operation + "/result",
                    headers={"Authorization": "Bearer " + token("pbi")},
                    timeout=60,
                    allow_redirects=False,
                )
                if response.status_code != 200:
                    raise RuntimeError("Cannot retrieve definition operation result")
            return response
        if status not in {"Running", "NotStarted"}:
            raise RuntimeError("Update operation did not succeed: " + str(status))
    raise RuntimeError(
        "Update still pending; inspect this operation before retrying: " + operation
    )


def normalized(source: Any) -> str:
    """Compare code with notebook newline conventions normalized."""
    text = source if isinstance(source, str) else "".join(source)
    return text.replace("\r\n", "\n").rstrip()


def content(definition: dict[str, Any]) -> dict[str, Any]:
    """Read the exact notebook part while leaving other definition parts intact."""
    parts = [p for p in definition["parts"] if p["path"] == "notebook-content.ipynb"]
    if len(parts) != 1 or parts[0].get("payloadType") != "InlineBase64":
        raise ValueError("Expected one InlineBase64 ipynb notebook part")
    result = json.loads(base64.b64decode(parts[0]["payload"], validate=True))
    if not isinstance(result, dict) or not isinstance(result.get("cells"), list):
        raise ValueError("Invalid notebook definition")
    return result


def signature(value: Any) -> str:
    """Bind all saved fields, including parameters and Lakehouse metadata."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def prepare(
    before: dict[str, Any], patches: list[dict[str, str]]
) -> tuple[dict[str, Any], list[int]]:
    """Preserve all cells/fields except the four known code sources and their output."""
    after = copy.deepcopy(before)
    changed: list[int] = []
    used: set[int] = set()
    for patch in patches:
        old, new = normalized(patch["Before"]), normalized(patch["After"])
        matches = [
            i
            for i, cell in enumerate(before["cells"])
            if cell.get("cell_type") == "code"
            and normalized(cell.get("source", [])) in {old, new}
        ]
        if len(matches) != 1 or matches[0] in used:
            raise ValueError(
                "Saved notebook differs at "
                + patch["Name"]
                + ". No update attempted; send the error and keep your downloaded backup."
            )
        index = matches[0]
        used.add(index)
        compile(patch["After"], patch["Name"], "exec")
        if normalized(before["cells"][index]["source"]) == old:
            after["cells"][index]["source"] = patch["After"].splitlines(keepends=True)
            after["cells"][index]["outputs"] = []
            after["cells"][index]["execution_count"] = None
            changed.append(index)
    return after, changed


def install(
    http: Any, token: Any, store: Any, patches: list[dict[str, str]]
) -> dict[str, Any]:
    """Back up, check concurrency, update the same item, and verify the saved result."""
    item = api(http, token, "GET", ITEM).json()
    if (
        item.get("id") != NOTEBOOK
        or item.get("displayName") != "ForecastMaster_Refresh"
    ):
        raise ValueError(
            "Existing ForecastMaster_Refresh identity differs; nothing updated"
        )
    if not store.acquire():
        raise RuntimeError(
            "A refresh writer is active. Let it finish, then run this setup cell again."
        )
    try:
        original = api(
            http, token, "POST", ITEM + "/getDefinition?format=ipynb"
        ).json()["definition"]
        before = content(original)
        after, changed = prepare(before, patches)
        if not changed:
            return {
                "Status": "HOURLY_NOTEBOOK_ALREADY_UPDATED",
                "NotebookID": NOTEBOOK,
                "RefreshStarted": False,
                "FunctionsUpdated": False,
            }
        backup = (
            "upgrades/hourly-files-r01-"
            + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            + ".json"
        )
        receipt = {"NotebookID": NOTEBOOK, "Definition": original}
        store.write(backup, receipt)
        if store.read(backup) != receipt:
            raise RuntimeError("Backup read-back failed; nothing updated")
        current = api(http, token, "POST", ITEM + "/getDefinition?format=ipynb").json()[
            "definition"
        ]
        if signature(current) != signature(original):
            raise RuntimeError(
                "Another editor changed the notebook; nothing updated. Backup: "
                + backup
            )
        definition = copy.deepcopy(original)
        # Platform metadata is not being changed. Carry all other definition parts.
        definition["parts"] = [
            p for p in definition["parts"] if p["path"] != ".platform"
        ]
        definition["format"] = "ipynb"
        part = next(
            p for p in definition["parts"] if p["path"] == "notebook-content.ipynb"
        )
        part["payload"] = base64.b64encode(
            json.dumps(after, ensure_ascii=False).encode()
        ).decode()
        api(
            http,
            token,
            "POST",
            ITEM + "/updateDefinition",
            json={"definition": definition},
        )
        saved = content(
            api(http, token, "POST", ITEM + "/getDefinition?format=ipynb").json()[
                "definition"
            ]
        )
        if signature(saved) != signature(after):
            raise RuntimeError(
                "Update sent but saved read-back differs. Inspect before retrying. Backup: "
                + backup
            )
        result = {
            "Status": "HOURLY_NOTEBOOK_UPDATED",
            "NotebookID": NOTEBOOK,
            "ChangedCells": changed,
            "Backup": "Files/ForecastMasterRefreshState/" + backup,
            "WorkbookReads": 0,
            "RefreshStarted": False,
            "FunctionsUpdated": False,
        }
        print(json.dumps(result, indent=2), flush=True)
        return result
    finally:
        store.release()
