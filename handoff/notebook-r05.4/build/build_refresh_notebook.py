"""Rebuild R05.4 from the readable modules and cell templates; no cloud actions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "ForecastMaster_Refresh.ipynb"
notebook = json.loads(path.read_text())
modules = {3:"request_worker",5:"reader",6:"fast_refresh",7:"catalog",8:"reporting",9:"model_refresh",10:"run",11:"confirmed_model"}
for index, module in modules.items():
    source = (ROOT / "Refresh/source" / (module + ".py")).read_text()
    if module == "run":
        source = "".join(line for line in source.splitlines(True) if not line.startswith(("from catalog import ","from fast_refresh import ","from model_refresh import ","from reporting import ")))
    notebook["cells"][index]["source"] = source.splitlines(True)
hourly = (ROOT / "Refresh/source/hourly_worker.py").read_text().replace("from request_worker import WorkerRefreshError, queue_utc\n", "")
notebook["cells"][4]["source"] = (hourly + "\n" + (ROOT/"build/preflight_cell.txt").read_text()).splitlines(True)
notebook["cells"][12]["source"] = (ROOT/"build/execute_cell.txt").read_text().splitlines(True)
for index, cell in enumerate(notebook["cells"]):
    if cell["cell_type"] == "code":
        compile("".join(cell["source"]), "cell-"+str(index), "exec")
        cell["outputs"] = []
        cell["execution_count"] = None
assert notebook["cells"][1]["metadata"]["tags"] == ["parameters"]
path.write_text(json.dumps(notebook, indent=1)+"\n")
print("Rebuilt the one R05.4 notebook; company runtime qualification is pending.")
