"""Qualify calculated metadata and rank-independent chart selection synthetically.

All source tables here are calculated/import fixtures, not Direct Lake. Passing
this engine suite does not qualify the receiving Direct Lake preview feature.
"""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import onelake_model as om
sys.path.insert(0, str(om.R17 / "tests"))
import native_fixture as old


def create_fixture():
    previous, lookup = old.fixture()
    review_tables = [t for t in previous["model"]["tables"] if t["name"].startswith("fm_review_")]
    files = next(t for t in review_tables if t["name"] == "fm_review_files")
    # Synthetic names intentionally produce the same scenario labels as the
    # previous manually supplied fixture; no company file labels are read.
    records = []
    for country in ("UK", "Example EUR", "Example USD"):
        for driver, short in (("Example Oral", "a"), ("Example Paed", "b")):
            source = country + "-" + short
            records.append(dict(SourceRevisionID=source, SourceFileName=source + "_IMS202608_ADS.xlsm",
                SourceRelativePath="Synthetic/" + source, Country=country, DemandCycle="2026-10",
                GrowthDriver=driver, SourceProfile="Ext", PublicationStatus="SAVED", FileLabel=source,
                IMSActualsThrough=old.date(2026, 8, 1), ExFactoryActualsThrough=old.date(2026, 9, 1)))
    review = dict(records[0], SourceRevisionID="UK-a-review", FileLabel="UK-a-review",
                  SourceFileName="Synthetic_IMS202608_REVIEW_001.xlsm")
    records.append(review)
    records.append(dict(records[0], SourceRevisionID="inactive", FileLabel="inactive",
                        GrowthDriver="Example Inactive", DemandCycle="2025-10"))
    parser = []
    for id_, suffix, imported, priority, revision in (
        ("p1", "ADS", "2026-10-22T08:00:00+00:00", 2, 0),
        ("p2", "ADS", "2026-10-22T09:00:00+01:00", 2, 0),
        ("p3", "PLAN_ADS", "2026-10-21T08:00:00Z", 3, 0),
        ("p4", "ADS_2", "2026-10-22T08:00:00Z", 1, 2),
        ("p5", "ADS_3", "2026-10-22T08:00:00Z", 1, 3),
        ("p6", "PLAN_ADS", "2026-10-21T08:00:00.500000Z", 3, 0),
        ("p7", "ADS_1.0", "2026-10-22T08:00:00Z", 0, 0),
        ("p8", "ADS_+4", "2026-10-22T08:00:00Z", 1, 4),
        ("p9", "ADS_2e2", "2026-10-22T08:00:00Z", 0, 0),
    ):
        name = "Parser_IMS202608_" + suffix + ".xlsm"
        records.append(dict(records[0], SourceRevisionID=id_, SourceFileName=name, Country="Parser",
            GrowthDriver="Parser", FileLabel=name + " · Imported " + imported + " · Synthetic/Parser · " + id_))
        parser.append({"id": id_, "priority": priority, "revision": revision,
                       "timestamp": datetime.fromisoformat(imported.replace("Z", "+00:00")).timestamp(),
                       "scenario": suffix.upper()})
    review_tables[review_tables.index(files)] = old.datatable("fm_review_files", records)
    database = deepcopy(previous)
    database["name"] = database["id"] = "ForecastMasterNativeSyntheticOneLakeR171"
    database["model"]["tables"] = review_tables
    database["model"].pop("relationships", None)
    database["model"]["expressions"] = [{"name": "OriginalSource", "kind": "m",
                                          "expression": 'AzureStorage.DataLake("synthetic.invalid")'}]
    fact = next(t for t in review_tables if t["name"] == "fm_review_facts")
    actual_partition = deepcopy(fact["partitions"])
    fact["partitions"] = [{"name": "Source", "mode": "directLake", "source": {
        "type": "entity", "entityName": "fm_review_facts", "expressionSource": "OriginalSource"}}]
    database = om.extend_onelake(database)
    next(t for t in database["model"]["tables"] if t["name"] == "fm_review_facts")["partitions"] = actual_partition
    database["model"].pop("expressions")
    # Keep the old fixture's three fabricated currencies to exercise FX safely.
    old_tables = {t["name"]: t for t in previous["model"]["tables"]}
    for table in database["model"]["tables"]:
        if table["name"] in {"fm_native_state", "fm_native_rows", "fm_native_currency_map"}:
            table["partitions"] = deepcopy(old_tables[table["name"]]["partitions"])
    queries = old.queries()
    queries.append({"name": "parser", "query": "EVALUATE FILTER(SELECTCOLUMNS('fm_native_files',"
        '\"ID\",[SourceRevisionID],\"P\",[ADSPriority],\"R\",[ADSRevision],\"Rank\",[PreferenceRank],'
        '\"Ties\",[PreferenceTies],\"Scenario\",[Scenario]),LEFT([ID],1)=\"p\")'})
    for row in ("abbott", "market", "share", "wholesaler"):
        for display in ("Units", "Value"):
            for rank in ("0:0:0", "3:2:4"):
                token = f"row:{row}:{display}:{rank}"
                filters = ['TREATAS({"UK"},\'fm_review_files\'[Country])',
                    'TREATAS({"2026-10"},\'fm_review_files\'[DemandCycle])',
                    'TREATAS({"Total"},\'fm_native_lines\'[ViewType])',
                    'TREATAS({"Automatic ADS"},\'fm_native_lines\'[Mode])',
                    'TREATAS({"Automatic ADS"},\'fm_native_lines\'[Scenario])',
                    'TREATAS({"2026-10"},\'fm_native_lines\'[DemandCycle])',
                    'TREATAS({"sop"},\'fm_native_lines\'[Chart])',
                    f'TREATAS({{{json.dumps(row)}}},\'fm_native_lines\'[RowID])',
                    f'TREATAS({{{json.dumps(display)}}},\'fm_native_display\'[Display])',
                    'TREATAS({0},\'fm_native_lines\'[LineKind])',
                    'TREATAS({"Local"},\'fm_native_currency\'[Currency])',
                    'TREATAS({DATE(2026,1,1)},\'fm_review_axis\'[Month])',
                    f'TREATAS({{{json.dumps(token)}}},\'fm_native_state\'[Token])']
                queries.append({"name": f"chart/{row}/{display}/{rank}", "query":
                    'EVALUATE ROW("V",CALCULATE([N Chart Monthly],' + ','.join(filters) + '))'})
    return database, queries, lookup, parser


def verify(results, lookup, parser):
    primary = old.verify([r for r in results if r["name"] in {"aggregate", "leaf", "availability"}], lookup)
    failures = primary["Failures"]
    checks = primary["Checks"]
    by_name = {r["name"]: r for r in results}
    parsed = by_name.get("parser", {})
    if "error" in parsed:
        failures.append(parsed["error"])
    actual = {r["[ID]"]: r for r in parsed.get("rows", [])}
    ranks = sorted({(r["priority"], r["revision"], r["timestamp"]) for r in parser}, reverse=True)
    for row in parser:
        key = (row["priority"], row["revision"], row["timestamp"])
        expected = {"[P]": row["priority"], "[R]": row["revision"], "[Rank]": ranks.index(key) + 1,
                    "[Ties]": sum((r["priority"], r["revision"], r["timestamp"]) == key for r in parser),
                    "[Scenario]": row["scenario"]}
        for field, value in expected.items():
            checks += 1
            if actual.get(row["id"], {}).get(field) != value:
                failures.append(f'Parser {row["id"]} {field}: {actual.get(row["id"])} != {value}')
    for name, group in by_name.items():
        if not name.startswith("chart/"):
            continue
        _, row, display, rank = name.split("/")
        sectors = old.ALL_SECTORS
        nums = old.available([lookup[("UK", sector, "abbott" if row == "share" else row, display, 24)] for sector in sectors])
        expected = nums / sum(lookup[("UK", sector, "market", display, 24)] for sector in sectors) if row == "share" else nums
        actual_value = group.get("rows", [{}])[0].get("[V]")
        checks += 1
        if "error" in group or not isinstance(actual_value, (int, float)) or not math.isclose(actual_value, expected):
            failures.append(f"{name}: {group} != {expected}")
    return {"Checks": checks, "Failures": failures,
            "Evidence": "Local Power BI engine, all source facts synthetic/calculated. No company data.",
            "ReceivingDirectLakePreview": "UNVERIFIED", "DesktopUIOrExport": "UNVERIFIED"}


if __name__ == "__main__":
    parser_ = argparse.ArgumentParser()
    parser_.add_argument("directory", type=Path)
    parser_.add_argument("--verify", type=Path)
    args = parser_.parse_args()
    database, queries, lookup, parsing = create_fixture()
    if args.verify:
        results = json.loads(args.verify.read_text(encoding="utf-8-sig"))
        result = verify(results, lookup, parsing)
        input_path = args.directory / "synthetic-model.json"
        result["CurrentFixtureMatchesRetainedEngineInput"] = json.loads(input_path.read_text()) == database
        if not result["CurrentFixtureMatchesRetainedEngineInput"]:
            result["Failures"].append("Current fixture differs from the retained engine input; run the engine again.")
        result["EngineInputSHA256"] = hashlib.sha256(input_path.read_bytes()).hexdigest()
        result["EngineResultSHA256"] = hashlib.sha256(args.verify.read_bytes()).hexdigest()
        result["SourceSHA256"] = {str(p.relative_to(ROOT.parents[1])): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / "onelake_model.py", Path(__file__), om.R17 / "native_model.py")}
        (ROOT / "VALIDATION-ENGINE.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        raise SystemExit(bool(result["Failures"]))
    args.directory.mkdir(parents=True, exist_ok=True)
    (args.directory / "synthetic-model.json").write_text(json.dumps(database, ensure_ascii=False))
    (args.directory / "queries.json").write_text(json.dumps(queries))
    for stem in ("fx-queries", "edge-queries"):
        (args.directory / (stem + ".json")).write_text("[]")
    print("Synthetic OneLake-shape fixture ready; no external source or credentials.")
