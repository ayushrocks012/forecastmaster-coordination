"""Pure inventory decisions and native probe lifecycle; no company services."""

import copy
import json
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from azure.core import MatchConditions
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

from test_function_check import NAME, app


def metadata(path: str | None = None) -> dict[str, Any]:
    return {
        "Path": path or "2026/10 Oct 26/Bridge Files/" + NAME,
        "Bytes": 100,
        "ModifiedAtUtc": "2026-10-19T12:00:00+00:00",
        "ETag": "etag-1",
    }


def discovery(rows: Any) -> dict[str, Any]:
    return {
        "Status": "METADATA_VISIBLE",
        "CompleteDirectoryListing": True,
        "Files": rows,
        "MatchingBridgeFiles": len(rows),
        "MissingMetadataPaths": [],
        "DirectoriesListed": 5,
        "Seconds": 1.0,
    }


def baseline(rows: Any) -> dict[str, Any]:
    return {
        "SchemaVersion": 1,
        "SourceRoot": "Files/Demand",
        "Status": "SUCCESS",
        "RefreshRunID": "synthetic-success",
        "Files": copy.deepcopy(rows),
        "Fingerprint": app.inventoryFingerprint(rows),
    }


def test_unchanged_inventory_skips_refresh() -> None:
    rows = [metadata()]
    result = app.prepareMetadataDecision(discovery(rows), baseline(rows))
    assert result["Status"] == "UNCHANGED" and result["NeedsRefresh"] is False
    assert result["ChangedFiles"] == [] and result["RemovedFiles"] == []


def test_missing_baseline_requests_initial_worker_run_without_creating_a_baseline() -> (
    None
):
    rows = [metadata()]
    result = app.prepareMetadataDecision(discovery(rows), None)
    assert result["Status"] == "BASELINE_REQUIRED" and result["NeedsRefresh"] is True
    assert result["ChangedFiles"] == [rows[0]["Path"]]
    assert "RefreshRunID" not in result["Snapshot"]


@pytest.mark.parametrize(
    "field,value",
    [("Bytes", 0), ("ModifiedAtUtc", "2026-10-19T12:00:01+00:00"), ("ETag", "etag-2")],
)
def test_independent_change_signals_and_one_changed_file(
    field: str, value: Any
) -> None:
    rows = [metadata(), metadata("any-folder/" + NAME)]
    before = baseline(rows)
    rows[0][field] = value
    result = app.prepareMetadataDecision(discovery(rows), before)
    assert result["NeedsRefresh"] is True
    assert result["ChangedFiles"] == [rows[0]["Path"]]


def test_deleted_file_and_renamed_path_are_detected() -> None:
    old = [metadata(), metadata("older-folder/" + NAME)]
    new = [metadata(), metadata("renamed-folder/" + NAME)]
    result = app.prepareMetadataDecision(discovery(new), baseline(old))
    assert result["ChangedFiles"] == [new[1]["Path"]]
    assert result["RemovedFiles"] == [old[1]["Path"].casefold()]


def test_order_case_and_timezone_representation_are_not_new_files() -> None:
    old = [metadata(), metadata("another-folder/" + NAME)]
    new = copy.deepcopy(list(reversed(old)))
    for row in new:
        row["Path"] = row["Path"].upper()
        row["ModifiedAtUtc"] = "2026-10-19T13:00:00+01:00"
    assert (
        app.prepareMetadataDecision(discovery(new), baseline(old))["NeedsRefresh"]
        is False
    )


@pytest.mark.parametrize(
    "change",
    [
        {"Status": "METADATA_INCOMPLETE"},
        {"CompleteDirectoryListing": False},
        {"MatchingBridgeFiles": 0},
        {"MissingMetadataPaths": ["missing"]},
        {"Files": None},
    ],
)
def test_incomplete_or_inconsistent_discovery_cannot_be_committed(change: Any) -> None:
    current = discovery([metadata()])
    current.update(change)
    with pytest.raises((ValueError, TypeError)):
        app.prepareMetadataDecision(current, None)


@pytest.mark.parametrize(
    "change",
    [
        {"Status": "FAILED"},
        {"SourceRoot": "elsewhere"},
        {"RefreshRunID": ""},
        {"Fingerprint": "tampered"},
    ],
)
def test_invalid_baseline_fails_instead_of_skipping(change: Any) -> None:
    rows = [metadata()]
    prior = baseline(rows)
    prior.update(change)
    with pytest.raises(ValueError):
        app.prepareMetadataDecision(discovery(rows), prior)


@pytest.mark.parametrize(
    "change",
    [
        {"Bytes": True},
        {"Bytes": -1},
        {"ETag": ""},
        {"ModifiedAtUtc": "2026-10-19T12:00:00"},
        {"Path": "../" + NAME},
        {"Path": "unrelated.xlsx"},
        {"Path": "~$" + NAME},
    ],
)
def test_bad_metadata_is_not_a_valid_inventory(change: Any) -> None:
    row = metadata()
    row.update(change)
    with pytest.raises((ValueError, TypeError)):
        app.canonicalInventory([row])


def test_empty_and_duplicate_inventory_fail() -> None:
    for rows in [[], [metadata(), metadata()]]:
        with pytest.raises(ValueError):
            app.canonicalInventory(rows)


class FakeFile:
    def __init__(self, path: str, owner: Any):
        self.path, self.owner = path, owner
        self.closed = False

    def upload_data(
        self, data: bytes, overwrite: bool, *, match_condition: Any
    ) -> None:
        assert overwrite is True
        assert match_condition == MatchConditions.IfMissing
        assert self.path not in self.owner.contents
        assert self.path.startswith("ForecastMasterRefreshState/probe-")
        self.owner.contents[self.path] = data

    def download_file(self) -> Any:
        if self.path not in self.owner.contents:
            raise ResourceNotFoundError("missing")
        return SimpleNamespace(readall=lambda: self.owner.contents[self.path])

    def close(self) -> None:
        self.closed = True


class FakeFiles:
    def __init__(self) -> None:
        self.contents = {
            "ForecastMasterRefreshState/latest.json": json.dumps(
                {"SchemaVersion": 1, "Status": "SUCCESS"}
            ).encode()
        }
        self.clients: list[FakeFile] = []
        self.lock: str | None = None
        self.events: list[str] = []

    def get_file_client(self, path: str) -> FakeFile:
        assert "worker.lock" not in path
        client = FakeFile(path, self)
        self.clients.append(client)
        return client


class FakeLease:
    def __init__(self, file: FakeFile):
        self.owner = file.owner
        self.id = str(uuid4())

    def acquire(self, lease_duration: int) -> None:
        assert lease_duration == 60
        if self.owner.lock:
            exc = HttpResponseError("already held")
            exc.status_code = 409
            exc.error_code = "LeaseAlreadyPresent"
            raise exc
        self.owner.lock = self.id
        self.owner.events.append("acquired")

    def renew(self) -> None:
        assert self.owner.lock == self.id
        self.owner.events.append("renewed")

    def release(self) -> None:
        assert self.owner.lock == self.id
        self.owner.lock = None
        self.owner.events.append("released")


def test_native_probe_releases_lock_closes_clients_and_retains_only_small_receipt() -> (
    None
):
    files = FakeFiles()
    result = app.verifyNativeState(files, FakeLease)
    assert result["Status"] == "NATIVE_STATE_READY"
    assert result["CurrentWorkerLockTouched"] is False
    assert files.events == ["acquired", "renewed", "released"]
    assert files.lock is None and all(client.closed for client in files.clients)
    assert len(files.contents) == 2


def test_native_failure_still_releases_probe_lease() -> None:
    class BadRenew(FakeLease):
        def renew(self) -> None:
            raise RuntimeError("renew failed")

    files = FakeFiles()
    with pytest.raises(RuntimeError, match="renew failed"):
        app.verifyNativeState(files, BadRenew)
    assert files.lock is None and all(client.closed for client in files.clients)


def test_missing_control_baseline_is_not_a_read_error() -> None:
    files = FakeFiles()
    assert app.readControlJson(files, "metadata-success.json") is None
    assert files.clients[-1].closed


def test_permission_error_is_not_treated_as_missing_baseline() -> None:
    class Forbidden:
        closed = False

        def download_file(self) -> None:
            exc = HttpResponseError("forbidden")
            exc.status_code = 403
            raise exc

        def close(self) -> None:
            self.closed = True

    denied = Forbidden()
    files = SimpleNamespace(get_file_client=lambda path: denied)
    with pytest.raises(HttpResponseError):
        app.readControlJson(files, "metadata-success.json")
    assert denied.closed
