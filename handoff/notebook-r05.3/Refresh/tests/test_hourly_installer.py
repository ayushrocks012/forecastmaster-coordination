"""The one-time handoff retains the maintained item and notebook parameters."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_current_files import HTTP, Store, upgrade

ROOT = Path(__file__).resolve().parents[2]


def test_install_preserves_hourly_parameter_tags_and_company_attachment() -> None:
    notebook = json.loads((ROOT / "ForecastMaster_Refresh.ipynb").read_text())
    http, store = HTTP(), Store()
    upgrade.install(http, lambda _: "synthetic-test-token", store, notebook)
    saved = upgrade.content(http.definition)
    cells = [cell for cell in saved["cells"] if "parameters" in cell.get("metadata", {}).get("tags", [])]
    assert len(cells) == 1
    assert 'FM_RUN_MODE = "REQUESTS"' in "".join(cells[0]["source"])
    assert 'FM_METADATA_JSON = ""' in "".join(cells[0]["source"])
    assert saved["metadata"] == {"attachedLakehouse": "company-original"}
    assert store.writes[0][0].startswith("upgrades/r053-")


def test_install_detects_lost_parameter_cell_tags() -> None:
    class LosingTags(HTTP):
        def request(self, method, url, **kwargs):
            result = super().request(method, url, **kwargs)
            if url.endswith("/updateDefinition"):
                value = upgrade.content(self.definition)
                value["cells"][1]["metadata"]["tags"] = []
                import base64
                self.definition["parts"][0]["payload"] = base64.b64encode(json.dumps(value).encode()).decode()
            return result
    notebook = json.loads((ROOT / "ForecastMaster_Refresh.ipynb").read_text())
    store = Store()
    with pytest.raises(RuntimeError, match="verification failed"):
        upgrade.install(LosingTags(), lambda _: "synthetic-test-token", store, notebook)
    assert store.released


def test_single_cell_installer_is_compilable_and_stops_the_old_notebook() -> None:
    cell = upgrade.build_cell(ROOT)
    compile(cell, "R05.3-installer", "exec")
    assert "notebookutils.notebook.exit(" in cell
    assert "/schedules" not in cell and "createNotebook" not in cell


def test_generated_installer_executes_backup_update_verification_and_exit(monkeypatch) -> None:
    from test_worker_notebook import ExitNotebook
    http = HTTP()
    blob_calls = []
    def put(url, **kwargs):
        blob_calls.append((url, kwargs))
        headers = kwargs.get("headers", {})
        if headers.get("x-ms-lease-action") == "acquire":
            return SimpleNamespace(status_code=201, headers={"x-ms-lease-id": headers["x-ms-proposed-lease-id"]})
        if headers.get("x-ms-lease-action") == "release":
            return SimpleNamespace(status_code=200, headers={})
        return SimpleNamespace(status_code=201, headers={})
    def leave(value):
        raise ExitNotebook(value)
    monkeypatch.setitem(sys.modules, "requests", SimpleNamespace(request=http.request, put=put))
    monkeypatch.setitem(sys.modules, "notebookutils", SimpleNamespace(
        credentials=SimpleNamespace(getToken=lambda _: "synthetic-token"),
        notebook=SimpleNamespace(exit=leave),
    ))
    with pytest.raises(ExitNotebook, match="UPDATED: ForecastMaster_Refresh R05.3"):
        exec(upgrade.build_cell(ROOT), {})  # noqa: S102 -- exercise the exact generated installer locally
    backups = [(url, kwargs) for url, kwargs in blob_calls if "/upgrades/r053-" in url]
    assert len(backups) == 1
    retained = json.loads(backups[0][1]["data"])
    assert retained["NotebookID"] == upgrade.NOTEBOOK and "Definition" in retained
    assert "R05.3" in "".join(upgrade.content(http.definition)["cells"][0]["source"])
    assert blob_calls[-1][1]["headers"]["x-ms-lease-action"] == "release"
