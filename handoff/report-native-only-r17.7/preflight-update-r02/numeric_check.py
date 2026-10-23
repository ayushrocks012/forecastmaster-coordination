"""Compare the same 72 old/candidate scalars in separate read-only queries."""
import hashlib
import json
import math
from numbers import Number
import time

MEMBERS = (("P", "N Plan"), ("B", "N Benchmark"),
           ("V", "N Variance %"), ("T", "N Trend Monthly"))


class PreflightStopped(RuntimeError):
    def __init__(self, detail):
        super().__init__("R17.7 numerical preflight stopped before any model write.")
        self.detail = detail


def text_filter(table, column, value):
    literal = '"' + value.replace('"', '""') + '"'
    return "TREATAS({" + literal + "},'" + table + "'[" + column + "])"


def build_scalar(scope, overrides, metric, window, year, field):
    if metric not in ("market", "ef", "share") or window not in (6, 12, 24) or field not in dict(MEMBERS):
        raise ValueError("Unknown preflight case; no write.")
    definitions = ""
    if overrides:
        definitions = "DEFINE\n" + "\n".join("MEASURE 'fm_native_measures'[" + name + "] =\n" + expression
                          for name, expression in overrides.items()) + "\n"
    filters = [text_filter("fm_review_files", "Country", scope["Country"]),
               text_filter("fm_review_files", "DemandCycle", scope["Cycle"]),
               text_filter("fm_native_scope", "GrowthDriver", scope["Driver"]),
               text_filter("fm_native_file_mode", "Mode", "Automatic ADS"),
               text_filter("fm_native_scenario", "Mode", "Automatic ADS"),
               text_filter("fm_native_currency", "Currency", "Local"),
               text_filter("fm_native_display", "Display", "Units"),
               text_filter("fm_native_metric", "RowID", metric),
               "TREATAS({" + str(window) + "},'fm_native_trend'[Window])",
               text_filter("fm_native_periods", "PeriodKey", str(year) + ":FY")]
    if field == "T":
        filters.append("TREATAS({DATE(" + str(year) + ",12,1)},'fm_review_axis'[Month])")
    return definitions + 'EVALUATE ROW("Value",CALCULATE([' + dict(MEMBERS)[field] + '],' + ",".join(filters) + '))'


def source_metadata_query(scope):
    filters = [text_filter("fm_native_files", column, scope[key])
               for column, key in (("Country", "Country"), ("DemandCycle", "Cycle"), ("GrowthDriver", "Driver"))]
    return '''EVALUATE CALCULATETABLE(SELECTCOLUMNS('fm_native_files',
 "Revision",'fm_native_files'[SourceRevisionID],"Priority",'fm_native_files'[ADSPriority],
 "Rank",'fm_native_files'[PreferenceRank],"Ties",'fm_native_files'[PreferenceTies]),''' + ",".join(filters) + ")"


def source_metadata_digest(rows):
    if not rows or any(set(row) != {"Revision", "Priority", "Rank", "Ties"}
                       or not isinstance(row["Revision"], str) or not row["Revision"] for row in rows):
        raise PreflightStopped({"Reason": "SOURCE_SELECTION_METADATA_UNAVAILABLE"})
    try:
        parts = sorted(json.dumps(row, sort_keys=True, allow_nan=False) for row in rows)
    except (ValueError, TypeError):
        raise PreflightStopped({"Reason": "SOURCE_SELECTION_METADATA_INVALID"}) from None
    return hashlib.sha256(json.dumps(parts).encode("utf-8")).hexdigest()


def scalar_value(rows, checkpoint):
    if len(rows) != 1 or set(rows[0]) != {"Value"}:
        raise PreflightStopped({"Reason": "INCOMPLETE_SCALAR_RESULT", "Checkpoint": checkpoint})
    value = rows[0]["Value"]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Number):
        raise PreflightStopped({"Reason": "NONNUMERIC_SCALAR_RESULT", "Checkpoint": checkpoint})
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        raise PreflightStopped({"Reason": "NONNUMERIC_SCALAR_RESULT", "Checkpoint": checkpoint}) from None
    if math.isnan(number):
        return None
    if not math.isfinite(number):
        raise PreflightStopped({"Reason": "NONFINITE_SCALAR_RESULT", "Checkpoint": checkpoint})
    return number


def verify_numeric(evaluate, workspace, dataset, overrides):
    elapsed = {"Original": 0, "Candidate": 0}
    query_counts = {"Original": 0, "Candidate": 0, "Metadata": 0}

    def query(dax, kind, checkpoint):
        query_counts[kind] += 1
        start = time.monotonic()
        try:
            rows = records(evaluate(dataset=dataset, dax_string=dax, workspace=workspace,
                                    verbose=0, use_readwrite_connection=False))
        except Exception as exc:
            raise PreflightStopped({"Reason": "READ_ONLY_QUERY_FAILED", "Checkpoint": checkpoint,
                                    "CompletedComparisons": completed, "QueryKind": kind,
                                    "Error": safe_error(exc)}) from None
        if kind in elapsed:
            elapsed[kind] += round((time.monotonic() - start) * 1000)
        return rows

    completed = 0
    scopes = query(METADATA_QUERY, "Metadata", {"Step": "AvailableScopeMetadata"})
    if not valid_scope(scopes):
        raise PreflightStopped({"Reason": "NO_UNIQUE_AVAILABLE_ADS_SCOPE"})
    scope = scopes[0]
    year = int(scope["Cycle"][:4])
    selection_query = source_metadata_query(scope)
    selection_before = source_metadata_digest(query(selection_query, "Metadata", {"Step": "SourceMetadataBefore"}))
    numeric, benchmark_numeric, future_trend_numeric = 0, 0, 0
    by_metric = {metric: {"Numeric": 0, "Blank": 0} for metric in ("market", "ef", "share")}
    print("R17.7 R02: 72 paired comparisons; one scalar per query, sequential reads, no values printed.", flush=True)
    for metric in ("market", "ef", "share"):
        for window in (6, 12, 24):
            for year_offset in (0, 1):
                print("Read-only comparisons " + str(completed + 1) + "-" + str(completed + 4)
                      + "/72: " + metric + ", " + str(window) + "M, year offset " + str(year_offset) + ".", flush=True)
                for field, _ in MEMBERS:
                    checkpoint = {"CheckIndex": completed + 1, "Metric": metric, "Window": window,
                                  "YearOffset": year_offset, "Field": field}
                    left = scalar_value(query(build_scalar(scope, {}, metric, window, year + year_offset, field),
                                              "Original", checkpoint), checkpoint)
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
    if completed != 72 or numeric == 0 or benchmark_numeric == 0 or future_trend_numeric == 0:
        raise PreflightStopped({"Reason": "INCOMPLETE_OR_UNINFORMATIVE_PREFLIGHT", "CompletedComparisons": completed})
    selection_after = source_metadata_digest(query(selection_query, "Metadata", {"Step": "SourceMetadataAfter"}))
    if selection_after != selection_before:
        raise PreflightStopped({"Reason": "SOURCE_SELECTION_METADATA_CHANGED", "CompletedComparisons": completed})
    result = {"Revision": "R02", "Checks": completed, "NumericComparisons": numeric,
              "BlankComparisons": completed - numeric, "Mismatches": 0,
              "NumericBenchmarks": benchmark_numeric, "NumericFutureTrends": future_trend_numeric,
              "ComparisonCountsByMetric": by_metric, "MaximumValuesPerQuery": 1,
              "ScalarQueries": query_counts["Original"] + query_counts["Candidate"],
              "MetadataQueries": query_counts["Metadata"], "OriginalQueryMs": elapsed["Original"],
              "CandidateQueryMs": elapsed["Candidate"], "SourceSelectionMetadataStable": True,
              "TimingCaveat": "Serial representative checks; original precedes each candidate; cache order differs; not report speed acceptance",
              "CompanyAmountValuesPrintedOrStored": False}
    print("Numerical preflight passed: 72 paired checks; no amounts printed.", flush=True)
    return result
