from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = "f5cb5742-9a7c-4337-a4c0-952706dddf0b"
LAKEHOUSE = "d6e33ebd-67b1-420a-8d84-c3a0d04d8b21"


class ExitNotebook(Exception):
    pass


def code_cells():
    notebook = json.loads((ROOT.parent / "ForecastMaster_Refresh.ipynb").read_text())
    return [
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code" and "parameters" not in cell.get("metadata", {}).get("tags", [])
    ]


def test_idle_notebook_exits_before_importing_reader_or_starting_ingestion(monkeypatch):
    def leave(value):
        raise ExitNotebook(value)

    fake = SimpleNamespace(
        runtime=SimpleNamespace(
            context={
                "defaultLakehouseId": LAKEHOUSE,
                "defaultLakehouseWorkspaceId": WORKSPACE,
            }
        ),
        fs=SimpleNamespace(ls=lambda path: []),
        credentials=SimpleNamespace(getToken=lambda audience: "test"),
        notebook=SimpleNamespace(exit=leave),
    )
    monkeypatch.setitem(sys.modules, "notebookutils", fake)
    monkeypatch.setattr(
        requests, "get", lambda *args, **kw: SimpleNamespace(status_code=404)
    )
    namespace = {"FM_RUN_MODE": "REQUESTS", "FM_METADATA_JSON": ""}
    cells = code_cells()
    exec(cells[0], namespace)
    exec(cells[1], namespace)
    with pytest.raises(ExitNotebook, match="IDLE"):
        exec(cells[2], namespace)
    assert "BridgeReader" not in namespace
    assert "run_refresh" not in namespace
    assert "SparkSession" not in namespace


def test_wrong_default_lakehouse_stops_before_queue_or_source_access(monkeypatch):
    fake = SimpleNamespace(
        runtime=SimpleNamespace(context={"defaultLakehouseId": "wrong"})
    )
    monkeypatch.setitem(sys.modules, "notebookutils", fake)
    namespace = {"FM_RUN_MODE": "REQUESTS", "FM_METADATA_JSON": ""}
    cells = code_cells()
    exec(cells[0], namespace)
    exec(cells[1], namespace)
    with pytest.raises(RuntimeError, match="Attach ForecastMaster"):
        exec(cells[2], namespace)


def test_decoder_preserved_and_notebook_matches_current_runtime_sources():
    receipt = json.loads((ROOT / "PARENT_SOURCE_HASHES.json").read_text())
    assert hashlib.sha256((ROOT / "source/reader.py").read_bytes()).hexdigest() == receipt["SourceSHA256"]["reader.py"]
    notebook=json.loads((ROOT.parent / "ForecastMaster_Refresh.ipynb").read_text())
    for index,name in {2:"request_worker",4:"reader",5:"fast_refresh",6:"catalog",7:"reporting",8:"model_refresh",9:"run",10:"confirmed_model"}.items():
        source=(ROOT / "source" / (name + ".py")).read_text()
        if name=="run":
            source="".join(line for line in source.splitlines(True) if not line.startswith(("from catalog import ","from fast_refresh import ","from model_refresh import ","from reporting import ")))
        assert "".join(notebook["cells"][index + 1]["source"]) == source
