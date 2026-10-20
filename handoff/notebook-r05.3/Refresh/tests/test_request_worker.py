from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from request_worker import OneLakeQueueStore, RequestWorker, WorkerRefreshError

COMMAND = {"SchemaVersion": 1, "Action": "REFRESH_DEMAND", "Scope": "ALL"}


class FS:
    def __init__(self):
        self.files = {}
        self.reads = []
        self.directories = []

    def add(self, body=None):
        name = "refresh-" + str(uuid4()) + ".json"
        self.files[name] = json.dumps(COMMAND if body is None else body)
        return name

    def ls(self, path):
        return [SimpleNamespace(name=n, isFile=True) for n in self.files]

    def head(self, path, size):
        name = path.rsplit("/", 1)[1]
        self.reads.append(name)
        return self.files[name][:size]

    def mkdirs(self, path):
        self.directories.append(path)
        return True


class Store:
    def __init__(self):
        self.values = {}
        self.busy = False
        self.acquired = self.released = 0
        self.fail_write = None

    def read(self, name):
        return copy.deepcopy(self.values.get(name))

    def write(self, name, body):
        if (
            name == self.fail_write
            or self.fail_write == "batches"
            and name.startswith("batches/")
        ):
            raise OSError("receipt write failed")
        self.values[name] = copy.deepcopy(body)

    def acquire(self):
        self.acquired += 1
        return not self.busy

    def release(self):
        self.released += 1


def setup():
    fs, store = FS(), Store()
    return (
        fs,
        store,
        RequestWorker(
            fs,
            store,
            "Files/Demand/ForecastMaster Refresh Requests",
            "Files/ForecastMasterRefreshState",
        ),
    )


def completed():
    return object(), {
        "Status": "SUCCESS",
        "StageErrors": [],
        "FileResults": {"METADATA_UNCHANGED": 7},
        "ModelRefresh": {"Status": "COMPLETED"},
    }


def test_empty_queue_does_not_start_refresh_or_acquire_writer():
    fs, store, worker = setup()
    _, result = worker.run(lambda: pytest.fail("No refresh should run"))
    assert result["Status"] == "IDLE"
    assert store.acquired == 0
    assert fs.directories == []


def test_multiple_clicks_coalesce_once_and_completed_files_do_not_repeat():
    fs, store, worker = setup()
    fs.add()
    fs.add()
    original = fs.files.copy()
    calls = []

    def refresh():
        calls.append(True)
        return completed()

    _, result = worker.run(refresh)
    assert result["Status"] == "SUCCESS"
    assert len(result["Requests"]) == 2
    assert len(calls) == 1
    assert fs.files == original
    reads = len(fs.reads)
    _, second = worker.run(lambda: pytest.fail("Handled requests must not repeat"))
    assert second["Status"] == "IDLE"
    assert len(fs.reads) == reads
    assert store.released == 1


def test_request_arriving_during_refresh_is_left_for_next_run():
    fs, _, worker = setup()
    fs.add()

    def refresh():
        fs.add()
        return completed()

    worker.run(refresh)
    assert len(worker.pending()) == 1


def test_another_worker_owns_lock_so_no_source_work_runs():
    fs, store, worker = setup()
    fs.add()
    store.busy = True
    _, result = worker.run(lambda: pytest.fail("Writer race"))
    assert result["Status"] == "BUSY"
    assert store.values == {}
    assert store.released == 0
    assert len(worker.pending()) == 1


@pytest.mark.parametrize(
    "summary",
    [
        {"Status": "PARTIAL", "StageErrors": ["model pending"]},
        {"Status": "SUCCESS", "StageErrors": [], "ModelRefresh": {"Status": "PENDING"}},
        {
            "Status": "SUCCESS",
            "StageErrors": [],
            "ModelRefresh": {"Status": "COMPLETED"},
            "FileResults": {"FAILED": 1},
        },
        {
            "Status": "SUCCESS",
            "StageErrors": ["catalog failed"],
            "ModelRefresh": {"Status": "COMPLETED"},
        },
    ],
)
def test_partial_data_or_unconfirmed_model_never_marks_request_success(summary):
    fs, store, worker = setup()
    fs.add()
    with pytest.raises(WorkerRefreshError):
        worker.run(lambda: (None, summary))
    assert store.values["latest.json"]["Status"] == "FAILED"
    assert all(
        r["Status"] == "FAILED"
        for r in store.values["requests.json"]["Requests"].values()
    )
    assert store.released == 1
    assert worker.pending() == []
    # A business user can retry by making a new request; no code toggle.
    fs.add()
    assert len(worker.pending()) == 1


def test_exception_has_failure_receipt_and_releases_lock():
    fs, store, worker = setup()
    fs.add()

    def refresh():
        raise OSError("source unavailable")

    with pytest.raises(WorkerRefreshError):
        worker.run(refresh)
    assert store.values["latest.json"]["Refresh"]["StageErrors"] == [
        "source unavailable"
    ]
    assert store.released == 1


@pytest.mark.parametrize(
    "body",
    [
        {**COMMAND, "Scope": "FILES"},
        {**COMMAND, "SchemaVersion": True},
        {**COMMAND, "Path": "somewhere"},
        [],
        {**COMMAND, "Action": "DELETE"},
    ],
)
def test_request_cannot_change_scope_or_supply_execution_arguments(body):
    fs, store, worker = setup()
    fs.add(body)
    with pytest.raises(WorkerRefreshError):
        worker.run(lambda: pytest.fail("Invalid command ran"))
    assert (
        next(iter(store.values["latest.json"]["Requests"].values()))["Status"]
        == "REJECTED"
    )
    assert store.released == 1


def test_invalid_request_does_not_prevent_other_valid_request_from_running():
    fs, store, worker = setup()
    fs.add({**COMMAND, "Action": "WRONG"})
    fs.add()
    with pytest.raises(WorkerRefreshError):
        worker.run(completed)
    assert {r["Status"] for r in store.values["latest.json"]["Requests"].values()} == {
        "SUCCESS",
        "REJECTED",
    }


@pytest.mark.parametrize("target", ["batches", "requests.json"])
def test_failed_receipt_commit_leaves_request_pending_and_releases_lease(target):
    fs, store, worker = setup()
    fs.add()
    store.fail_write = target
    with pytest.raises(OSError):
        worker.run(completed)
    assert len(worker.pending()) == 1
    assert store.released == 1


def test_corrupt_receipt_index_stops_without_replaying_sources():
    fs, store, worker = setup()
    fs.add()
    store.values["requests.json"] = {
        "SchemaVersion": 1,
        "Requests": {"id": {"Status": "QUEUED"}},
    }
    with pytest.raises(ValueError):
        worker.run(lambda: pytest.fail("Corrupt state must be investigated"))
    assert store.acquired == 0


class HTTP:
    def __init__(self, mode="ok"):
        self.mode, self.calls, self.active = mode, [], False

    def put(self, url, **kwargs):
        self.calls.append((url, kwargs))
        headers = kwargs["headers"]
        assert headers["x-ms-date"].endswith(" GMT")
        action = headers.get("x-ms-lease-action")
        if action == "acquire":
            if self.mode == "busy":
                return SimpleNamespace(
                    status_code=409, headers={"x-ms-error-code": "LeaseAlreadyPresent"}
                )
            if self.mode == "unsupported":
                return SimpleNamespace(status_code=201, headers={})
            self.active = True
            return SimpleNamespace(
                status_code=201,
                headers={"x-ms-lease-id": headers["x-ms-proposed-lease-id"]},
            )
        if action == "release":
            self.active = False
            return SimpleNamespace(status_code=200, headers={})
        return SimpleNamespace(status_code=201, headers={})


def test_onelake_writer_uses_exclusive_infinite_lease_and_releases():
    http = HTTP()
    store = OneLakeQueueStore(
        str(uuid4()), str(uuid4()), lambda audience: "test", http=http
    )
    assert store.acquire()
    assert http.active
    assert http.calls[-1][1]["headers"]["x-ms-lease-duration"] == "-1"
    store.release()
    assert not http.active


def test_unsupported_lease_fails_before_forecast_execution():
    store = OneLakeQueueStore(
        str(uuid4()), str(uuid4()), lambda audience: "test", http=HTTP("unsupported")
    )
    with pytest.raises(RuntimeError, match="No refresh started"):
        store.acquire()


def test_busy_lease_is_a_skip_not_an_execution():
    store = OneLakeQueueStore(
        str(uuid4()), str(uuid4()), lambda audience: "test", http=HTTP("busy")
    )
    assert not store.acquire()
