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
