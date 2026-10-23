"""Embedded read-only verification of the already-submitted R03 update.

Only three newly added calculated columns can admit isNameInferred=true.
Every other definition field, backup change and cloud mapping remains checked.
"""


def named(items, code):
    require(isinstance(items, list) and all(isinstance(item, dict) and isinstance(item.get("name"), str)
                                          for item in items), code)
    result = {item["name"]: item for item in items}
    require(len(result) == len(items), code)
    return result


def exact_expression_hash(value):
    return hashlib.sha256(expression_text(value).encode("utf-8")).hexdigest()


def verify_backup_pair(before, candidate):
    old_decoded, old_db = unpack(before)
    new_decoded, new_db = unpack(candidate)
    old_tables = named(old_db["model"]["tables"], "BACKUP_TABLE_INVENTORY_INVALID")
    new_tables = named(new_db["model"]["tables"], "BACKUP_TABLE_INVENTORY_INVALID")
    require(sum(n.startswith("fm_native_") for n in old_tables) == 24, "BACKUP_NATIVE_TABLE_COUNT_UNEXPECTED")
    require(set(old_tables) == set(new_tables), "BACKUP_TABLE_INVENTORY_CHANGED")
    old_measures = named(old_tables["fm_native_measures"]["measures"], "BACKUP_MEASURE_INVENTORY_INVALID")
    new_measures = named(new_tables["fm_native_measures"]["measures"], "BACKUP_MEASURE_INVENTORY_INVALID")
    require(set(old_measures) == set(INPUT_HASHES), "BACKUP_NOT_KNOWN_R176_INPUT")
    require(set(new_measures) == set(INPUT_HASHES) | set(FIT_OBJECT_HASHES), "BACKUP_NOT_KNOWN_R177_OUTPUT")
    restored = deepcopy(new_decoded)
    restore_db = next(p for p in restored["parts"] if p["path"] == "model.bim")["payload"]
    restore_tables = named(restore_db["model"]["tables"], "BACKUP_TABLE_INVENTORY_INVALID")
    restore_measures = named(restore_tables["fm_native_measures"]["measures"], "BACKUP_MEASURE_INVENTORY_INVALID")
    for name, fields in INPUT_HASHES.items():
        old = old_measures[name]
        require(known_expression_hash(old["expression"]) == fields["expression"], "BACKUP_UNKNOWN_INPUT_EXPRESSION")
        require(("formatStringDefinition" in old) == ("formatStringDefinition" in fields), "BACKUP_INPUT_FORMAT_INVENTORY_CHANGED")
        if "formatStringDefinition" in fields:
            require(known_expression_hash(old["formatStringDefinition"]["expression"]) == fields["formatStringDefinition"],
                    "BACKUP_UNKNOWN_INPUT_FORMAT")
        if name in EDIT_HASHES:
            require(exact_expression_hash(new_measures[name]["expression"]) == EDIT_HASHES[name],
                    "BACKUP_UNKNOWN_CANDIDATE_EXPRESSION")
            restore_measures[name]["expression"] = deepcopy(old["expression"])
    for name, expected in FIT_OBJECT_HASHES.items():
        require(digest(new_measures[name]) == expected, "BACKUP_UNKNOWN_FIT_MEASURE")
    restore_tables["fm_native_measures"]["measures"] = [m for m in restore_tables["fm_native_measures"]["measures"]
                                                        if m["name"] not in FIT_OBJECT_HASHES]
    for name, spec in HELPER_SPECS.items():
        old_table, new_table, restored_table = old_tables[name], new_tables[name], restore_tables[name]
        require(len(old_table.get("partitions", [])) == len(new_table.get("partitions", [])) == 1,
                "BACKUP_HELPER_PARTITIONS_CHANGED")
        old_source, new_source = old_table["partitions"][0]["source"], new_table["partitions"][0]["source"]
        require(old_source.get("type") == new_source.get("type") == "calculated", "BACKUP_HELPER_TYPE_CHANGED")
        require(known_expression_hash(old_source["expression"]) == spec["InputHash"], "BACKUP_UNKNOWN_INPUT_HELPER")
        require(exact_expression_hash(new_source["expression"]) == spec["OutputHash"], "BACKUP_UNKNOWN_OUTPUT_HELPER")
        restored_table["partitions"][0]["source"]["expression"] = deepcopy(old_source["expression"])
        old_columns = named(old_table["columns"], "BACKUP_COLUMN_INVENTORY_INVALID")
        new_columns = named(new_table["columns"], "BACKUP_COLUMN_INVENTORY_INVALID")
        additions = {column["name"]: column for column in spec["Columns"]}
        require(not set(old_columns) & set(additions), "BACKUP_NEW_COLUMN_ALREADY_PRESENT")
        require(set(new_columns) == set(old_columns) | set(additions), "BACKUP_COLUMN_INVENTORY_CHANGED")
        for column, expected in additions.items():
            require(digest(new_columns[column]) == digest(expected), "BACKUP_UNKNOWN_NEW_COLUMN")
        restored_table["columns"] = [column for column in restored_table["columns"] if column["name"] not in additions]
    require(digest(restored) == digest(old_decoded), "BACKUP_UNDECLARED_MODEL_OR_PART_CHANGE")
    return new_decoded, new_db


def verify_preflight(value):
    expected = {"Revision": "R03", "Checks": 72, "NumericComparisons": 72, "BlankComparisons": 0,
                "Mismatches": 0, "DirectOriginalScalarReads": 54, "DerivedOriginalVarianceComparisons": 18,
                "ActualCandidateScalarReads": 72, "OriginalVarianceFormulaVerified": True,
                "OriginalVariancePercentMeasureExecuted": False, "NumericBenchmarks": 18,
                "NumericFutureTrends": 9, "ScalarQueries": 126, "MetadataQueries": 3,
                "SourceSelectionMetadataStable": True, "CompanyAmountValuesPrintedOrStored": False,
                "ValidationMethod": "54_DIRECT_BASELINE_AND_18_VERIFIED_FORMULA_EXPECTATIONS_VS_72_ACTUAL_CANDIDATES",
                "ComparisonCountsByMetric": {m: {"Numeric": 24, "Blank": 0} for m in ("market", "ef", "share")}}
    require(isinstance(value, dict), "PREFLIGHT_RECEIPT_INVALID")
    require(all(key in value and digest(value[key]) == digest(want) for key, want in expected.items()),
            "PREFLIGHT_RECEIPT_NOT_EXPECTED_SUCCESS")
    return {key: value[key] for key in ("Revision", "Checks", "NumericComparisons", "BlankComparisons", "Mismatches",
                                       "DirectOriginalScalarReads", "DerivedOriginalVarianceComparisons", "ActualCandidateScalarReads")}


def inferred_name_normalization(expected, observed):
    right = deepcopy(observed)
    expected_db = next(p for p in expected["parts"] if p["path"] == "model.bim")["payload"]
    right_db = next(p for p in right["parts"] if p["path"] == "model.bim")["payload"]
    left_tables = named(expected_db["model"]["tables"], "CANDIDATE_TABLE_INVENTORY_INVALID")
    right_tables = named(right_db["model"]["tables"], "CURRENT_TABLE_INVENTORY_INVALID")
    details = []
    for table, spec in HELPER_SPECS.items():
        left_columns = named(left_tables[table]["columns"], "CANDIDATE_COLUMN_INVENTORY_INVALID")
        right_columns = named(right_tables.get(table, {}).get("columns", []), "CURRENT_COLUMN_INVENTORY_INVALID")
        for col in spec["Columns"]:
            name = col["name"]
            a, b = left_columns[name], right_columns.get(name, {})
            if "isNameInferred" not in b:
                continue
            value = b["isNameInferred"]
            accepted = ("isNameInferred" not in a and type(value) is bool and value is True
                        and a.get("type") == b.get("type") == "calculatedTableColumn"
                        and a.get("sourceColumn") == b.get("sourceColumn") == "[" + name + "]")
            details.append({"Table": table, "Column": name, "Property": "isNameInferred",
                            "ObservedBoolean": value if type(value) is bool else "NONBOOLEAN_VALUE_WITHHELD",
                            "Accepted": accepted})
            if accepted:
                del b["isNameInferred"]
    return right, details


def run(client, fs):
    reader = MetadataReader(client)
    response = reader.get(ITEM)
    require(response.status_code == 200, "TEST_IDENTITY_UNAVAILABLE")
    identity = response.json()
    require(identity.get("id") == TEST_MODEL and identity.get("displayName") == TEST_NAME
            and identity.get("type") == "SemanticModel", "TEST_IDENTITY_MISMATCH")
    print("Read-only: exact R03 private backup, preflight receipt and two TEST metadata snapshots. No amount query, update or refresh.", flush=True)
    backups = read_backups(fs)
    expected, expected_db = verify_backup_pair(backups["definition-before.json"], backups["definition-candidate.json"])
    numeric = verify_preflight(backups["numerical-check-summary.json"])
    saved_connections = backups["connections-before.json"]
    require(isinstance(saved_connections, list) and any(c.get("connectivityType") == "ShareableCloud" for c in saved_connections),
            "BACKUP_EXPLICIT_CLOUD_MAPPING_MISSING")
    first, first_mapping = definition(reader), connections(reader)
    second, second_mapping = definition(reader), connections(reader)
    observed, _ = unpack(second)
    raw_diff = compare_with_calculated(expected, observed)
    normalized, additions = inferred_name_normalization(expected, observed)
    diff = compare_with_calculated(expected, normalized)
    stable = digest(unpack(first)[0]) == digest(observed) and digest(first_mapping) == digest(second_mapping)
    mapping_ok = digest(sorted(saved_connections, key=digest)) == digest(second_mapping)
    flags_ok = all(detail["Accepted"] for detail in additions)
    verified = stable and mapping_ok and flags_ok and diff["Unexplained"] == 0
    result = {"Stage": "TEST_R177_READBACK_VERIFIED" if verified else "TEST_R177_READBACK_NEEDS_REVIEW",
              "CheckVersion": "R01", "UpdaterRevision": "R03", "TestModelID": TEST_MODEL,
              "ExactPrivateBackupRead": True, "BackupPairVerifiedAgainstFrozenR177": True,
              "NumericalPreflightReceiptVerified": True, "NumericalPreflight": numeric,
              "TwoMetadataSnapshotsStable": stable, "CloudConnectionMatchesBackup": mapping_ok,
              "WholeDefinitionMatchesWithOnlyDocumentedNormalizations": diff["Unexplained"] == 0,
              "InferredNameMetadata": additions,
              "RawUnexplainedDifferenceCount": raw_diff["Unexplained"], "DifferenceSummaryAfterStrictCheck": diff,
              "ModelWriteRequested": False, "OriginalModelWriteRequested": False,
              "CompanyAmountsQueried": False, "RefreshRequested": False, "ReportPublished": False,
              "NextStep": ("Refresh ONLY existing R17.1 TEST once; require warning-free Completed, then open unchanged R17.7 TEST PBIP. Send this JSON and refresh result."
                           if verified else "Send this JSON; keep backup. Do not rerun updater, refresh, open R17.7 or publish.")}
    print(json.dumps(result, indent=2), flush=True)
    return result


def safe_run(client, fs):
    try:
        return run(client, fs)
    except Exception as exc:
        result = {"Stage": "TEST_R177_READBACK_CHECK_STOPPED", "CheckVersion": "R01",
                  "ReasonCode": str(exc) if isinstance(exc, CheckStopped) else "METADATA_OR_BACKUP_READ_FAILED",
                  "ModelWriteRequested": False, "CompanyAmountsQueried": False,
                  "RefreshRequested": False, "ReportPublished": False,
                  "NextStep": "Send this JSON. Do not retry the updater, refresh or publish; preserve the private backup."}
        print(json.dumps(result, indent=2), flush=True)
        return result
