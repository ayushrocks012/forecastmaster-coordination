"""R03: direct baseline inputs plus a definition-checked variance expectation.

Embedded by build_cell.py. The cancelled baseline Variance % query is never
reported as executed or passed. All candidate results are queried directly.
"""
import math
import time

VARIANCE_CONTRACT = {
    "N Variance": "VAR _p=[N Plan] VAR _t=[N Benchmark] RETURN IF(NOT ISBLANK(_p)&&NOT ISBLANK(_t),_p-_t)",
    "N Variance %": "DIVIDE([N Variance],ABS([N Benchmark]))",
}


def verify_variance_contract(database):
    tables = [t for t in database.get("model", {}).get("tables", []) if t.get("name") == "fm_native_measures"]
    if len(tables) != 1:
        raise PreflightStopped({"Reason": "BASELINE_VARIANCE_CONTRACT_UNAVAILABLE"})
    measures = tables[0].get("measures", [])
    for name, expected in VARIANCE_CONTRACT.items():
        matches = [m for m in measures if m.get("name") == name]
        if len(matches) != 1 or expression_hash(matches[0].get("expression", "")) != expression_hash(expected):
            raise PreflightStopped({"Reason": "BASELINE_VARIANCE_CONTRACT_CHANGED"})


def expected_variance_percent(plan, benchmark, checkpoint):
    # Exact verified chain: guarded N Variance numerator / ABS(N Benchmark).
    # DIVIDE with no alternate returns blank for zero denominator. Blanks are
    # kept separate from numeric zero; a negative benchmark still uses ABS.
    if plan is None or benchmark is None or benchmark == 0:
        return None
    value = (plan - benchmark) / abs(benchmark)
    if not math.isfinite(value):
        raise PreflightStopped({"Reason": "NONFINITE_VARIANCE_EXPECTATION", "Checkpoint": checkpoint})
    return value


def verify_numeric(evaluate, workspace, dataset, overrides, database):
    verify_variance_contract(database)
    elapsed = {"Original": 0, "Candidate": 0}
    query_counts = {"Original": 0, "Candidate": 0, "Metadata": 0}
    completed, derived = 0, 0

    def query(dax, kind, checkpoint):
        query_counts[kind] += 1
        start = time.monotonic()
        try:
            rows = records(evaluate(dataset=dataset, dax_string=dax, workspace=workspace,
                                    verbose=0, use_readwrite_connection=False))
        except Exception as exc:
            raise PreflightStopped({"Reason": "READ_ONLY_QUERY_FAILED", "Checkpoint": checkpoint,
                                    "CompletedComparisons": completed, "QueryKind": kind,
                                    "ElapsedMs": round((time.monotonic() - start) * 1000),
                                    "Error": safe_error(exc)}) from None
        if kind in elapsed:
            elapsed[kind] += round((time.monotonic() - start) * 1000)
        return rows

    scopes = query(METADATA_QUERY, "Metadata", {"Step": "AvailableScopeMetadata"})
    if not valid_scope(scopes):
        raise PreflightStopped({"Reason": "NO_UNIQUE_AVAILABLE_ADS_SCOPE"})
    scope = scopes[0]
    year = int(scope["Cycle"][:4])
    selection_query = source_metadata_query(scope)
    selection_before = source_metadata_digest(query(selection_query, "Metadata", {"Step": "SourceMetadataBefore"}))
    numeric, benchmark_numeric, future_trend_numeric = 0, 0, 0
    by_metric = {metric: {"Numeric": 0, "Blank": 0} for metric in ("market", "ef", "share")}
    print("R17.7 R03: 72 comparisons; 54 direct baseline reads, 18 definition-checked variance expectations, 72 actual candidate reads.", flush=True)
    print("The cancelled baseline Variance % query is not rerun or marked passed. Company amounts stay private.", flush=True)
    for metric in ("market", "ef", "share"):
        for window in (6, 12, 24):
            for year_offset in (0, 1):
                original_inputs = {}
                print("Comparisons " + str(completed + 1) + "-" + str(completed + 4)
                      + "/72: " + metric + ", " + str(window) + "M, year offset " + str(year_offset) + ".", flush=True)
                for field, _ in MEMBERS:
                    checkpoint = {"CheckIndex": completed + 1, "Metric": metric, "Window": window,
                                  "YearOffset": year_offset, "Field": field,
                                  "BaselineEvidence": "VERIFIED_FORMULA_FROM_P_B" if field == "V" else "DIRECT_QUERY"}
                    if field == "V":
                        if set(original_inputs) != {"P", "B"}:
                            raise PreflightStopped({"Reason": "MISSING_BASELINE_VARIANCE_INPUTS", "Checkpoint": checkpoint})
                        left = expected_variance_percent(original_inputs["P"], original_inputs["B"], checkpoint)
                        derived += 1
                    else:
                        left = scalar_value(query(build_scalar(scope, {}, metric, window, year + year_offset, field),
                                                  "Original", checkpoint), checkpoint)
                        if field in {"P", "B"}:
                            original_inputs[field] = left
                    right = scalar_value(query(build_scalar(scope, overrides, metric, window, year + year_offset, field),
                                               "Candidate", checkpoint), checkpoint)
                    if left is None or right is None:
                        same = left is None and right is None
                    else:
                        same = math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-6)
                    if not same:
                        raise PreflightStopped({"Reason": "NUMERICAL_MISMATCH", "Checkpoint": checkpoint,
                                                "CompletedComparisons": completed,
                                                "CompanyAmountValuesPrintedOrStored": False})
                    completed += 1
                    if left is None:
                        by_metric[metric]["Blank"] += 1
                    else:
                        numeric += 1
                        by_metric[metric]["Numeric"] += 1
                        if field == "B":
                            benchmark_numeric += 1
                        if field == "T" and year_offset == 1:
                            future_trend_numeric += 1
    if (completed != 72 or derived != 18 or query_counts["Original"] != 54
            or query_counts["Candidate"] != 72 or numeric == 0 or benchmark_numeric == 0 or future_trend_numeric == 0):
        raise PreflightStopped({"Reason": "INCOMPLETE_OR_UNINFORMATIVE_PREFLIGHT", "CompletedComparisons": completed})
    selection_after = source_metadata_digest(query(selection_query, "Metadata", {"Step": "SourceMetadataAfter"}))
    if selection_after != selection_before:
        raise PreflightStopped({"Reason": "SOURCE_SELECTION_METADATA_CHANGED", "CompletedComparisons": completed})
    result = {"Revision": "R03", "Checks": completed, "NumericComparisons": numeric,
              "BlankComparisons": completed - numeric, "Mismatches": 0,
              "ValidationMethod": "54_DIRECT_BASELINE_AND_18_VERIFIED_FORMULA_EXPECTATIONS_VS_72_ACTUAL_CANDIDATES",
              "DirectOriginalScalarReads": query_counts["Original"], "DerivedOriginalVarianceComparisons": derived,
              "ActualCandidateScalarReads": query_counts["Candidate"], "OriginalVarianceFormulaVerified": True,
              "OriginalVariancePercentMeasureExecuted": False,
              "NumericBenchmarks": benchmark_numeric, "NumericFutureTrends": future_trend_numeric,
              "ComparisonCountsByMetric": by_metric, "MaximumValuesPerQuery": 1,
              "ScalarQueries": query_counts["Original"] + query_counts["Candidate"],
              "MetadataQueries": query_counts["Metadata"], "OriginalQueryMs": elapsed["Original"],
              "CandidateQueryMs": elapsed["Candidate"], "SourceSelectionMetadataStable": True,
              "TimingCaveat": "Mixed direct/derived baseline evidence; serial representative checks; cache order differs; not report speed acceptance",
              "CompanyAmountValuesPrintedOrStored": False}
    print("Preflight passed: 54 direct baseline and 18 verified-formula comparisons against 72 actual candidate results. No amounts printed.", flush=True)
    return result
