"""Installer qualification with exact saved artifacts and injected API failures."""

from __future__ import annotations

import ast
import base64
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent
HANDOFF = ROOT.parents[1]
spec = importlib.util.spec_from_file_location(
    "install_hourly", ROOT / "install_hourly.py"
)
assert spec and spec.loader
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def saved_notebook():
    return json.loads(
        (HANDOFF / "notebook-r05.4/ForecastMaster_Refresh.ipynb").read_text(
            encoding="utf-8"
        )
    )


def patches():
    before = saved_notebook()
    after = json.loads(
        (ROOT.parent / "candidate/ForecastMaster_Refresh.ipynb").read_text(
            encoding="utf-8"
        )
    )
    return [
        {
            "Name": f"cell-{i:02d}",
            "Before": "".join(before["cells"][i]["source"]),
            "After": "".join(after["cells"][i]["source"]),
        }
        for i in (4, 8, 10, 12)
    ]


def definition(n):
    return {
        "format": "ipynb",
        "parts": [
            {
                "path": "notebook-content.ipynb",
                "payloadType": "InlineBase64",
                "payload": base64.b64encode(json.dumps(n).encode()).decode(),
            },
            {
                "path": ".platform",
                "payloadType": "InlineBase64",
                "payload": base64.b64encode(b'{"metadata":"retained"}').decode(),
            },
        ],
    }


class Response:
    def __init__(self, body, status=200, headers=None):
        self.body, self.status_code, self.headers = body, status, headers or {}

    def json(self):
        return copy.deepcopy(self.body)


class Store:
    def __init__(self):
        self.held = False
        self.busy = False
        self.values = {}
        self.released = 0
        self.bad_read = False

    def acquire(self):
        if self.busy:
            return False
        self.held = True
        return True

    def release(self):
        assert self.held
        self.held = False
        self.released += 1

    def write(self, name, value):
        assert self.held
        self.values[name] = copy.deepcopy(value)

    def read(self, name):
        assert self.held
        return {} if self.bad_read else copy.deepcopy(self.values.get(name))


class HTTP:
    def __init__(self, notebook=None):
        self.definition = definition(saved_notebook() if notebook is None else notebook)
        self.calls = []
        self.reads = 0
        self.concurrent = False
        self.bad_save = False
        self.wrong_item = False
        self.fail_update = False

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if url.endswith(M.ITEM):
            assert method == "GET"
            return Response(
                {
                    "id": M.NOTEBOOK,
                    "displayName": "wrong"
                    if self.wrong_item
                    else "ForecastMaster_Refresh",
                }
            )
        if url.endswith("/getDefinition?format=ipynb"):
            assert method == "POST"
            self.reads += 1
            if self.concurrent and self.reads == 2:
                doc = M.content(self.definition)
                doc["metadata"]["other-editor"] = "changed"
                self.definition = definition(doc)
            return Response({"definition": self.definition})
        if url.endswith("/updateDefinition"):
            assert method == "POST"
            if self.fail_update:
                return Response({}, status=503)
            self.definition = copy.deepcopy(kwargs["json"]["definition"])
            if self.bad_save:
                doc = M.content(self.definition)
                doc["cells"][8]["source"] = ["changed by injection"]
                self.definition = definition(doc)
            return Response({})
        raise AssertionError("Unexpected endpoint: " + url)


def mutations(http):
    return [c for c in http.calls if c[1].endswith("/updateDefinition")]


def test_updates_four_cells_and_preserves_parameters_metadata_other_cells():
    before = saved_notebook()
    before["metadata"]["preserved-custom"] = {"x": 1}
    before["cells"][1]["source"] = [
        'FM_RUN_MODE="REQUESTS"\nFM_METADATA_JSON="operator value"\n'
    ]
    http, store = HTTP(before), Store()
    result = M.install(http, lambda _: "fake", store, patches())
    after = M.content(http.definition)
    assert result["Status"] == "HOURLY_NOTEBOOK_UPDATED" and result["ChangedCells"] == [
        4,
        8,
        10,
        12,
    ]
    assert after["metadata"] == before["metadata"]
    for i in range(len(before["cells"])):
        if i not in {4, 8, 10, 12}:
            assert after["cells"][i] == before["cells"][i]
    assert result["WorkbookReads"] == 0 and not result["RefreshStarted"]
    assert (
        not result["FunctionsUpdated"]
        and store.released == 1
        and len(mutations(http)) == 1
    )
    assert M.content(next(iter(store.values.values()))["Definition"]) == before


def test_already_installed_is_idempotent_and_does_not_write_backup():
    http, store = HTTP(), Store()
    M.install(http, lambda _: "fake", store, patches())
    count = len(mutations(http))
    backups = len(store.values)
    result = M.install(http, lambda _: "fake", store, patches())
    assert result["Status"] == "HOURLY_NOTEBOOK_ALREADY_UPDATED"
    assert len(mutations(http)) == count and len(store.values) == backups


def test_partially_installed_known_cells_complete_only_remaining_cells():
    before = saved_notebook()
    before["cells"][4]["source"] = patches()[0]["After"].splitlines(True)
    http, store = HTTP(before), Store()
    assert M.install(http, lambda _: "fake", store, patches())["ChangedCells"] == [
        8,
        10,
        12,
    ]


@pytest.mark.parametrize("index", [4, 8, 10, 12])
def test_unknown_customization_fails_before_any_update_or_backup(index):
    before = saved_notebook()
    before["cells"][index]["source"].append("\noperator_change = 1\n")
    http, store = HTTP(before), Store()
    with pytest.raises(ValueError, match="differs"):
        M.install(http, lambda _: "fake", store, patches())
    assert not mutations(http) and not store.values and store.released == 1


def test_duplicate_matching_cell_fails_before_update():
    before = saved_notebook()
    before["cells"].append(copy.deepcopy(before["cells"][4]))
    http, store = HTTP(before), Store()
    with pytest.raises(ValueError):
        M.install(http, lambda _: "fake", store, patches())
    assert not mutations(http)


@pytest.mark.parametrize(
    "failure", ["busy", "wrong-item", "backup", "concurrent", "bad-save", "update"]
)
def test_failure_boundaries(failure):
    http, store = HTTP(), Store()
    store.busy = failure == "busy"
    store.bad_read = failure == "backup"
    http.wrong_item = failure == "wrong-item"
    http.concurrent = failure == "concurrent"
    http.bad_save = failure == "bad-save"
    http.fail_update = failure == "update"
    with pytest.raises((RuntimeError, ValueError)):
        M.install(http, lambda _: "fake", store, patches())
    assert len(mutations(http)) == (1 if failure in {"bad-save", "update"} else 0)
    assert store.released == (0 if failure in {"busy", "wrong-item"} else 1)


def test_long_running_get_and_update_wait_and_do_not_repeat_mutations(monkeypatch):
    calls = []

    def request(method, url, **kwargs):
        calls.append((method, url))
        if "/operations/" not in url:
            return Response(
                {},
                202,
                {
                    "x-ms-operation-id": "c5b9233f-8246-498d-8a24-276d382b837e",
                    "Retry-After": "1",
                },
            )
        if url.endswith("/result"):
            return Response({"definition": {"parts": []}})
        return Response({"status": "Succeeded"})

    monkeypatch.setattr(M.time, "sleep", lambda _: None)
    http = SimpleNamespace(request=request)
    M.api(http, lambda _: "fake", "POST", M.ITEM + "/getDefinition?format=ipynb")
    M.api(
        http,
        lambda _: "fake",
        "POST",
        M.ITEM + "/updateDefinition",
        json={"definition": {}},
    )
    assert sum(method == "POST" for method, _ in calls) == 2
    assert sum(url.endswith("/result") for _, url in calls) == 1


def test_packed_installer_executes_exact_saved_file_with_stubs(monkeypatch):
    import sys

    class Done(Exception):
        pass

    http = HTTP()
    store = Store()
    # Exercise the saved encoded module and patch payload, including its final exit.
    original = Path(ROOT / "01 - UPDATE HOURLY NOTEBOOK.txt").read_text(
        encoding="utf-8"
    )
    fake_requests = SimpleNamespace(request=http.request)
    # The embedded store writes are routed to the same synthetic in-memory store.
    fake_requests.get = lambda *args, **kwargs: Response({})
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    def exit_(value):
        raise Done(value)

    utils = SimpleNamespace(
        credentials=SimpleNamespace(getToken=lambda _: "fake"),
        notebook=SimpleNamespace(exit=exit_),
    )
    monkeypatch.setitem(sys.modules, "notebookutils", utils)
    lines = original.splitlines(True)
    cut = next(i for i, line in enumerate(lines) if line.startswith("_fm_store ="))
    ns = {}
    exec("".join(lines[:cut]), ns)
    ns["_fm_setup"]["OneLakeQueueStore"] = lambda *args: store
    with pytest.raises(Done) as result:
        exec("".join(lines[cut:]), ns)
    assert json.loads(str(result.value))["Status"] == "HOURLY_NOTEBOOK_UPDATED"
    assert len(mutations(http)) == 1


def test_complete_functions_file_preserves_all_other_function_definitions():
    old = (
        HANDOFF / "native-adhoc-r01/ForecastMaster-Actions-R06-native.txt"
    ).read_text(encoding="utf-8")
    new = (ROOT / "02 - PASTE CURRENT FUNCTIONS.txt").read_text(encoding="utf-8")

    def functions(source):
        return {
            n.name: ast.dump(n, include_attributes=False)
            for n in ast.parse(source).body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef))
        }

    a, b = functions(old), functions(new)
    assert a.keys() == b.keys()
    assert {name for name in a if a[name] != b[name]} == {
        "prepareMetadataDecision",
        "checkDemandChangesR05",
    }
    assert a["submitNativeRefreshR06"] == b["submitNativeRefreshR06"]
    compile(new, "functions", "exec")
