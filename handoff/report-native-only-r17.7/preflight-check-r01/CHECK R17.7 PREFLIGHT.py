"""ONE NEW Python cell in ForecastMaster_GM_Setup; run only this cell.
Read existing TEST only. No candidate overrides, model writes or refreshes.
Print fixed diagnostic labels and counts, never company values or raw errors.
This is a diagnostic, not authorization to install or refresh R17.7.
"""
import json
import math
from numbers import Number
import re
import sys
import time

WORKSPACE = "f5cb5742-9a7c-4337-a4c0-952706dddf0b"
TEST_MODEL = "31d00232-ac03-48fe-af39-f2e4bae82443"

METADATA_QUERY = '''EVALUATE SELECTCOLUMNS(TOPN(1,
 FILTER(ALL('fm_native_files'),'fm_native_files'[ADSPriority]>0
 &&'fm_native_files'[PreferenceRank]=1&&'fm_native_files'[PreferenceTies]=1),
 'fm_native_files'[DemandCycle],DESC,'fm_native_files'[SourceRevisionID],ASC),
 "Country",'fm_native_files'[Country],"Cycle",'fm_native_files'[DemandCycle],
 "Driver",'fm_native_files'[GrowthDriver])'''

PROBES = (
    ("Plan", "N Plan", False),
    ("Benchmark", "N Benchmark", False),
    ("VariancePercent", "N Variance %", False),
    ("FutureTrend", "N Trend Monthly", True),
)


def safe_error(exc):
    """Inspect text privately; return only allowlisted codes/categories/numbers.

    Fabric/.NET wrappers may put the useful error in Message, InnerException
    or Errors. Unknown messages are suppressed, not redacted by a denylist.
    """
    texts, pending, visited = [], [exc], set()
    while pending and len(visited) < 24:
        item = pending.pop(0)
        if id(item) in visited:
            continue
        visited.add(id(item))
        try:
            texts.append(str(item)[:100000])
        except Exception:
            pass
        for name in ("Message", "Description", "message"):
            try:
                value = getattr(item, name, None)
                if isinstance(value, str):
                    texts.append(value[:100000])
            except Exception:
                pass
        for name in ("__cause__", "__context__", "InnerException", "inner_exception"):
            try:
                value = getattr(item, name, None)
                if value is not None:
                    pending.append(value)
            except Exception:
                pass
        try:
            for index, value in enumerate(getattr(item, "Errors", ())):
                if index >= 8:
                    break
                pending.append(value)
        except Exception:
            pass
    raw = "\n".join(texts)
    lower = raw.lower()
    signals = []
    patterns = (
        ("MEMORY_LIMIT", ("rsquerymemorylimitexceeded", "query memory limit", "consumed memory",
                          "out of memory", "not enough memory", "wasn't enough memory",
                          "memory-intensive", "memory limit exceeded")),
        ("TIMEOUT", ("rsquerytimeoutexceeded", "timeout", "timed out", "time limit exceeded")),
        ("QUERY_SYNTAX_OR_DEFINITION", ("syntax for", "syntax is incorrect", "failed to resolve name",
                                        "couldnotresolvesemanticquerydefinition", "cannot find table",
                                        "cannot find column", "cannot find measure", "not a valid table",
                                        "not a valid column", "not a valid function", "could not be resolved")),
        ("PROCESSING_REQUIRED", ("not been processed", "needs to be processed", "unprocessed")),
        ("ACCESS_OR_AUTHENTICATION", ("unauthorized", "not authorized", "access is denied",
                                      "access denied", "forbidden", "authentication failed",
                                      "permission denied", "insufficient permission")),
        ("CAPACITY_OR_THROTTLING", ("throttl", "capacity is paused", "capacity is overloaded",
                                    "too many requests")),
        ("CANCELLED", ("canceled", "cancelled")),
    )
    for label, phrases in patterns:
        if any(phrase in lower for phrase in phrases):
            signals.append(label)
    # Positions are useful for parser errors; no echoed DAX/source text is emitted.
    positions = re.findall(r"\bquery\s*\(\s*(\d{1,6})\s*,\s*(\d{1,6})\s*\)", raw, re.I)
    if positions and "QUERY_SYNTAX_OR_DEFINITION" not in signals:
        signals.append("QUERY_POSITION_REPORTED")
    codes = [code for code in ("rsQueryMemoryLimitExceeded", "rsQueryTimeoutExceeded",
                               "CouldNotResolveSemanticQueryDefinition") if code.lower() in lower]
    detail = {"ExceptionFamily": (type(exc).__name__ if type(exc).__name__ in {
                  "FabricAdomdException", "AdomdErrorResponseException", "AdomdConnectionException",
                  "TimeoutError", "ConnectionError", "RuntimeError", "ValueError"} else "OtherException"),
              "ErrorCategory": signals[0] if signals else "UNCLASSIFIED",
              "KnownSignals": signals, "KnownCodes": codes,
              "RawExceptionPrintedOrStored": False}
    if positions:
        detail["QueryPositions"] = [{"Line": int(a), "Column": int(b)} for a, b in positions[:4]]
    if "MEMORY_LIMIT" in signals:
        for field, label in (("ConsumedMemory", "consumed memory"), ("MemoryLimit", "memory limit")):
            match = re.search(label + r"\s*[:=]?\s*(\d{1,9})\s*(MB|KB|GB)\b", raw, re.I)
            if match:
                detail[field] = {"Value": int(match.group(1)), "Unit": match.group(2).upper()}
    return detail


def records(frame):
    return [{key.rsplit("[", 1)[-1].rstrip("]"): value for key, value in row.items()}
            for row in frame.to_dict("records")]


def previous_preflight_error():
    """Python retains __context__ even when 'raise ... from None' hides it.

    IPython may retain that exception in sys.last_value/last_exc. If it does,
    classify the original error without issuing the costly query again.
    Ignore unrelated notebook exceptions; never display their messages.
    """
    prefix = "Read-only numerical preflight unavailable; no model write. Error type: FabricAdomdException"
    for name in ("last_exc", "last_value"):
        exc = getattr(sys, name, None)
        if not isinstance(exc, RuntimeError):
            continue
        try:
            matches = str(exc) == prefix
        except Exception:
            matches = False
        if matches:
            return {"Available": True, "Error": safe_error(exc)}
    return {"Available": False}


def valid_scope(rows):
    if len(rows) != 1 or set(rows[0]) != {"Country", "Cycle", "Driver"}:
        return False
    row = rows[0]
    if any(not isinstance(row[key], str) or not row[key].strip() for key in row):
        return False
    return (re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", row["Cycle"]) is not None
            and 1 <= int(row["Cycle"][:4]) <= 9998)


def scalar_query(scope, measure, future):
    if measure not in {item[1] for item in PROBES}:
        raise ValueError("Unknown diagnostic measure.")
    year = int(scope["Cycle"][:4]) + int(future)

    def text_filter(table, column, value):
        literal = '"' + value.replace('"', '""') + '"'
        return "TREATAS({" + literal + "},'" + table + "'[" + column + "])"

    filters = [text_filter("fm_review_files", "Country", scope["Country"]),
               text_filter("fm_review_files", "DemandCycle", scope["Cycle"]),
               text_filter("fm_native_scope", "GrowthDriver", scope["Driver"]),
               text_filter("fm_native_file_mode", "Mode", "Automatic ADS"),
               text_filter("fm_native_scenario", "Mode", "Automatic ADS"),
               text_filter("fm_native_currency", "Currency", "Local"),
               text_filter("fm_native_display", "Display", "Units"),
               text_filter("fm_native_metric", "RowID", "market"),
               "TREATAS({12},'fm_native_trend'[Window])",
               text_filter("fm_native_periods", "PeriodKey", str(year) + ":FY")]
    if future:
        filters.append("TREATAS({DATE(" + str(year) + ",12,1)},'fm_review_axis'[Month])")
    return 'EVALUATE ROW("Value",CALCULATE([' + measure + '],' + ','.join(filters) + '))'


def value_state(rows):
    if len(rows) != 1 or set(rows[0]) != {"Value"}:
        return "UNEXPECTED_RESULT_SHAPE"
    value = rows[0]["Value"]
    if value is None:
        return "BLANK"
    if isinstance(value, bool) or not isinstance(value, Number):
        return "UNEXPECTED_VALUE_TYPE"
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return "UNEXPECTED_VALUE_TYPE"
    if math.isnan(number):
        return "BLANK"
    return "NUMERIC" if math.isfinite(number) else "NONFINITE_VALUE"


def run(evaluate):
    result = {"Stage": "R177_PREFLIGHT_DIAGNOSTIC_STARTED", "ProbeVersion": "R01",
              "TestModelID": TEST_MODEL, "Checks": [], "CandidateOverridesEvaluated": False,
              "NumericalParityVerified": False, "CompanyAmountValuesPrintedOrStored": False,
              "ModelWriteRequested": False, "RefreshRequested": False, "ReportPublished": False}
    result["PreviousPreflightError"] = previous_preflight_error()

    def finish(stage):
        result["Stage"] = stage
        result["NextStep"] = "Send this JSON back. Keep R17.6; do not rerun the updater or refresh TEST yet."
        print(json.dumps(result, indent=2), flush=True)
        return result

    def read(label, dax):
        print("Read-only existing TEST: " + label + " (no values printed).", flush=True)
        start = time.monotonic()
        check = {"Check": label}
        result["Checks"].append(check)
        try:
            rows = records(evaluate(dataset=TEST_MODEL, dax_string=dax, workspace=WORKSPACE,
                                    verbose=0, use_readwrite_connection=False))
        except Exception as exc:
            check.update({"Status": "QUERY_FAILED", "ElapsedMs": round((time.monotonic()-start)*1000),
                          "Error": safe_error(exc)})
            return None
        check.update({"Status": "READ_COMPLETED", "ElapsedMs": round((time.monotonic()-start)*1000)})
        return rows

    previous = result["PreviousPreflightError"]
    if previous["Available"] and previous["Error"]["ErrorCategory"] != "UNCLASSIFIED":
        return finish("R177_PREFLIGHT_PREVIOUS_ERROR_CAPTURED")
    rows = read("AvailableScopeMetadata", METADATA_QUERY)
    if rows is None:
        return finish("R177_PREFLIGHT_DIAGNOSTIC_QUERY_FAILED")
    if not valid_scope(rows):
        return finish("R177_PREFLIGHT_DIAGNOSTIC_SCOPE_UNAVAILABLE")
    scope = rows[0]
    for label, measure, future in PROBES:
        values = read(label, scalar_query(scope, measure, future))
        if values is None:
            return finish("R177_PREFLIGHT_DIAGNOSTIC_QUERY_FAILED")
        state = value_state(values)
        result["Checks"][-1]["ValueState"] = state
        if state not in {"NUMERIC", "BLANK"}:
            return finish("R177_PREFLIGHT_DIAGNOSTIC_UNEXPECTED_RESULT")
    result["Interpretation"] = ("Four small baseline reads completed. This does not identify why the original "
                                "72-value query failed, validate candidate formulas or authorize an update.")
    return finish("R177_SMALL_BASELINE_READS_COMPLETED")


def main():
    try:
        import sempy.fabric as fabric
    except Exception as exc:
        print(json.dumps({"Stage": "R177_PREFLIGHT_DIAGNOSTIC_STARTUP_FAILED", "Error": safe_error(exc),
                          "ModelWriteRequested": False, "RefreshRequested": False,
                          "NextStep": "Send this JSON back; do not install packages or rerun old setup cells."}, indent=2),
              flush=True)
        return
    run(fabric.evaluate_dax)


if __name__ == "__main__":
    main()
