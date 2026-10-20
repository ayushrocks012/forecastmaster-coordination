"""Build a separate native worker; original R05.4 files are read-only parents."""

import base64
import hashlib
import json
from pathlib import Path
import zlib

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / "notebook-r05.4"


def build():
    notebook = json.loads((PARENT / "ForecastMaster_Refresh.ipynb").read_text())
    notebook["cells"][0]["source"] = [
        "# ForecastMaster_Native_Adhoc R01\n",
        "Native event requests; unchanged R05.4 ingestion, reporting, retention, model confirmation and shared writer lock.\n",
        "Requires an exact FM_EVENT_SUBJECT. Original hourly and SharePoint request items are unchanged.\n",
    ]
    notebook["cells"][1]["source"] = ['# Event parameter supplied by ForecastMaster_Adhoc.\n', 'FM_EVENT_SUBJECT = ""\n']
    support = (ROOT / "native_consumer.py").read_text().replace(
        "from request_worker import REQUEST_NAME, RequestWorker, WorkerRefreshError\n", ""
    )
    notebook["cells"][4]["source"] = (support + "\n" + (ROOT / "native_preflight.txt").read_text()).splitlines(True)
    execute = (PARENT / "build/execute_cell.txt").read_text()
    old = 'if fm_mode == "HOURLY":\n    engine, worker_result = hourly_worker.run(fm_hourly_snapshot, requested_refresh)\nelse:\n    engine, worker_result = request_worker.run(requested_refresh)'
    if execute.count(old) != 1:
        raise ValueError("Parent dispatch differs; no native package built")
    execute = execute.replace(old, 'engine, worker_result = run_native_request(request_worker, FM_EVENT_SUBJECT, requested_refresh)')
    notebook["cells"][12]["source"] = execute.splitlines(True)
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), "native-cell-" + str(index), "exec")
            cell.update(outputs=[], execution_count=None)
    (ROOT / "ForecastMaster_Native_Adhoc.ipynb").write_text(json.dumps(notebook, indent=1) + "\n")
    original_functions = (ROOT.parent / "functions-r05.2/function_app.py").read_text()
    functions = (
        "# R06-NATIVE-R01: unchanged R05.2 helpers followed by a native request producer.\n"
        + original_functions + "\n\n" + (ROOT / "native_producer.py").read_text()
        + '''\n\n@udf.connection(argName="lakehouse", alias="ForecastMaster")
@udf.function()
def submitNativeRefreshR06(lakehouse: fn.FabricLakehouseClient) -> str:
    """Queue one native request. This acknowledgement is not refresh completion."""
    files = lakehouse.connectToFiles()
    try:
        return json.dumps(submit_native_request(files), ensure_ascii=False, allow_nan=False, indent=2)
    finally:
        files.close()
'''
    )
    compile(functions, "ForecastMaster-Actions-R06-native.txt", "exec")
    (ROOT / "ForecastMaster-Actions-R06-native.txt").write_text(functions)
    payload = json.dumps(notebook).encode()
    install = (ROOT / "install_native.py").read_bytes()
    cell = f'''# Create the separate native notebook and pipeline. No job, schedule or event rule is started.
import base64, zlib, json, hashlib, requests, notebookutils
_fm_native_bytes = zlib.decompress(base64.b64decode({base64.b64encode(zlib.compress(payload, 9)).decode()!r}))
assert hashlib.sha256(_fm_native_bytes).hexdigest() == {hashlib.sha256(payload).hexdigest()!r}
_fm_native_setup_scope = {{"__name__": "native_setup"}}
exec(zlib.decompress(base64.b64decode({base64.b64encode(zlib.compress(install, 9)).decode()!r})), _fm_native_setup_scope)
_fm_native_setup_scope["install_native"](requests, notebookutils.credentials.getToken, json.loads(_fm_native_bytes))
notebookutils.notebook.exit("READY: native items created and verified; event rule and button still require connection")
'''
    compile(cell, "SETUP NATIVE ADHOC R01", "exec")
    (ROOT / "SETUP NATIVE ADHOC R01.txt").write_text(cell)


if __name__ == "__main__":
    build()
