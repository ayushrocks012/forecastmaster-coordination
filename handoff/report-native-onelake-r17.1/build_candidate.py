"""Build readable single-cell receiving files. Never calls Fabric."""
import ast
import inspect
import json
from pathlib import Path
import pprint
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import onelake_model as om
nm = om.nm

RUNTIME = r'''
# Creates ONE NEW test semantic model. Never updates/replaces the original model.
# Run only this new code cell in ForecastMaster_GM_Setup, not Run all.
WORKSPACE = "f5cb5742-9a7c-4337-a4c0-952706dddf0b"
SOURCE_MODEL = "e7af2967-7725-4108-a170-9e490d4e35bb"
TEST_NAME = "ForecastMaster Native OneLake R17.1 - TEST"


def digest(value):
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()


def complete(client, response):
    if response.status_code not in {200, 201, 202}:
        try:
            code = response.json().get("errorCode", "UNKNOWN")
        except (ValueError, AttributeError):
            code = "UNKNOWN"
        code = code if isinstance(code, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]{0,95}", code) else "UNKNOWN"
        raise RuntimeError("Fabric HTTP " + str(response.status_code)
                           + " (" + code + "). Inspect this run; do not retry a creation blindly.")
    if response.status_code != 202:
        return response.json()
    operation_id = str(UUID(response.headers["x-ms-operation-id"]))
    print("Operation: " + operation_id, flush=True)
    operation = "/v1/operations/" + operation_id
    deadline = time.monotonic() + 360
    while time.monotonic() < deadline:
        delay = max(1, min(30, int(response.headers.get("Retry-After", "5"))))
        time.sleep(min(delay, max(0, deadline - time.monotonic())))
        response = client.get(operation)
        if response.status_code != 200:
            raise RuntimeError("Operation status unavailable. Inspect the operation before retrying.")
        state = response.json().get("status")
        if state == "Succeeded":
            result = client.get(operation + "/result")
            if result.status_code not in {200, 201}:
                raise RuntimeError("Operation succeeded but result is unavailable. Do not recreate it.")
            return result.json()
        if state in {"Failed", "Cancelled", "Canceled"}:
            raise RuntimeError("Operation " + state + ". Inspect its details in Fabric; keep the original model.")
    raise TimeoutError("Operation unconfirmed. Check the TEST model and this operation before any retry.")


def read_definition(client, model_id):
    path = f"/v1/workspaces/{WORKSPACE}/semanticModels/{str(UUID(model_id))}/getDefinition?format=TMSL"
    return complete(client, client.post(path))["definition"]


def model_part(definition):
    parts = [p for p in definition["parts"] if p["path"] == "model.bim"]
    if len(parts) != 1:
        raise ValueError("Expected exactly one TMSL model.bim. No creation attempted.")
    return json.loads(base64.b64decode(parts[0]["payload"]))


def ensure_absent(client):
    token = None
    for _ in range(100):
        path = f"/v1/workspaces/{WORKSPACE}/semanticModels"
        if token:
            path += "?continuationToken=" + quote(token, safe="")
        response = client.get(path)
        if response.status_code != 200:
            raise RuntimeError("Cannot check existing test models. No creation attempted.")
        page = response.json()
        if any(item.get("displayName", "").casefold() == TEST_NAME.casefold()
               for item in page.get("value", [])):
            raise ValueError("The TEST model already exists. Keep it and send its result; do not overwrite it.")
        token = page.get("continuationToken")
        if not token:
            return
    raise RuntimeError("Item listing did not complete. No creation attempted.")


def create_test_model(client):
    ensure_absent(client)
    before = read_definition(client, SOURCE_MODEL)
    source = model_part(before)
    candidate = extend_onelake(source)
    candidate["name"] = TEST_NAME
    candidate.pop("id", None)
    # Item identity and platform metadata belong to the original. Never clone them.
    parts = [copy.deepcopy(p) for p in before["parts"] if p["path"] != ".platform"]
    part = next(p for p in parts if p["path"] == "model.bim")
    part["payload"] = base64.b64encode(json.dumps(candidate, ensure_ascii=False).encode()).decode()
    part["payloadType"] = "InlineBase64"
    if not any(p["path"] == "definition.pbism" for p in parts):
        raise ValueError("Required definition.pbism was not returned. No creation attempted.")
    if digest(read_definition(client, SOURCE_MODEL)) != digest(before):
        raise RuntimeError("Original metadata changed concurrently. No creation attempted.")
    print("Creating one separate TEST model; the original model is not an update target.", flush=True)
    created = complete(client, client.post(f"/v1/workspaces/{WORKSPACE}/semanticModels", json={
        "displayName": TEST_NAME,
        "description": "OneLake native metadata compatibility TEST only. R16.6 production stays in place.",
        "definition": {"parts": parts}}))
    test_id = str(UUID(created["id"]))
    print("Created TEST model ID: " + test_id, flush=True)
    if test_id == SOURCE_MODEL:
        raise RuntimeError("Unexpected item identity. Stop and inspect Fabric.")
    received = model_part(read_definition(client, test_id))
    old = {t["name"]: t for t in source["model"]["tables"]}
    new = {t["name"]: t for t in received["model"]["tables"]}
    native = [t for name, t in new.items() if name.startswith("fm_native_")]
    preserved = all(new.get(name) == value for name, value in old.items())
    roles = received["model"].get("roles", []) == source["model"].get("roles", [])
    helpers = len(native) == 20 and all(
        len(t.get("partitions", [])) == 1
        and t["partitions"][0].get("source", {}).get("type") == "calculated" for t in native)
    production_unchanged = digest(read_definition(client, SOURCE_MODEL)) == digest(before)
    result = {"Stage": "ONELAKE_TEST_CREATED", "TestModelName": TEST_NAME, "TestModelID": test_id,
              "OriginalModelUnchanged": production_unchanged, "OriginalTablesCopiedExactly": preserved,
              "OriginalRolesCopiedExactly": roles, "NativeCalculatedHelpers": len(native),
              "HelperDefinitionsConfirmed": helpers, "SourceAmountsQueried": False,
              "OriginalModelUpdated": False, "RefreshRequested": False, "ReportPublished": False,
              "DirectLakeCalculatedTablePreview": "Company processing still unverified",
              "R166Parity": "NOT COMPLETE; qualification candidate only"}
    print(json.dumps(result, indent=2), flush=True)
    if not all((preserved, roles, helpers, production_unchanged)):
        raise RuntimeError("Readback needs inspection. Keep this TEST model; do not publish or recreate it.")
    print("NEXT: send this output. Do not change the published report or run the old SQL installer.")
    return result


if __name__ == "__main__":
    create_test_model(fabric.FabricRestClient())
'''


def source_of(module, names):
    tree = ast.parse(inspect.getsource(module))
    return "\n\n".join(ast.get_source_segment(inspect.getsource(module), node)
        for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names)


def render():
    header = '''# ONE NEW TEST semantic model only. The original report/model is never replaced.
# OneLake calculated helpers referencing Direct Lake are a preview compatibility test.
# This file is readable Python. Import the .ipynb instead of copying JSON/base64 text.
import base64
import copy
from copy import deepcopy
import hashlib
import json
import re
import time
from types import SimpleNamespace
from urllib.parse import quote
from uuid import UUID
import sempy.fabric as fabric
'''
    constants = 'PREFIX = "fm_native_"\nORDER = ' + repr(nm.ORDER) + '\n'
    catalog = 'def catalog_rows():\n    return ' + pprint.pformat(nm.catalog_rows(), width=95).replace('\n', '\n    ')
    common = source_of(nm, {"static_tables", "columns_for", "native_table", "extend_model", "measures"})
    dax = "SOURCES = " + repr(nm.SOURCES) + "\n"
    for name in ("FILES", "SCOPE", "GROUPS", "SCENARIO", "LINES"):
        dax += name + " = r'''" + getattr(om, name) + "'''\n\n"
    dax += 'EXPRESSIONS = {"files": FILES, "scope": SCOPE, "groups": GROUPS, "scenario": SCENARIO, "lines": LINES}\n'
    namespace = '''nm = SimpleNamespace(extend_model=extend_model, static_tables=static_tables)
'''
    # Source helper string is split visibly, not one giant encoded line.
    dax = dax.replace("SOURCES = " + repr(nm.SOURCES), "SOURCES = r'''" + nm.SOURCES + "'''")
    return '\n\n'.join((header, constants, catalog, dax, common, namespace,
                         source_of(om, {"datatable", "extend_onelake"}), RUNTIME)) + '\n'


def main():
    code = render()
    compile(code, "CREATE ONELAKE TEST MODEL.py", "exec")
    (HERE / "CREATE ONELAKE TEST MODEL.py").write_text(code)
    notebook = {"nbformat": 4, "nbformat_minor": 5,
                "metadata": {"kernelspec": {"display_name": "Synapse PySpark",
                              "language": "python", "name": "synapse_pyspark"}},
                "cells": [{"cell_type": "markdown", "id": "about", "metadata": {}, "source": [
                    "# ForecastMaster OneLake R17.1 TEST only\n",
                    "Creates a separate test model. Never replaces R16.6 or updates the original model.\n",
                    "Calculated tables that reference Direct Lake are a preview compatibility gate.\n",
                    "No source sales amounts are queried; no refresh or report is published.\n"]},
                    {"cell_type": "code", "id": "create-only", "metadata": {}, "execution_count": None,
                     "outputs": [], "source": code.splitlines(keepends=True)}]}
    (HERE / "ForecastMaster OneLake Test - CREATE ONLY.ipynb").write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({"SourceBytes": len(code.encode()), "SourceLines": len(code.splitlines()),
                      "MaximumLineLength": max(map(len, code.splitlines()))}))


if __name__ == "__main__":
    main()
