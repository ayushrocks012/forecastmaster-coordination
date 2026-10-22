# READ ONLY: inspect model metadata. No installer, sales query or refresh.
# Paste this entire short file into ONE NEW code cell in ForecastMaster_GM_Setup.
import base64
import json
import time
from uuid import UUID
import sempy.fabric as fabric

MODE = "PROBE"
WORKSPACE = 'f5cb5742-9a7c-4337-a4c0-952706dddf0b'
MODEL = 'e7af2967-7725-4108-a170-9e490d4e35bb'


def read_definition(client):
    path = f"/v1/workspaces/{WORKSPACE}/semanticModels/{MODEL}/getDefinition"
    response = client.post(path + "?format=TMSL")
    response.raise_for_status()
    if response.status_code == 200:
        return response.json()["definition"]
    if response.status_code != 202:
        raise RuntimeError("Unexpected metadata response. No model changes made.")
    operation_id = str(UUID(response.headers["x-ms-operation-id"]))
    operation = "/v1/operations/" + operation_id
    deadline = time.monotonic() + 360
    while time.monotonic() < deadline:
        delay = max(1, min(30, int(response.headers.get("Retry-After", "5"))))
        time.sleep(min(delay, max(0, deadline - time.monotonic())))
        response = client.get(operation)
        response.raise_for_status()
        status = response.json().get("status")
        if status == "Succeeded":
            result = client.get(operation + "/result")
            result.raise_for_status()
            return result.json()["definition"]
        if status in {"Failed", "Cancelled", "Canceled"}:
            raise RuntimeError("Metadata read did not complete: " + status)
    raise TimeoutError("Metadata read timed out. No model changes made.")


def describe_model(definition):
    part = next((p for p in definition["parts"] if p["path"] == "model.bim"), None)
    if part is None:
        raise ValueError("TMSL model.bim was not returned. No changes made.")
    model = json.loads(base64.b64decode(part["payload"]))["model"]
    tables = model.get("tables", [])
    fact = next((t for t in tables if t["name"] == "fm_review_facts"), {})
    partitions = fact.get("partitions", [])
    partition = partitions[0] if len(partitions) == 1 else {}
    source = partition.get("source", {})
    expression_name = source.get("expressionSource")
    expressions = model.get("expressions", [])
    expression = next((e.get("expression", "") for e in expressions
                       if e["name"] == expression_name), "")
    if isinstance(expression, list):
        expression = "\n".join(expression)
    is_sql = any(token in expression for token in ("Sql.Database", "OneLake.SqlAnalytics"))
    native_count = sum(t["name"].startswith("fm_native_") for t in tables)
    compatible = (len(partitions) == 1 and partition.get("mode") == "directLake"
                  and source.get("type") == "entity" and is_sql and native_count == 0)
    if native_count:
        reason = "Native objects already exist; inspect before any installation."
    elif not partitions:
        reason = "fm_review_facts or its source partition was not found."
    elif not compatible:
        reason = "Current adapter requires one existing Direct Lake on SQL entity partition."
    else:
        reason = "Source shape is compatible; native installation and parity remain unverified."
    return {"Mode": "PROBE", "FactPartitionCount": len(partitions),
            "SourceStorageModes": [p.get("mode", "UNKNOWN") for p in partitions],
            "SourceType": source.get("type", "UNKNOWN"), "SQLSourceConfirmed": is_sql,
            "NativeTablesAlreadyPresent": native_count,
            "ExistingTableCount": len(tables),
            "ExistingSecurityRoleCount": len(model.get("roles", [])),
            "CompatibleWithCurrentAdapter": compatible, "Reason": reason,
            "SourceAmountsRead": False, "ModelUpdated": False}


if MODE != "PROBE":
    raise ValueError("This short file supports read-only PROBE only.")
print("Reading model metadata only. No installation, sales query or refresh.")
print(json.dumps(describe_model(read_definition(fabric.FabricRestClient())), indent=2))
