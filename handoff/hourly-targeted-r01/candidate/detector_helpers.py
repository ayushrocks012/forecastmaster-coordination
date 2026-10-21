from __future__ import annotations
import hashlib
import json
from datetime import UTC, datetime
from typing import Any
import re
bridgePattern = re.compile('[^_]+_.+?_Bridge_(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \\d{2}_EF-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \\d{2}_IMS-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \\d{2}_.+\\.(?:xlsx|xlsm)', re.IGNORECASE)

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
        try:
            if (
                not isinstance(baseline, dict)
                or type(baseline.get("SchemaVersion")) is not int
                or baseline.get("SchemaVersion") != 1
                or baseline.get("SourceRoot") != "Files/Demand"
                or baseline.get("Status") != "SUCCESS"
                or not baseline.get("RefreshRunID")
            ):
                raise ValueError("The committed metadata baseline is invalid.")
            captured = datetime.fromisoformat(baseline["CapturedAtUtc"])
            if captured.utcoffset() is None:
                raise ValueError("Committed baseline timestamp needs a timezone.")
            before = canonicalInventory(baseline.get("Files"))
            if baseline.get("Fingerprint") != inventoryFingerprint(baseline["Files"]):
                raise ValueError("The committed metadata baseline fingerprint is invalid.")
        except (KeyError, TypeError, ValueError):
            baseline, before = None, {}
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
