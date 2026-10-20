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

from request_worker import WorkerRefreshError, queue_utc

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


def validate_processed_snapshot(engine: Any, snapshot: dict[str, Any]) -> None:
    expected = metadata_inventory(snapshot["Files"])
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
        refresh: Callable[[list[str]], tuple[Any, dict[str, Any]]],
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
            changed = hourly_changes(snapshot, self.store.read("metadata-success.json"))
            if changed is None:
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
                len(changed),
                flush=True,
            )
            engine, summary = refresh(changed)
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
                "CodeVersion": "R05.3",
                "Mode": "HOURLY",
                "Status": "SUCCESS",
                "BatchID": batch_id,
                "StartedAtUtc": started,
                "FinishedAtUtc": queue_utc(),
                "Refresh": summary,
                "MetadataFingerprint": snapshot["Fingerprint"],
                "CurrentFiles": len(snapshot["Files"]),
                "ContentChecksRequested": len(changed),
                "BaselineReceipt": "metadata-baselines/" + batch_id + ".json",
            }
            # Retain the full successful metadata before replacing its current pointer.
            self.store.write(result["BaselineReceipt"], baseline)
            self.store.write("hourly/" + batch_id + ".json", result)
            self.store.write("metadata-success.json", baseline)
            self.store.write("latest.json", result)
            return engine, result
        except Exception as exc:
            failure = {
                "SchemaVersion": 1,
                "CodeVersion": "R05.3",
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
