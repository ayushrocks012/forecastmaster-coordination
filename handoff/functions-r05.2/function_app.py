# FORECASTMASTER ORCHESTRATION HELPERS R05.2 - first test checkNativeStateR05
"""Prerequisite checks for ForecastMaster's planned refresh coordination.

Paste this complete file into the existing ForecastMaster_Actions function item.
Keep the existing lakehouse connection alias ForecastMaster.
First test checkNativeStateR05: it retains one tiny native test receipt.
This is a capability check, not the finished hourly/on-demand refresh release.
"""

import hashlib
import json
import logging
import re
import time
from collections import deque
from collections.abc import Iterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from uuid import UUID, uuid4

import fabric.functions as fn
from azure.core import MatchConditions
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.storage.filedatalake import (
    DataLakeDirectoryClient,
    DataLakeLeaseClient,
    PathProperties,
)

udf = fn.UserDataFunctions()
logger = logging.getLogger("ForecastMaster.MetadataCheck")

# Keep the deployed R04.1 filename admission rule; versions are not hardcoded.
monthPattern = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{2}"
# In this regex, \x5f is the literal underscore character used in filenames.
bridgePattern = re.compile(
    r"[^\x5f]+\x5f.+?\x5fBridge\x5f"
    + monthPattern
    + r"\x5fEF-"
    + monthPattern
    + r"\x5fIMS-"
    + monthPattern
    + r"\x5f.+\.(?:xlsx|xlsm)",
    re.IGNORECASE,
)


def walkMetadata(
    root: DataLakeDirectoryClient, started: float, stats: dict[str, Any]
) -> Iterator[PathProperties]:
    """List each folder explicitly: this shortcut ignores recursive=True."""
    prefix = root.path_name.rstrip("/") + "/"
    pending = deque([""])
    queued = {""}
    while pending:
        if time.monotonic() - started > 70:
            raise RuntimeError(
                "Metadata folder walk exceeded 70 seconds; it is incomplete."
            )
        relative_folder = pending.popleft()
        logger.info("DEMAND_FOLDER path=%s", relative_folder or "/")
        current = (
            root.get_sub_directory_client(relative_folder) if relative_folder else root
        )
        current_prefix = current.path_name.rstrip("/") + "/"
        try:
            for item in current.get_paths(
                recursive=False, max_results=1000, timeout=20
            ):
                if time.monotonic() - started > 70:
                    raise RuntimeError(
                        "Metadata folder walk exceeded 70 seconds; it is incomplete."
                    )
                if not item.name.startswith(current_prefix):
                    raise ValueError(
                        "Unexpected path outside the listed directory: " + item.name
                    )
                if item.is_directory:
                    relative = item.name[len(prefix) :]
                    if not relative or any(
                        part in {"", ".", ".."} for part in relative.split("/")
                    ):
                        raise ValueError("Invalid child folder path: " + item.name)
                    identity = relative.casefold()
                    if identity in queued:
                        raise ValueError(
                            "Duplicate directory identity in metadata listing: "
                            + relative
                        )
                    queued.add(identity)
                    pending.append(relative)
                yield item
            if time.monotonic() - started > 70:
                raise RuntimeError(
                    "Metadata folder walk exceeded 70 seconds; it is incomplete."
                )
            stats["DirectoryPaths"].append(relative_folder or "/")
        finally:
            if current is not root:
                current.close()


def inspectMetadata(directory: DataLakeDirectoryClient) -> dict[str, Any]:
    """Complete a paged metadata listing; never download or change a workbook."""
    started = time.monotonic()
    prefix = directory.path_name.rstrip("/") + "/"
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[str] = set()
    entries = 0
    stats: dict[str, Any] = {"DirectoryPaths": []}
    for item in walkMetadata(directory, started, stats):
        entries += 1
        if item.is_directory:
            continue
        if not item.name.startswith(prefix):
            raise ValueError(
                "Unexpected path outside the selected Demand directory: " + item.name
            )
        relative = item.name[len(prefix) :]
        filename = relative.rsplit("/", 1)[-1]
        if filename.startswith("~$") or bridgePattern.fullmatch(filename) is None:
            continue
        identity = relative.casefold()
        if identity in seen:
            raise ValueError("Duplicate file identity in metadata listing: " + relative)
        seen.add(identity)
        modified = item.last_modified
        modified_utc: str | None = None
        if modified is not None:
            if isinstance(modified, datetime) and modified.utcoffset() is None:
                # The Azure SDK parses the service's GMT header into a naive
                # datetime; its parser explicitly defines that value as UTC.
                modified = modified.replace(tzinfo=UTC)
            elif isinstance(modified, str):
                try:
                    modified = parsedate_to_datetime(modified)
                except (TypeError, ValueError):
                    modified = datetime.fromisoformat(modified)
            if not isinstance(modified, datetime) or modified.utcoffset() is None:
                raise ValueError(
                    "Expected a timezone-aware modification time: " + relative
                )
            modified_utc = modified.astimezone(UTC).isoformat()
        etag = getattr(item, "etag", None)
        size = item.content_length
        if size is None or modified_utc is None or not etag:
            missing.append(relative)
        rows.append(
            {
                "Path": relative,
                "Bytes": size,
                "ModifiedAtUtc": modified_utc,
                "ETag": etag,
            }
        )
        logger.info("DEMAND_BRIDGE path=%s bytes=%s", relative, size)
    rows.sort(key=lambda row: row["Path"].casefold())
    status = "METADATA_VISIBLE" if rows and not missing else "METADATA_INCOMPLETE"
    return {
        "SchemaVersion": 1,
        "CodeVersion": "R04",
        "Check": "ForecastMaster metadata access prerequisite",
        "Status": status,
        "ListingMode": "EXPLICIT_FOLDER_WALK",
        "CompleteDirectoryListing": True,
        "DirectoriesListed": len(stats["DirectoryPaths"]),
        "DirectoryPaths": stats["DirectoryPaths"],
        "EntriesFound": entries,
        "MatchingBridgeFiles": len(rows),
        "MissingMetadataPaths": missing,
        "WorkbookContentsRead": False,
        "Files": rows,
        "Seconds": round(time.monotonic() - started, 3),
    }


# The published Fabric SDK decorators have no type annotations.
@udf.connection(argName="lakehouse", alias="ForecastMaster")  # type: ignore[untyped-decorator]
@udf.function()  # type: ignore[untyped-decorator]
def checkDemandAccessR04(lakehouse: fn.FabricLakehouseClient) -> str:
    """Check the existing Demand shortcut without starting Spark or a refresh."""
    files = lakehouse.connectToFiles()
    try:
        demand = files.get_sub_directory_client("Demand")
        try:
            result = inspectMetadata(demand)
        finally:
            demand.close()
    finally:
        files.close()
    return json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2)


def canonicalInventory(rows: Any) -> dict[str, dict[str, Any]]:
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
        if not isinstance(path, str) or path.startswith("/") or "\\" in path:
            raise ValueError("Invalid relative bridge path.")
        if any(part in {"", ".", ".."} for part in path.split("/")):
            raise ValueError("Invalid relative bridge path.")
        filename = path.rsplit("/", 1)[-1]
        if filename.startswith("~$") or bridgePattern.fullmatch(filename) is None:
            raise ValueError(
                "Inventory includes a file outside the bridge naming contract."
            )
        identity = path.casefold()
        if identity in result:
            raise ValueError("Duplicate bridge path in inventory: " + path)
        size = row["Bytes"]
        if type(size) is not int or size < 0:
            raise ValueError("Bridge size must be a nonnegative integer.")
        if not isinstance(row["ETag"], str) or not row["ETag"]:
            raise ValueError("Bridge ETag is missing.")
        modified = datetime.fromisoformat(row["ModifiedAtUtc"])
        if modified.utcoffset() is None:
            raise ValueError("Bridge metadata must include an explicit timezone.")
        result[identity] = {
            "Path": identity,
            "Bytes": size,
            "ModifiedAtUtc": modified.astimezone(UTC).isoformat(),
            "ETag": row["ETag"],
        }
    return result


def inventoryFingerprint(rows: Any) -> str:
    canonical = canonicalInventory(rows)
    payload = json.dumps(
        [canonical[key] for key in sorted(canonical)],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def prepareMetadataDecision(discovery: dict[str, Any], baseline: Any) -> dict[str, Any]:
    if (
        discovery.get("Status") != "METADATA_VISIBLE"
        or discovery.get("CompleteDirectoryListing") is not True
    ):
        raise ValueError(
            "Metadata discovery is incomplete; no refresh decision was made."
        )
    rows = discovery.get("Files")
    if not isinstance(rows, list):
        raise TypeError("Metadata discovery must include a bridge inventory list.")
    current = canonicalInventory(rows)
    if (
        discovery.get("MatchingBridgeFiles") != len(current)
        or discovery.get("MissingMetadataPaths") != []
    ):
        raise ValueError(
            "Bridge inventory does not reconcile with the discovery result."
        )
    fingerprint = inventoryFingerprint(rows)
    before: dict[str, dict[str, Any]] = {}
    if baseline is not None:
        if (
            not isinstance(baseline, dict)
            or baseline.get("SchemaVersion") != 1
            or baseline.get("SourceRoot") != "Files/Demand"
            or baseline.get("Status") != "SUCCESS"
            or not baseline.get("RefreshRunID")
        ):
            raise ValueError("The committed metadata baseline is invalid.")
        before = canonicalInventory(baseline.get("Files"))
        if baseline.get("Fingerprint") != inventoryFingerprint(baseline["Files"]):
            raise ValueError("The committed metadata baseline fingerprint is invalid.")
    original = {row["Path"].casefold(): row["Path"] for row in rows}
    changed = [
        original[key] for key in sorted(current) if before.get(key) != current[key]
    ]
    removed = sorted(set(before) - set(current))
    needed = baseline is None or bool(changed or removed)
    return {
        "SchemaVersion": 1,
        "CodeVersion": "R05",
        "Status": "BASELINE_REQUIRED"
        if baseline is None
        else ("CHANGED" if needed else "UNCHANGED"),
        "NeedsRefresh": needed,
        "CurrentFiles": len(current),
        "ChangedFiles": changed,
        "RemovedFiles": removed,
        "WorkbookContentsRead": False,
        "Snapshot": {
            "SchemaVersion": 1,
            "SourceRoot": "Files/Demand",
            "CapturedAtUtc": datetime.now(UTC).isoformat(),
            "Fingerprint": fingerprint,
            "Files": rows,
        },
        "DirectoriesListed": discovery.get("DirectoriesListed"),
        "Seconds": discovery.get("Seconds"),
    }


def readControlJson(files: DataLakeDirectoryClient, name: str) -> Any:
    control = files.get_file_client("ForecastMasterRefreshState/" + name)
    try:
        try:
            payload = control.download_file().readall()
        except ResourceNotFoundError:
            return None
        return json.loads(payload)
    finally:
        control.close()


def verifyNativeState(
    files: DataLakeDirectoryClient, leaseFactory: Any = DataLakeLeaseClient
) -> dict[str, Any]:
    existing = readControlJson(files, "latest.json")
    if not isinstance(existing, dict) or existing.get("SchemaVersion") != 1:
        raise ValueError("The existing native refresh receipt could not be verified.")
    identity = str(uuid4())
    relative = "ForecastMasterRefreshState/probe-" + identity + ".json"
    payload = json.dumps(
        {
            "SchemaVersion": 1,
            "Purpose": "Native refresh coordination capability check",
            "ProbeID": identity,
            "CreatedAtUtc": datetime.now(UTC).isoformat(),
        },
        sort_keys=True,
    ).encode("utf-8")
    probe = files.get_file_client(relative)
    held = False
    lease: Any = None
    try:
        # IfMissing supplies the wildcard condition itself. Passing an extra
        # etag leaves an unsupported keyword in this SDK's HTTP request options.
        probe.upload_data(
            payload, overwrite=True, match_condition=MatchConditions.IfMissing
        )
        if probe.download_file().readall() != payload:
            raise ValueError("The native test receipt did not read back identically.")
        lease = leaseFactory(probe)
        lease.acquire(lease_duration=60)
        held = True
        UUID(str(lease.id))
        contender = leaseFactory(probe)
        try:
            contender.acquire(lease_duration=60)
        except HttpResponseError as exc:
            code = getattr(exc, "error_code", None)
            code = getattr(code, "value", code)
            if exc.status_code != 409 or code != "LeaseAlreadyPresent":
                raise
        else:
            contender.release()
            raise ValueError("A competing writer unexpectedly acquired the same lease.")
        lease.renew()
    finally:
        try:
            if held:
                lease.release()
        finally:
            probe.close()
    return {
        "SchemaVersion": 1,
        "CodeVersion": "R05.2",
        "Status": "NATIVE_STATE_READY",
        "ExistingStateReadVerified": True,
        "ExistingLatestStatus": existing.get("Status"),
        "NativeWriteReadVerified": True,
        "ExclusiveLeaseVerified": True,
        "LeaseReleased": True,
        "ProbeFile": "Files/" + relative,
        "WorkbookContentsRead": False,
        "CurrentWorkerLockTouched": False,
    }


@udf.connection(argName="lakehouse", alias="ForecastMaster")  # type: ignore[untyped-decorator]
@udf.function()  # type: ignore[untyped-decorator]
def checkNativeStateR05(lakehouse: fn.FabricLakehouseClient) -> str:
    """Check one tiny native test receipt and a temporary exclusive lease."""
    files = lakehouse.connectToFiles()
    try:
        result = verifyNativeState(files)
    finally:
        files.close()
    return json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2)


@udf.connection(argName="lakehouse", alias="ForecastMaster")  # type: ignore[untyped-decorator]
@udf.function()  # type: ignore[untyped-decorator]
def checkDemandChangesR05(lakehouse: fn.FabricLakehouseClient) -> str:
    """Read metadata and compare with the worker's last successful baseline."""
    files = lakehouse.connectToFiles()
    try:
        demand = files.get_sub_directory_client("Demand")
        try:
            discovery = inspectMetadata(demand)
        finally:
            demand.close()
        baseline = readControlJson(files, "metadata-success.json")
        result = prepareMetadataDecision(discovery, baseline)
    finally:
        files.close()
    return json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2)
