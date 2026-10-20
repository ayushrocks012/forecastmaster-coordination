"""Hourly handoff invariants without company access or Spark jobs."""

from __future__ import annotations

import copy
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "source"
sys.path.insert(0, str(SOURCE))
from fast_refresh import FastRefresh
from hourly_worker import (
    HourlyWorker,
    checked_snapshot,
    hourly_changes,
    metadata_fingerprint,
    parse_hourly_manifest,
    validate_processed_snapshot,
)
from request_worker import WorkerRefreshError

NAME = "UK_Core Oral_Bridge_Oct 26_EF-Sep 26_IMS-Aug 26_ADS.xlsm"
PATH = "2026/10 Oct 26/Bridge Files/" + NAME


def inventory() -> list[dict[str, Any]]:
    return [
        {
            "Path": PATH,
            "Bytes": 10,
            "ModifiedAtUtc": "2026-10-19T12:00:00+00:00",
            "ETag": "version-1",
        }
    ]


def snapshot(rows: Any = None, at: str = "2026-10-19T13:00:00+00:00") -> dict[str, Any]:
    rows = inventory() if rows is None else rows
    return {
        "SchemaVersion": 1,
        "SourceRoot": "Files/Demand",
        "CapturedAtUtc": at,
        "Fingerprint": metadata_fingerprint(rows),
        "Files": copy.deepcopy(rows),
    }


def engine(rows: Any = None) -> Any:
    rows = inventory() if rows is None else rows
    return SimpleNamespace(
        discovery_metadata=[
            {
                "relative": row["Path"],
                "size": row["Bytes"],
                "modified": row["ModifiedAtUtc"],
            }
            for row in rows
        ],
        events=[
            {"SourceRelativePath": row["Path"], "Status": "SUCCEEDED"} for row in rows
        ],
    )


def summary() -> dict[str, Any]:
    return {
        "RunID": "synthetic-refresh",
        "Status": "SUCCESS",
        "StageErrors": [],
        "FileResults": {"SUCCEEDED": 1},
        "ModelRefresh": {"Status": "COMPLETED"},
    }


class Store:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}
        self.busy = False
        self.held = False
        self.released = 0
        self.fail_write = ""
        self.writes: list[str] = []

    def acquire(self) -> bool:
        if self.busy:
            return False
        assert not self.held
        self.held = True
        return True

    def release(self) -> None:
        assert self.held
        self.held = False
        self.released += 1

    def read(self, name: str) -> Any:
        assert self.held
        return copy.deepcopy(self.values.get(name))

    def write(self, name: str, value: Any) -> None:
        assert self.held
        if name == self.fail_write:
            raise OSError("injected receipt write failure")
        self.writes.append(name)
        self.values[name] = copy.deepcopy(value)


def worker(store: Store) -> HourlyWorker:
    return HourlyWorker(
        SimpleNamespace(mkdirs=lambda _: True),
        store,
        "Files/ForecastMasterRefreshState",
    )


def test_first_success_commits_baseline_after_refresh_under_the_same_lease() -> None:
    store = Store()

    def refresh(changed: list[str]) -> Any:
        assert store.held and "metadata-success.json" not in store.values
        assert changed == [PATH]
        return engine(), summary()

    _, result = worker(store).run(snapshot(), refresh)
    assert result["Status"] == "SUCCESS"
    baseline = store.values["metadata-success.json"]
    assert baseline["RefreshRunID"] == "synthetic-refresh"
    assert baseline["Fingerprint"] == snapshot()["Fingerprint"]
    assert store.writes.index(result["BaselineReceipt"]) < store.writes.index(
        "metadata-success.json"
    )
    assert store.released == 1 and not store.held


def test_unchanged_under_lease_skips_refresh_and_does_not_write_receipts() -> None:
    store = Store()
    worker(store).run(snapshot(), lambda _: (engine(), summary()))
    before = copy.deepcopy(store.values)

    def unexpected(_: Any) -> Any:
        raise AssertionError("Unchanged snapshot started ingestion")

    _, result = worker(store).run(snapshot(), unexpected)
    assert result["Status"] == "IDLE" and store.values == before
    assert store.released == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("ETag", "version-2"),
        ("Bytes", 11),
        ("ModifiedAtUtc", "2026-10-19T12:01:00+00:00"),
    ],
)
def test_only_the_changed_path_requires_content_check(field: str, value: Any) -> None:
    rows = inventory() + [{**inventory()[0], "Path": "other/" + NAME}]
    old = {**snapshot(rows), "Status": "SUCCESS", "RefreshRunID": "previous"}
    rows[0][field] = value
    new = snapshot(rows, "2026-10-19T14:00:00+00:00")
    assert hourly_changes(new, old) == [PATH]


def test_deletion_only_still_runs_a_complete_inventory() -> None:
    old = {
        **snapshot(inventory() + [{**inventory()[0], "Path": "old/" + NAME}]),
        "Status": "SUCCESS",
        "RefreshRunID": "previous",
    }
    assert hourly_changes(snapshot(at="2026-10-19T14:00:00+00:00"), old) == []


@pytest.mark.parametrize(
    "failure",
    [
        "partial",
        "unconfirmed-model",
        "file-failed",
        "stage-error",
        "exception",
        "inventory-race",
        "unsupported-profile",
    ],
)
def test_failed_refresh_does_not_advance_the_baseline(failure: str) -> None:
    store = Store()
    old = snapshot(at="2026-10-19T11:00:00+00:00")
    old["Files"][0]["ETag"] = "older"
    old["Fingerprint"] = metadata_fingerprint(old["Files"])
    old.update(Status="SUCCESS", RefreshRunID="previous")
    store.values["metadata-success.json"] = copy.deepcopy(old)

    def refresh(_: Any) -> Any:
        e, s = engine(), summary()
        if failure == "exception":
            raise RuntimeError("injected refresh failure")
        if failure == "partial":
            s["Status"] = "PARTIAL"
        if failure == "unconfirmed-model":
            s["ModelRefresh"]["Status"] = "ACCEPTED_UNCONFIRMED"
        if failure == "file-failed":
            s["FileResults"]["FAILED"] = 1
        if failure == "stage-error":
            s["StageErrors"] = ["injected"]
        if failure == "inventory-race":
            e.discovery_metadata[0]["size"] = 12
        if failure == "unsupported-profile":
            e.events[0]["Status"] = "OTHER_PROFILE"
        return e, s

    with pytest.raises((RuntimeError, ValueError)):
        worker(store).run(snapshot(), refresh)
    assert store.values["metadata-success.json"] == old
    assert store.released == 1
    assert any(name.startswith("hourly/failed-") for name in store.values)


def test_baseline_pointer_write_failure_retains_previous_success() -> None:
    store = Store()
    store.fail_write = "metadata-success.json"
    with pytest.raises(OSError):
        worker(store).run(snapshot(), lambda _: (engine(), summary()))
    assert "metadata-success.json" not in store.values and store.released == 1


def test_busy_writer_is_a_failed_hourly_attempt_and_leaves_baseline_unmodified() -> (
    None
):
    store = Store()
    store.busy = True
    with pytest.raises(WorkerRefreshError, match="writer lock"):
        worker(store).run(snapshot(), lambda _: (engine(), summary()))
    assert store.values == {} and store.released == 0


def test_stale_different_snapshot_cannot_replace_a_newer_baseline() -> None:
    old = snapshot()
    newer = snapshot(at="2026-10-19T14:00:00+00:00")
    newer["Files"][0]["ETag"] = "new"
    newer["Fingerprint"] = metadata_fingerprint(newer["Files"])
    newer.update(Status="SUCCESS", RefreshRunID="newer")
    with pytest.raises(ValueError, match="stale"):
        hourly_changes(old, newer)


def test_manifest_requires_detector_output_and_a_valid_fingerprint() -> None:
    value = {
        "SchemaVersion": 1,
        "Status": "BASELINE_REQUIRED",
        "NeedsRefresh": True,
        "WorkbookContentsRead": False,
        "CurrentFiles": 1,
        "Snapshot": snapshot(),
    }
    assert parse_hourly_manifest(json.dumps(value)) == value["Snapshot"]
    for text in ("", "{}", json.dumps({**value, "WorkbookContentsRead": True})):
        with pytest.raises(ValueError):
            parse_hourly_manifest(text)
    bad = snapshot()
    bad["Fingerprint"] = "tampered"
    with pytest.raises(ValueError):
        checked_snapshot(bad)


def test_timezone_equivalence_and_spark_naive_utc_match_the_gate() -> None:
    e = engine()
    e.discovery_metadata[0]["modified"] = "2026-10-19T12:00:00"
    validate_processed_snapshot(e, snapshot())
    e.discovery_metadata[0]["modified"] = "2026-10-19T13:00:00+01:00"
    validate_processed_snapshot(e, snapshot())


def test_etag_only_changed_path_bypasses_the_mtime_size_shortcut() -> None:
    class FileReadRequired(Exception):
        pass

    class Spark:
        def read(self) -> Any:
            raise FileReadRequired

        read = property(read)

    config = {
        "SOURCE_ROOT": "Files/Demand",
        "TABLE_PREFIX": "test",
        "ALLOWED_PROFILES": ["Ext"],
        "FORCE_REHASH_PATHS": [PATH.upper()],
    }
    e = FastRefresh(Spark(), {"CONTRACT": "test"}, config)
    e.completed = {"same": {"SourceProfile": "Ext"}}
    meta = {
        "path": "synthetic-path",
        "relative": PATH,
        "modified": "2026-10-19T12:00:00",
        "size": 10,
        "name": NAME,
    }
    prior = {meta["path"]: (meta["modified"], "10", "same")}
    with pytest.raises(FileReadRequired):
        e.ingest_one(meta, prior)
    e.config["FORCE_REHASH_PATHS"] = ["another/" + NAME]
    e.ingest_one(meta, prior)
    assert e.events[-1]["Status"] == "METADATA_UNCHANGED"


def test_gate_and_worker_fingerprints_have_identical_semantics() -> None:
    path = Path("/tmp/forecastmaster-native-check-r05-2/function_app.py")
    if not path.exists():
        pytest.skip("Cross-package SDK source fixture is external to this handoff")
    # Extract the pure functions, without loading the function runtime or any SDK.
    import ast

    tree = ast.parse(path.read_text())
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"canonicalInventory", "inventoryFingerprint"}
    ]
    namespace: dict[str, Any] = {
        "Any": Any,
        "datetime": datetime,
        "UTC": UTC,
        "hashlib": __import__("hashlib"),
        "json": json,
        "bridgePattern": __import__("hourly_worker").BRIDGE,
    }
    exec(  # noqa: S102 -- reviewed pure helper AST only
        compile(ast.Module(body=selected, type_ignores=[]), "gate-pure", "exec"),
        namespace,
    )
    assert namespace["inventoryFingerprint"](inventory()) == metadata_fingerprint(
        inventory()
    )


def test_notebook_hourly_preflight_uses_parameters_without_reading_request_queue(
    monkeypatch: Any,
) -> None:
    from test_worker_notebook import code_cells

    def unexpected_queue(_: str) -> Any:
        raise AssertionError("Hourly preflight consulted the button queue")

    fake = SimpleNamespace(
        runtime=SimpleNamespace(
            context={
                "defaultLakehouseId": "d6e33ebd-67b1-420a-8d84-c3a0d04d8b21",
                "defaultLakehouseWorkspaceId": "f5cb5742-9a7c-4337-a4c0-952706dddf0b",
            }
        ),
        credentials=SimpleNamespace(getToken=lambda _: "synthetic"),
        fs=SimpleNamespace(ls=unexpected_queue),
    )
    value = {
        "SchemaVersion": 1,
        "Status": "BASELINE_REQUIRED",
        "NeedsRefresh": True,
        "WorkbookContentsRead": False,
        "CurrentFiles": 1,
        "Snapshot": snapshot(),
    }
    monkeypatch.setitem(sys.modules, "notebookutils", fake)
    cells = code_cells()
    namespace = {"FM_RUN_MODE": "HOURLY", "FM_METADATA_JSON": json.dumps(value)}
    for cell in cells[:3]:
        exec(cell, namespace)  # noqa: S102 -- execute the saved notebook preflight
    assert namespace["fm_hourly_snapshot"] == value["Snapshot"]
    assert "request_worker" not in namespace
    assert "BridgeReader" not in namespace and "run_refresh" not in namespace


def test_notebook_final_cell_passes_changed_paths_and_returns_explicit_result(
    monkeypatch: Any,
) -> None:
    import pyspark.sql
    from test_worker_notebook import ExitNotebook, code_cells

    fake_spark = object()
    monkeypatch.setattr(
        pyspark.sql,
        "SparkSession",
        SimpleNamespace(builder=SimpleNamespace(getOrCreate=lambda: fake_spark)),
    )
    captured: list[dict[str, Any]] = []

    def run_refresh(
        spark: Any, reader: Any, config: Any, utils: Any, rules: str
    ) -> Any:
        assert spark is fake_spark and "ims-market-units" in rules
        captured.append(config)
        return SimpleNamespace(events=[], timings=[]), summary()

    class Hourly:
        def run(self, snap: Any, callback: Any) -> Any:
            assert snap == snapshot()
            callback([PATH])
            return None, {"Status": "SUCCESS", "Mode": "HOURLY", "Refresh": summary()}

    def leave(value: str) -> None:
        raise ExitNotebook(value)

    namespace: dict[str, Any] = {
        "fm_mode": "HOURLY",
        "fm_hourly_snapshot": snapshot(),
        "hourly_worker": Hourly(),
        "run_refresh": run_refresh,
        "refresh_confirmed_model": object(),
        "json": json,
        "notebookutils": SimpleNamespace(notebook=SimpleNamespace(exit=leave)),
    }
    cells = code_cells()
    exec(cells[0], namespace)  # noqa: S102 -- execute the saved notebook defaults
    with pytest.raises(ExitNotebook) as result:
        exec(cells[-1], namespace)  # noqa: S102 -- execute the saved notebook entrypoint
    assert json.loads(str(result.value))["Status"] == "SUCCESS"
    assert captured[0]["REFRESH_MODE"] == "ALL"
    assert captured[0]["FORCE_REHASH_PATHS"] == [PATH]
    assert captured[0]["FORCE_MODEL_REFRESH"] is False
