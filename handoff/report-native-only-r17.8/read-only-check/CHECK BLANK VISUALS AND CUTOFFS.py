"""ONE NEW ForecastMaster_GM_Setup cell. TEST metadata/counts only, no updates.

Checks the reported UK / 2026-10 / Market / Units state. No amounts, filenames,
revision IDs or connection contents are printed. No refresh or source write.
"""
import json
import time

WORKSPACE = "f5cb5742-9a7c-4337-a4c0-952706dddf0b"
TEST_MODEL = "31d00232-ac03-48fe-af39-f2e4bae82443"
TEST_NAME = "ForecastMaster Native OneLake R17.1 - TEST"
ITEM = "/v1/workspaces/" + WORKSPACE + "/items/" + TEST_MODEL

FILES_QUERY = '''EVALUATE
VAR _source=FILTER(ALL('fm_review_files'),'fm_review_files'[Country]="UK"
 &&'fm_review_files'[DemandCycle]="2026-10")
VAR _native=FILTER(ALL('fm_native_files'),'fm_native_files'[Country]="UK"
 &&'fm_native_files'[DemandCycle]="2026-10")
VAR _auto=FILTER(_native,'fm_native_files'[ADSPriority]>0
 &&'fm_native_files'[PreferenceRank]=1&&'fm_native_files'[PreferenceTies]=1)
VAR _ids=SELECTCOLUMNS(_source,"ID",'fm_review_files'[SourceRevisionID]&"")
VAR _nativeIds=SELECTCOLUMNS(_native,"ID",'fm_native_files'[SourceRevisionID]&"")
VAR _paired=ADDCOLUMNS(_source,"__NativeIMS",VAR _id='fm_review_files'[SourceRevisionID]
 RETURN MAXX(FILTER(_native,'fm_native_files'[SourceRevisionID]=_id),'fm_native_files'[IMSActualsThrough]),
 "__NativeEF",VAR _id='fm_review_files'[SourceRevisionID]
 RETURN MAXX(FILTER(_native,'fm_native_files'[SourceRevisionID]=_id),'fm_native_files'[ExFactoryActualsThrough]))
RETURN ROW("SourceRows",COUNTROWS(_source),"NativeRows",COUNTROWS(_native),
 "AutomaticADSSources",COUNTROWS(_auto),
 "SourceInvalidIMS",COUNTROWS(FILTER(_source,ISBLANK('fm_review_files'[IMSActualsThrough])
 ||'fm_review_files'[IMSActualsThrough]<DATE(2000,1,1)||'fm_review_files'[IMSActualsThrough]>=DATE(2100,1,1))),
 "SourceInvalidEF",COUNTROWS(FILTER(_source,ISBLANK('fm_review_files'[ExFactoryActualsThrough])
 ||'fm_review_files'[ExFactoryActualsThrough]<DATE(2000,1,1)||'fm_review_files'[ExFactoryActualsThrough]>=DATE(2100,1,1))),
 "NativeInvalidIMS",COUNTROWS(FILTER(_native,ISBLANK('fm_native_files'[IMSActualsThrough])
 ||'fm_native_files'[IMSActualsThrough]<DATE(2000,1,1)||'fm_native_files'[IMSActualsThrough]>=DATE(2100,1,1))),
 "NativeInvalidEF",COUNTROWS(FILTER(_native,ISBLANK('fm_native_files'[ExFactoryActualsThrough])
 ||'fm_native_files'[ExFactoryActualsThrough]<DATE(2000,1,1)||'fm_native_files'[ExFactoryActualsThrough]>=DATE(2100,1,1))),
 "AutoInvalidIMS",COUNTROWS(FILTER(_auto,ISBLANK('fm_native_files'[IMSActualsThrough])
 ||'fm_native_files'[IMSActualsThrough]<DATE(2000,1,1)||'fm_native_files'[IMSActualsThrough]>=DATE(2100,1,1))),
 "AutoInvalidEF",COUNTROWS(FILTER(_auto,ISBLANK('fm_native_files'[ExFactoryActualsThrough])
 ||'fm_native_files'[ExFactoryActualsThrough]<DATE(2000,1,1)||'fm_native_files'[ExFactoryActualsThrough]>=DATE(2100,1,1))),
 "SourceIdsMissingNative",COUNTROWS(EXCEPT(_ids,_nativeIds)),
 "NativeIdsMissingSource",COUNTROWS(EXCEPT(_nativeIds,_ids)),
 "IMSMetadataMismatch",COUNTROWS(FILTER(_paired,NOT('fm_review_files'[IMSActualsThrough]==[__NativeIMS]))),
 "EFMetadataMismatch",COUNTROWS(FILTER(_paired,NOT('fm_review_files'[ExFactoryActualsThrough]==[__NativeEF]))))'''

GUARDS_QUERY = '''EVALUATE CALCULATETABLE(
ROW("SourceOK",IF([N Source OK]=1,1,0),
 "CutoffValid",IF(NOT ISBLANK([N Cutoff])&&[N Cutoff]>=DATE(2000,1,1)&&[N Cutoff]<DATE(2100,1,1),1,0),
 "FitCutoffValid",IF(NOT ISBLANK([N Fit Cutoff])&&[N Fit Cutoff]>=DATE(2000,1,1)&&[N Fit Cutoff]<DATE(2100,1,1),1,0),
 "PeriodAvailable",IF([N Period Available]=1,1,0),
 "MetricChoices",COUNTROWS(VALUES('fm_native_metric'[RowID])),
 "ScenarioChoices",COUNTROWS(VALUES('fm_native_scenario'[Scenario])),
 "AvailableScopeRows",COUNTROWS('fm_native_scope')),
TREATAS({"UK"},'fm_review_files'[Country]),TREATAS({"2026-10"},'fm_review_files'[DemandCycle]),
TREATAS({"market"},'fm_native_metric'[RowID]),TREATAS({"Units"},'fm_native_display'[Display]),
TREATAS({"Automatic ADS"},'fm_native_file_mode'[Mode]),TREATAS({"Automatic ADS"},'fm_native_scenario'[Scenario]),
TREATAS({"2026 FY"},'fm_native_periods'[Label]),
TREATAS({DATE(2025,1,1)},'fm_native_start_month'[Month]),
TREATAS({DATE(2027,12,1)},'fm_native_end_month'[Month]))'''

FIELDS = {
    "Files": {"SourceRows", "NativeRows", "AutomaticADSSources", "SourceInvalidIMS", "SourceInvalidEF",
              "NativeInvalidIMS", "NativeInvalidEF", "AutoInvalidIMS", "AutoInvalidEF", "SourceIdsMissingNative",
              "NativeIdsMissingSource", "IMSMetadataMismatch", "EFMetadataMismatch"},
    "Guards": {"SourceOK", "CutoffValid", "FitCutoffValid", "PeriodAvailable", "MetricChoices", "ScenarioChoices", "AvailableScopeRows"}}


def counts(frame, expected):
    rows = frame.to_dict(orient="records")
    if len(rows) != 1:
        raise ValueError("Unexpected metadata row count")
    row = {key.rsplit("[", 1)[-1].rstrip("]"): value for key, value in rows[0].items()}
    if set(row) != expected:
        raise ValueError("Unexpected metadata columns")
    result = {}
    for key, value in row.items():
        # COUNTROWS over an empty table is BLANK. Keep the read boundary
        # explicit: only these known cardinalities, never financial values.
        if value is None or isinstance(value, float) and value != value:
            value = 0
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or int(value) != value:
            raise ValueError("Unexpected metadata count type")
        result[key] = int(value)
    return result


def run(client, evaluate):
    response = client.get(ITEM)
    if response.status_code != 200:
        raise RuntimeError("TEST identity unavailable")
    identity = response.json()
    if identity.get("id") != TEST_MODEL or identity.get("displayName") != TEST_NAME or identity.get("type") != "SemanticModel":
        raise RuntimeError("TEST identity mismatch")
    checks = {}
    for name, dax in (("Files", FILES_QUERY), ("Guards", GUARDS_QUERY)):
        print("Read-only TEST " + name + ": metadata counts only.", flush=True)
        start = time.monotonic()
        value = counts(evaluate(dataset=TEST_MODEL, dax_string=dax, workspace=WORKSPACE,
                                verbose=0, use_readwrite_connection=False), FIELDS[name])
        checks[name] = {"Counts": value, "ElapsedMs": round((time.monotonic()-start)*1000)}
    result = {"Stage": "R178_METADATA_READS_COMPLETED", "TestModelID": TEST_MODEL,
              "Scope": "UK / 2026-10 / Market / Units / Automatic ADS / 2026 FY",
              "Checks": checks, "CompanyAmountsQueriedOrPrinted": False, "ModelWriteRequested": False,
              "RefreshRequested": False, "ReportPublished": False,
              "NextStep": "Send this JSON. Keep the existing private backup; do not rerun an updater or refresh again."}
    print(json.dumps(result, indent=2), flush=True)
    return result


def safe_run(client, evaluate):
    try:
        return run(client, evaluate)
    except Exception as exc:
        result = {"Stage": "R178_METADATA_CHECK_STOPPED", "ExceptionFamily": type(exc).__name__,
                  "RawErrorPrinted": False, "CompanyAmountsQueriedOrPrinted": False, "ModelWriteRequested": False,
                  "RefreshRequested": False, "ReportPublished": False,
                  "NextStep": "Send this JSON. No updater/refresh retry."}
        print(json.dumps(result, indent=2), flush=True)
        return result


if __name__ == "__main__":
    import sempy.fabric as fabric
    safe_run(fabric.FabricRestClient(), fabric.evaluate_dax)
