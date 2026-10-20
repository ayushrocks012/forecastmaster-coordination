"""Create only the new native items; reuse only if their saved definitions match."""

import base64
import copy
import json
import time
from uuid import UUID

WORKSPACE = "f5cb5742-9a7c-4337-a4c0-952706dddf0b"
EXISTING_NOTEBOOK = "e2e0952d-4317-4936-bf0f-2c34698371dc"
LAKEHOUSE = "d6e33ebd-67b1-420a-8d84-c3a0d04d8b21"
NOTEBOOK_NAME = "ForecastMaster_Native_Adhoc"
PIPELINE_NAME = "ForecastMaster_Adhoc"
BASE = "https://api.fabric.microsoft.com/v1"


class API:
    def __init__(self, http, token, sleep=time.sleep):
        self.http, self.token, self.sleep = http, token, sleep

    def request(self, method, path, **kwargs):
        response = self.http.request(
            method, BASE + path, headers={"Authorization": "Bearer " + self.token("pbi")},
            timeout=60, allow_redirects=False, **kwargs,
        )
        if response.status_code not in {200, 201, 202}:
            raise RuntimeError(f"Native setup API {path}: HTTP {response.status_code}. " + response.text)
        return response

    def call(self, method, path, **kwargs):
        response = self.request(method, path, **kwargs)
        if response.status_code != 202:
            return response.json()
        operation = str(UUID(response.headers["x-ms-operation-id"]))
        print("Waiting for setup operation: " + operation, flush=True)
        for _ in range(30):
            self.sleep(max(1, int(response.headers.get("Retry-After", "2"))))
            response = self.request("GET", "/operations/" + operation)
            if response.status_code != 200:
                raise RuntimeError("Cannot confirm setup operation " + operation)
            body = response.json()
            if body.get("status") == "Succeeded":
                response = self.request("GET", "/operations/" + operation + "/result")
                if response.status_code != 200:
                    raise RuntimeError("Cannot retrieve setup result " + operation)
                return response.json()
            if body.get("status") not in {"Running", "NotStarted"}:
                raise RuntimeError("Native setup operation did not succeed: " + json.dumps(body))
        raise RuntimeError("Native setup operation still pending; inspect before retrying: " + operation)


def decode_part(definition, path):
    matching = [part for part in definition["parts"] if part["path"] == path]
    if len(matching) != 1 or matching[0]["payloadType"] != "InlineBase64":
        raise ValueError("Expected exactly one InlineBase64 " + path)
    return json.loads(base64.b64decode(matching[0]["payload"], validate=True))


def notebook_signature(value):
    return [
        (cell["cell_type"], "".join(cell["source"]).replace("\r\n", "\n").rstrip(),
         cell.get("metadata", {}).get("tags", []))
        for cell in value["cells"]
    ]


def definition_part(path, value):
    return {"path": path, "payloadType": "InlineBase64", "payload": base64.b64encode(json.dumps(value).encode()).decode()}


def list_items(api):
    items, continuation, seen = [], None, set()
    while True:
        params = {"continuationToken": continuation} if continuation else {}
        response = api.call("GET", f"/workspaces/{WORKSPACE}/items", params=params)
        items.extend(response["value"])
        continuation = response.get("continuationToken")
        if not continuation:
            return items
        if continuation in seen:
            raise ValueError("Repeated workspace inventory page; no creation attempted")
        seen.add(continuation)


def find_existing(items, name, kind):
    matches = [item for item in items if item.get("displayName") == name]
    if len(matches) > 1 or matches and matches[0].get("type") != kind:
        raise ValueError("Ambiguous or different existing item type: " + name)
    return matches[0] if matches else None


def pipeline_content(notebook_id):
    return {"properties": {
        "description": "Native ad hoc R01: event-scoped requests, shared R05.4 lock and retained receipts.",
        "parameters": {name: {"type": "String", "defaultValue": ""} for name in ("Subject", "Type", "Source")},
        "activities": [{
            "name": "Run_Native_Adhoc", "type": "TridentNotebook", "dependsOn": [],
            "policy": {"timeout": "0.00:30:00", "retry": 5, "retryIntervalInSeconds": 120,
                       "secureInput": False, "secureOutput": False},
            "typeProperties": {
                "workspaceId": WORKSPACE, "notebookId": notebook_id,
                "parameters": {"FM_EVENT_SUBJECT": {
                    "type": "string", "value": {"type": "Expression", "value": "@pipeline().parameters.Subject"},
                }},
            },
        }],
    }}


def ensure_new_item(api, items, name, kind, definition, expected):
    existing = find_existing(items, name, kind)
    if existing is None:
        print("Creating " + name, flush=True)
        created = api.call("POST", f"/workspaces/{WORKSPACE}/items", json={
            "displayName": name, "type": kind,
            "description": "ForecastMaster native ad hoc R01; existing hourly and controller items retained.",
            "definition": definition,
        })
        identity = str(UUID(created["id"]))
        if created.get("type", kind) != kind or created.get("displayName", name) != name:
            raise ValueError("Created item identity differs; inspect workspace before retrying")
    else:
        identity = str(UUID(existing["id"]))
        print("Verifying existing " + name + "; no overwrite", flush=True)
    format_suffix = "?format=ipynb" if kind == "Notebook" else ""
    saved = api.call("POST", f"/workspaces/{WORKSPACE}/items/{identity}/getDefinition" + format_suffix)["definition"]
    if kind == "Notebook":
        value = decode_part(saved, "notebook-content.ipynb")
        if notebook_signature(value) != notebook_signature(expected):
            raise ValueError("Existing/saved native notebook differs; no overwrite attempted")
        lakehouse = value.get("metadata", {}).get("dependencies", {}).get("lakehouse", {})
        if lakehouse.get("default_lakehouse") != LAKEHOUSE or lakehouse.get("default_lakehouse_workspace_id") != WORKSPACE:
            raise ValueError("Saved native notebook Lakehouse binding differs")
    elif decode_part(saved, "pipeline-content.json") != expected:
        raise ValueError("Existing/saved native pipeline differs; no overwrite attempted")
    print("Verified " + name + ": " + identity, flush=True)
    return identity


def install_native(http, token, notebook, sleep=time.sleep):
    api = API(http, token, sleep)
    current = api.call("GET", f"/workspaces/{WORKSPACE}/items/{EXISTING_NOTEBOOK}")
    if current.get("id") != EXISTING_NOTEBOOK or current.get("displayName") != "ForecastMaster_Refresh":
        raise ValueError("Maintained R05.4 notebook identity differs; nothing created")
    old = api.call("POST", f"/workspaces/{WORKSPACE}/notebooks/{EXISTING_NOTEBOOK}/getDefinition?format=ipynb")["definition"]
    source = decode_part(old, "notebook-content.ipynb")
    notebook = copy.deepcopy(notebook)
    notebook["metadata"] = source["metadata"]
    # Bind to the same native Lakehouse without editing the maintained notebook.
    binding = notebook.get("metadata", {}).get("dependencies", {}).get("lakehouse", {})
    if binding.get("default_lakehouse") != LAKEHOUSE or binding.get("default_lakehouse_workspace_id") != WORKSPACE:
        raise ValueError("Maintained notebook Lakehouse metadata differs; nothing created")
    items = list_items(api)
    # Preflight both names before creating either new item.
    find_existing(items, NOTEBOOK_NAME, "Notebook")
    find_existing(items, PIPELINE_NAME, "DataPipeline")
    notebook_id = ensure_new_item(api, items, NOTEBOOK_NAME, "Notebook", {
        "format": "ipynb", "parts": [definition_part("notebook-content.ipynb", notebook)],
    }, notebook)
    pipeline = pipeline_content(notebook_id)
    pipeline_id = ensure_new_item(api, items, PIPELINE_NAME, "DataPipeline", {
        "parts": [definition_part("pipeline-content.json", pipeline)],
    }, pipeline)
    print("READY: native notebook and pipeline definitions verified. No job or rule started.")
    print("Native pipeline: " + pipeline_id)
    print("Next: publish the native function addition and connect/test the event rule and report button.")
    return {"NotebookID": notebook_id, "PipelineID": pipeline_id}
