"""Read-only before-write company parity check. Never print/store amount values."""
import json
import math
import time

METADATA_QUERY = '''EVALUATE SELECTCOLUMNS(TOPN(1,
 FILTER(ALL('fm_native_files'),'fm_native_files'[ADSPriority]>0
 &&'fm_native_files'[PreferenceRank]=1&&'fm_native_files'[PreferenceTies]=1),
 'fm_native_files'[DemandCycle],DESC,'fm_native_files'[SourceRevisionID],ASC),
 "Country",'fm_native_files'[Country],"Cycle",'fm_native_files'[DemandCycle],
 "Driver",'fm_native_files'[GrowthDriver])'''


def build_query(scope, overrides):
    definitions = ""
    if overrides:
        definitions = "DEFINE\n" + "\n".join("MEASURE 'fm_native_measures'[" + name + "] =\n" + expression
            for name, expression in overrides.items()) + "\n"
    year = int(str(scope["Cycle"])[:4])
    def values(table, column, value):
        literal = '"' + str(value).replace('"', '""') + '"'
        return "TREATAS({" + literal + "},'" + table + "'[" + column + "])"
    shared = [values("fm_review_files", "Country", scope["Country"]),
              values("fm_review_files", "DemandCycle", scope["Cycle"]),
              values("fm_native_scope", "GrowthDriver", scope["Driver"]),
              values("fm_native_file_mode", "Mode", "Automatic ADS"),
              values("fm_native_scenario", "Mode", "Automatic ADS"),
              values("fm_native_currency", "Currency", "Local"),
              values("fm_native_display", "Display", "Units")]
    rows = []
    for metric in ("market", "ef", "share"):
        for window in (6, 12, 24):
            for y in (year, year+1):
                key = metric + "/" + str(window) + "/" + str(y)
                filters = shared + [values("fm_native_metric", "RowID", metric),
                    "TREATAS({" + str(window) + "},'fm_native_trend'[Window])",
                    values("fm_native_periods", "PeriodKey", str(y) + ":FY")]
                members = [('P', 'N Plan'), ('B', 'N Benchmark'), ('V', 'N Variance %'), ('T', 'N Trend Monthly')]
                expressions = []
                for label, measure in members:
                    extra = ["TREATAS({DATE(" + str(y) + ",12,1)},'fm_review_axis'[Month])"] if label == 'T' else []
                    expressions.append(json.dumps(label) + ',CALCULATE([' + measure + '],'
                                       + ",".join(filters + extra) + ')')
                rows.append('ROW("CheckKey",' + json.dumps(key) + ',' + ','.join(expressions) + ')')
    return definitions + "EVALUATE UNION(\n" + ",\n".join(rows) + ")"


def records(frame):
    result = []
    for row in frame.to_dict("records"):
        # SemPy may return bracketed aliases. Only locally held values are used.
        result.append({key.rsplit("[", 1)[-1].rstrip("]"): value for key, value in row.items()})
    return result


def verify_numeric(evaluate, workspace, dataset, overrides):
    def query(dax):
        try:
            return records(evaluate(dataset=dataset, dax_string=dax, workspace=workspace,
                                    verbose=0, use_readwrite_connection=False))
        except Exception as exc:
            raise RuntimeError("Read-only numerical preflight unavailable; no model write. Error type: "
                               + type(exc).__name__) from None
    scopes = query(METADATA_QUERY)
    if len(scopes) != 1 or set(scopes[0]) != {"Country", "Cycle", "Driver"}:
        raise RuntimeError("No unique available ADS test scope; no model write.")
    print("Read-only comparison: one available ADS driver, 3 measures, 3 trend windows, 2 years. Amounts stay private.", flush=True)
    start = time.monotonic()
    original = query(build_query(scopes[0], {}))
    original_ms = round((time.monotonic()-start)*1000)
    start = time.monotonic()
    candidate = query(build_query(scopes[0], overrides))
    candidate_ms = round((time.monotonic()-start)*1000)
    a = {(r["CheckKey"], field): r[field] for r in original for field in ('P', 'B', 'V', 'T')}
    b = {(r["CheckKey"], field): r[field] for r in candidate for field in ('P', 'B', 'V', 'T')}
    if len(a) != 72 or len(original) != 18 or set(a) != set(b) or len(candidate) != 18:
        raise RuntimeError("Incomplete numerical preflight; no model write.")
    def blank(value):
        return value is None or isinstance(value, (float, int)) and math.isnan(float(value))
    numeric = 0
    benchmark_numeric, future_trend_numeric = 0, 0
    for key, left in a.items():
        right = b[key]
        if blank(left) or blank(right):
            same = blank(left) and blank(right)
        else:
            numeric += 1
            if key[1] == 'B': benchmark_numeric += 1
            if key[1] == 'T' and key[0].endswith('/' + str(int(str(scopes[0]['Cycle'])[:4])+1)):
                future_trend_numeric += 1
            same = math.isfinite(float(left)) and math.isfinite(float(right)) and math.isclose(
                float(left), float(right), rel_tol=1e-9, abs_tol=1e-6)
        if not same:
            raise RuntimeError("Numerical preflight mismatch; no model write. No company values printed.")
    if numeric == 0 or benchmark_numeric == 0 or future_trend_numeric == 0:
        raise RuntimeError("No informative benchmark/future-trend comparisons in preflight; no model write.")
    result = {"Checks": 72, "NumericComparisons": numeric, "BlankComparisons": 72-numeric,
              "Mismatches": 0, "OriginalQueryMs": original_ms, "CandidateQueryMs": candidate_ms,
              "NumericBenchmarks": benchmark_numeric, "NumericFutureTrends": future_trend_numeric,
              "TimingCaveat": "Small representative scope; original runs first; cache order differs; not report speed acceptance",
              "CompanyAmountValuesPrintedOrStored": False}
    print("Numerical preflight passed: 72 checks; no amounts printed.", flush=True)
    return result
