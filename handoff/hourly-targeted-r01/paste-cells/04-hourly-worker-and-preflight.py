"""Coordinate a metadata-gated hourly run through the existing refresh engine.

The Fabric pipeline supplies the complete JSON string from checkDemandChangesR05.
The existing request-only worker and the hourly worker share worker.lock.
Baselines contain only file metadata; workbooks remain inputs.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{2}"
BRIDGE = re.compile(
    r"[^_]+_.+?_Bridge_"
    + MONTH
    + r"_EF-"
    + MONTH
    + r"_IMS-"
    + MONTH
    + r"_.+\.(?:xlsx|xlsm)",
    re.IGNORECASE,
)


def metadata_inventory(rows: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("A complete nonempty bridge inventory is required.")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "Path",
            "Bytes",
            "ModifiedAtUtc",
            "ETag",
        }:
            raise ValueError("Invalid bridge metadata fields.")
        path = row["Path"]
        if (
            not isinstance(path, str)
            or path.startswith("/")
            or "\\" in path
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or path.rsplit("/", 1)[-1].startswith("~$")
            or BRIDGE.fullmatch(path.rsplit("/", 1)[-1]) is None
        ):
            raise ValueError("Invalid relative bridge path.")
        identity = path.casefold()
        if identity in result:
            raise ValueError("Duplicate bridge path.")
        if type(row["Bytes"]) is not int or row["Bytes"] < 0:
            raise ValueError("Bridge byte length is invalid.")
        if not isinstance(row["ETag"], str) or not row["ETag"]:
            raise ValueError("Bridge version metadata is missing.")
        modified = datetime.fromisoformat(row["ModifiedAtUtc"])
        if modified.utcoffset() is None:
            raise ValueError("Bridge metadata needs an explicit timezone.")
        result[identity] = {
            "Path": identity,
            "Bytes": row["Bytes"],
            "ModifiedAtUtc": modified.astimezone(UTC).isoformat(),
            "ETag": row["ETag"],
        }
    return result


def metadata_fingerprint(rows: Any) -> str:
    canonical = metadata_inventory(rows)
    payload = json.dumps(
        [canonical[key] for key in sorted(canonical)],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def checked_snapshot(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or type(value.get("SchemaVersion")) is not int
        or value["SchemaVersion"] != 1
        or value.get("SourceRoot") != "Files/Demand"
    ):
        raise ValueError("Invalid hourly snapshot identity.")
    captured = datetime.fromisoformat(value["CapturedAtUtc"])
    if captured.utcoffset() is None:
        raise ValueError("Hourly snapshot timestamp needs a timezone.")
    if value.get("Fingerprint") != metadata_fingerprint(value.get("Files")):
        raise ValueError("Hourly snapshot fingerprint does not match its inventory.")
    return value


def parse_hourly_manifest(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text:
        raise ValueError(
            "HOURLY mode requires FM_METADATA_JSON from the Functions activity."
        )
    value = json.loads(text)
    if (
        not isinstance(value, dict)
        or type(value.get("SchemaVersion")) is not int
        or value["SchemaVersion"] != 1
        or value.get("Status") not in {"BASELINE_REQUIRED", "CHANGED", "UNCHANGED"}
        or type(value.get("NeedsRefresh")) is not bool
        or value.get("WorkbookContentsRead") is not False
    ):
        raise ValueError("Expected the successful metadata detector output.")
    snapshot = checked_snapshot(value.get("Snapshot"))
    if value.get("CurrentFiles") != len(snapshot["Files"]):
        raise ValueError("Hourly inventory count does not reconcile.")
    return snapshot


def hourly_changes(snapshot: dict[str, Any], baseline: Any) -> list[str] | None:
    """Recheck under the shared writer lease; None means another run handled it."""
    current = metadata_inventory(snapshot["Files"])
    previous: dict[str, dict[str, Any]] = {}
    if baseline is not None:
        checked_snapshot(baseline)
        if baseline.get("Status") != "SUCCESS" or not baseline.get("RefreshRunID"):
            raise ValueError("The committed hourly baseline is invalid.")
        if baseline["Fingerprint"] == snapshot["Fingerprint"]:
            return None
        if datetime.fromisoformat(snapshot["CapturedAtUtc"]) <= datetime.fromisoformat(
            baseline["CapturedAtUtc"]
        ):
            raise ValueError(
                "This metadata snapshot is stale. Run the hourly pipeline again."
            )
        previous = metadata_inventory(baseline["Files"])
    original = {row["Path"].casefold(): row["Path"] for row in snapshot["Files"]}
    # Deletions still need an ALL inventory run, even when this list is empty.
    return [
        original[key] for key in sorted(current) if current[key] != previous.get(key)
    ]


def hourly_refresh_plan(snapshot: dict[str, Any], baseline: Any) -> dict[str, Any] | None:
    """Choose scope again under the existing lease, using the committed baseline."""
    try:
        checked_snapshot(baseline)
        if baseline.get("Status") != "SUCCESS" or not baseline.get("RefreshRunID"):
            raise ValueError("Invalid committed baseline")
    except (KeyError, TypeError, ValueError):
        baseline = None
    changed = hourly_changes(snapshot, baseline)
    if changed is None:
        return None
    removed = sorted(set(metadata_inventory(baseline["Files"]))
                     - set(metadata_inventory(snapshot["Files"]))) if baseline else []
    mode = "ALL" if baseline is None or removed else "FILES"
    return {"Mode": mode, "ChangedFiles": changed, "RemovedFiles": removed}


def targeted_index_valid(spark: Any, config: dict[str, Any], snapshot: dict[str, Any],
                         changed: list[str], contract: str) -> bool:
    """Only compact metadata: untouched paths must already have complete pointers."""
    prefix = config["TABLE_PREFIX"]
    if not all(spark.catalog.tableExists(prefix + suffix)
               for suffix in ("_file_state", "_source_revisions")):
        return False
    expected = metadata_inventory(snapshot["Files"])
    changed_keys = {path.casefold() for path in changed}
    complete = {r[0] for r in spark.table(prefix + "_source_revisions")
                .select("SourceRevisionID").collect()}
    found = set()
    try:
        for row in spark.table(prefix + "_file_state").collect():
            key = row["SourceRelativePath"].casefold()
            if (key in found or key not in expected or row["ReaderContract"] != contract
                    or row["SourceRevisionID"] not in complete):
                return False
            found.add(key)
            if key not in changed_keys:
                modified = datetime.fromisoformat(row["SourceModifiedAt"])
                if modified.utcoffset() is None:
                    modified = modified.replace(tzinfo=UTC)
                if (int(row["SourceBytes"]) != expected[key]["Bytes"]
                        or modified.astimezone(UTC).isoformat() != expected[key]["ModifiedAtUtc"]):
                    return False
    except (KeyError, TypeError, ValueError):
        return False
    return set(expected) - changed_keys <= found


def validate_processed_snapshot(engine: Any, snapshot: dict[str, Any]) -> None:
    expected = metadata_inventory(snapshot["Files"])
    config = getattr(engine, "config", {})
    if config.get("REFRESH_MODE", "ALL") == "FILES":
        selected = {p.casefold() for p in config["SELECTED_RELATIVE_PATHS"]}
        if not selected or not selected <= set(expected):
            raise ValueError("Invalid selected snapshot scope")
        expected = {key: row for key, row in expected.items() if key in selected}
    found: dict[str, dict[str, Any]] = {}
    for meta in engine.discovery_metadata:
        key = meta["relative"].replace("\\", "/").casefold()
        if key in found:
            raise ValueError("Duplicate path in the refresh inventory.")
        found[key] = meta
    if set(found) != set(expected):
        raise ValueError(
            "Bridge paths changed after the metadata check; rerun the hourly pipeline."
        )
    for key, row in expected.items():
        meta = found[key]
        modified = datetime.fromisoformat(meta["modified"])
        # Spark binaryFile materializes modificationTime as a naive UTC datetime.
        if modified.utcoffset() is None:
            modified = modified.replace(tzinfo=UTC)
        if (
            meta["size"] != row["Bytes"]
            or modified.astimezone(UTC).isoformat() != row["ModifiedAtUtc"]
        ):
            raise ValueError(
                "A bridge changed after the metadata check: " + meta["relative"]
            )
    completed = {
        event["SourceRelativePath"].casefold()
        for event in engine.events
        if event["Status"] in {"METADATA_UNCHANGED", "SAME_CONTENT", "SUCCEEDED"}
    }
    if completed != set(expected):
        raise ValueError(
            "Not every inventoried bridge completed successfully; baseline retained."
        )


class HourlyWorker:
    def __init__(self, fs: Any, store: Any, state_folder: str):
        self.fs, self.store, self.state_folder = fs, store, state_folder.rstrip("/")

    def run(
        self,
        snapshot: dict[str, Any],
        refresh: Callable[[dict[str, Any]], tuple[Any, dict[str, Any]]],
    ) -> tuple[Any, dict[str, Any]]:
        snapshot = checked_snapshot(snapshot)
        if not self.store.acquire():
            raise WorkerRefreshError(
                "Another refresh owns the writer lock. Retry the hourly pipeline after it finishes."
            )
        batch_id, started = str(uuid4()), queue_utc()
        engine: Any = None
        summary: dict[str, Any] = {}
        try:
            try:
                baseline = self.store.read("metadata-success.json")
            except (TypeError, ValueError, UnicodeDecodeError):
                baseline = None
            plan = hourly_refresh_plan(snapshot, baseline)
            if plan is None:
                return None, {
                    "Status": "IDLE",
                    "Mode": "HOURLY",
                    "Message": "This inventory was already refreshed successfully.",
                }
            for folder in ("hourly", "metadata-baselines"):
                if not self.fs.mkdirs(self.state_folder + "/" + folder):
                    raise RuntimeError("Cannot prepare hourly receipt folders.")
            print(
                "Hourly metadata changes requiring content checks:",
                len(plan["ChangedFiles"]),
                flush=True,
            )
            engine, summary = refresh(plan)
            if (
                summary.get("Status") != "SUCCESS"
                or summary.get("StageErrors")
                or summary.get("FileResults", {}).get("FAILED", 0)
                or summary.get("ModelRefresh", {}).get("Status")
                not in {"COMPLETED", "UNCHANGED"}
                or not summary.get("RunID")
            ):
                raise WorkerRefreshError(
                    "Ingestion, reporting or model refresh did not succeed; hourly baseline retained."
                )
            validate_processed_snapshot(engine, snapshot)
            baseline = {
                **snapshot,
                "Status": "SUCCESS",
                "RefreshRunID": summary["RunID"],
                "BatchID": batch_id,
                "RecordedAtUtc": queue_utc(),
            }
            result = {
                "SchemaVersion": 1,
                "CodeVersion": "R05.4",
                "Mode": "HOURLY",
                "Status": "SUCCESS",
                "BatchID": batch_id,
                "StartedAtUtc": started,
                "FinishedAtUtc": queue_utc(),
                "Refresh": summary,
                "MetadataFingerprint": snapshot["Fingerprint"],
                "CurrentFiles": len(snapshot["Files"]),
                "ContentChecksRequested": len(plan["ChangedFiles"]),
                "RefreshMode": engine.config["REFRESH_MODE"],
                "BaselineReceipt": "metadata-baselines/" + batch_id + ".json",
            }
            # Retain the full successful metadata before replacing its current pointer.
            self.store.write(result["BaselineReceipt"], baseline)
            self.store.write("hourly/" + batch_id + ".json", result)
            self.store.write("latest.json", result)
            self.store.write("metadata-success.json", baseline)
            return engine, result
        except Exception as exc:
            failure = {
                "SchemaVersion": 1,
                "CodeVersion": "R05.4",
                "Mode": "HOURLY",
                "Status": "FAILED",
                "BatchID": batch_id,
                "StartedAtUtc": started,
                "FinishedAtUtc": queue_utc(),
                "Error": str(exc),
                "Refresh": summary,
            }
            # A separate failure receipt preserves any earlier successful-stage receipt.
            self.store.write("hourly/failed-" + batch_id + ".json", failure)
            raise
        finally:
            self.store.release()

# Verify the destination and check the queue before loading the ingestion code.
import notebookutils

worker_context = notebookutils.runtime.context
if (str(worker_context.get("defaultLakehouseId", "")).lower() != LAKEHOUSE_ID.lower()
    or str(worker_context.get("defaultLakehouseWorkspaceId", "")).lower() != WORKSPACE_ID.lower()):
    raise RuntimeError("Attach ForecastMaster as this notebook's default lakehouse, then run again.")
worker_files_root = f"abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE_ID}/Files"
worker_store = OneLakeQueueStore(WORKSPACE_ID, LAKEHOUSE_ID, notebookutils.credentials.getToken)
fm_mode = str(FM_RUN_MODE).upper()
if fm_mode not in {"REQUESTS", "HOURLY"}:
    raise ValueError("FM_RUN_MODE must be REQUESTS or HOURLY.")
if fm_mode == "HOURLY":
    fm_hourly_snapshot = parse_hourly_manifest(FM_METADATA_JSON)
    hourly_worker = HourlyWorker(notebookutils.fs, worker_store, worker_files_root + "/ForecastMasterRefreshState")
    print("Hourly mode: validated complete metadata snapshot for", len(fm_hourly_snapshot["Files"]), "bridges.", flush=True)
else:
    request_worker = RequestWorker(
        notebookutils.fs, worker_store,
        worker_files_root + "/Demand/ForecastMaster Refresh Requests",
        worker_files_root + "/ForecastMasterRefreshState",
    )
    waiting = request_worker.pending()
    print("New refresh requests:", len(waiting), flush=True)
    if not waiting:
        print("IDLE: no new request; no bridge discovery or model refresh ran.", flush=True)
        notebookutils.notebook.exit('{"Status":"IDLE","PendingRequests":0}')
