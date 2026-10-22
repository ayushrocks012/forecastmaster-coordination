"""Synthetic native engine regression, including visual-shaped queries.

No company source, source amount, credentials, or service connection is read.
"""
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import model
spec=importlib.util.spec_from_file_location("old_engine",HERE.parent/"report-native-onelake-r17.1/tests/engine_fixture.py")
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)


def build():
    before,queries,lookup,parser=old.create_fixture()
    db,changed=model.patch_database(before)
    db["name"]=db["id"]="ForecastMasterNativeSyntheticR172"
    queries=json.loads(json.dumps(queries).replace("fm_review_periods","fm_native_periods"))
    filters=['TREATAS({"UK"},\'fm_review_files\'[Country])','TREATAS({"2026-10"},\'fm_review_files\'[DemandCycle])',
             'TREATAS({"Local"},\'fm_native_currency\'[Currency])','TREATAS({"Units"},\'fm_native_display\'[Display])',
             'TREATAS({"market"},\'fm_native_catalog\'[RowID])']
    expected={}
    def query(name,expression,extra=()):
        queries.append({"name":name,"query":'EVALUATE ROW("V",CALCULATE('+expression+','+','.join(filters+list(extra))+'))'})
    for year in (2024,2025,2026,2027):
        for kind,start,end in (("YTD",0,8),("YTG",8,12),("H1",0,6),("H2",6,12)):
            name=f"period/{year}/{kind}"
            month_indices=range((year-2024)*12+start,(year-2024)*12+end)
            monthly=[old.old.available([lookup[("UK",sec,"market","Units",i)] for sec in old.old.ALL_SECTORS]) for i in month_indices]
            expected[name]=sum(monthly) if all(v is not None for v in monthly) else None
            query(name,"[N Plan]",[f'TREATAS({{{json.dumps(str(year)+":"+kind)}}},\'fm_native_periods\'[PeriodKey])'])
    # A negative trend's percentage must retain plan-minus-trend sign.
    queries.append({"name":"negative-denominator","query":'''EVALUATE ROW("P",CALCULATE([N Plan],
 TREATAS({"UK"},'fm_review_files'[Country]),TREATAS({"2026-10"},'fm_review_files'[DemandCycle]),
 TREATAS({"internal"},'fm_native_catalog'[RowID]),TREATAS({"Units"},'fm_native_display'[Display]),
 TREATAS({"2027:FY"},'fm_native_periods'[PeriodKey])),
 "B",CALCULATE([N Benchmark],TREATAS({"UK"},'fm_review_files'[Country]),TREATAS({"2026-10"},'fm_review_files'[DemandCycle]),
 TREATAS({"internal"},'fm_native_catalog'[RowID]),TREATAS({"2027:FY"},'fm_native_periods'[PeriodKey])),
 "V",CALCULATE([N Variance %],TREATAS({"UK"},'fm_review_files'[Country]),TREATAS({"2026-10"},'fm_review_files'[DemandCycle]),
 TREATAS({"internal"},'fm_native_catalog'[RowID]),TREATAS({"2027:FY"},'fm_native_periods'[PeriodKey])))'''})
    queries.append({"name":"visual/headline","query":'''EVALUATE SUMMARIZECOLUMNS(
 'fm_review_files'[DemandCycle],'fm_native_scenario'[Scenario],'fm_native_headline'[Label],'fm_native_periods'[Label],
 TREATAS({"UK"},'fm_review_files'[Country]),TREATAS({"2026-10"},'fm_review_files'[DemandCycle]),
 TREATAS({"Automatic ADS"},'fm_native_scenario'[Mode]),TREATAS({"2026 FY","2026 YTD","2026 YTG","2027 FY"},'fm_native_periods'[Label]),
 TREATAS({"Local"},'fm_native_currency'[Currency]),"Value",[N Headline Cell])'''})
    queries.append({"name":"visual/sop-groups","query":'''EVALUATE SUMMARIZECOLUMNS(
 'fm_native_groups'[ScopeLabel], 'fm_native_rows'[Measure],
 TREATAS({"Drivers"},'fm_native_view'[View]),TREATAS({"UK"},'fm_review_files'[Country]),
 TREATAS({"2026-10"},'fm_review_files'[DemandCycle]),TREATAS({"2026:FY"},'fm_native_periods'[PeriodKey]),
 TREATAS({"row:market:Units:0:0:0"},'fm_native_state'[Token]),"V",[N SOP Plan])'''})
    queries.append({"name":"visual/month-readout","query":'''EVALUATE ROW("Month",CALCULATE([N Selected Month],
 TREATAS({DATE(2026,3,1)},'fm_review_axis'[Month])),"None",[N Selected Month])'''})
    return db,queries,lookup,parser,expected


def verify(results,lookup,parser,expected):
    # The frozen oracle names the former period table; only column identity
    # changes for its unchanged FY/current-cutoff-year arithmetic cases.
    result=old.verify(json.loads(json.dumps(results).replace("fm_native_periods[","fm_review_periods[")),lookup,parser)
    by={r["name"]:r for r in results}
    for r in results:
        if "error" in r:result["Failures"].append(r["name"]+": "+r["error"])
    for name,expected_value in expected.items():
        got=by.get(name,{}).get("rows",[{}])[0].get("[V]")
        result["Checks"]+=1
        if expected_value is None:
            if got is not None:result["Failures"].append(name+" should be blank")
        elif not isinstance(got,(int,float)) or not math.isclose(got,expected_value,rel_tol=1e-9):
            result["Failures"].append(f"{name}: {got} != {expected_value}")
    r=by.get("negative-denominator",{}).get("rows",[{}])[0]
    if all(isinstance(r.get(k),(int,float)) for k in ("[P]","[B]","[V]")):
        if r["[B]"]>=0 or not math.isclose(r["[V]"],(r["[P]"]-r["[B]"])/abs(r["[B]"]),abs_tol=1e-10):
            result["Failures"].append("Negative benchmark percentage mismatch")
    else:result["Failures"].append("Negative benchmark query did not return numeric results")
    result["Checks"]+=1
    headline=by.get("visual/headline",{}).get("rows",[])
    # 4 plan cells; actual-only YTD variances stay blank and are suppressed.
    if len(headline)!=10:result["Failures"].append(f"Headline visual rows: {len(headline)} != 10")
    group=by.get("visual/sop-groups",{}).get("rows",[])
    if len(group)!=2:result["Failures"].append(f"SOP driver groups: {len(group)} != 2")
    else:
        expected_groups={"Example Oral":sum(old.old.available([lookup[("UK",s,"market","Units",i)] for s in ("Example A","Example B","")]) for i in range(24,36)),
                         "Example Paed":sum(lookup[("UK","Example C","market","Units",i)] for i in range(24,36))}
        for r in group:
            label=r.get("fm_native_groups[ScopeLabel]")
            if label not in expected_groups or not math.isclose(r["[V]"],expected_groups[label]):result["Failures"].append("SOP grouping arithmetic mismatch")
    r=by.get("visual/month-readout",{}).get("rows",[{}])[0]
    if r.get("[Month]")!="Mar 2026" or r.get("[None]") is not None:result["Failures"].append("Monthly readout mismatch")
    result["Checks"]+=4
    return result


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("directory",type=Path);p.add_argument("--verify",type=Path);a=p.parse_args()
    db,queries,lookup,parser,expected=build()
    if a.verify:
        result=verify(json.loads(a.verify.read_text(encoding="utf-8-sig")),lookup,parser,expected)
        result["RetainedInputMatches"]=json.loads((a.directory/"synthetic-model.json").read_text())==db
        if not result["RetainedInputMatches"]:result["Failures"].append("Retained synthetic input differs")
        print(json.dumps(result,indent=2));raise SystemExit(bool(result["Failures"]))
    a.directory.mkdir(exist_ok=True,parents=True)
    (a.directory/"synthetic-model.json").write_text(json.dumps(db,ensure_ascii=False))
    (a.directory/"queries.json").write_text(json.dumps(queries))
    for name in ("fx-queries","edge-queries"):(a.directory/(name+".json")).write_text("[]")
    print("Synthetic R17.2 fixture ready")
