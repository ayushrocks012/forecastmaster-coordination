"""Reporting projection retains R03.1 arithmetic and adds folder-independent path aliases."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from typing import Any

from delta.tables import DeltaTable
from pyspark.sql import functions as F


def update_reporting(engine: Any, embedded_rules: str) -> bool:
    spark = engine.spark
    SOURCE_PREFIX = engine.prefix
    REPORT_PREFIX = engine.config.get("REPORT_PREFIX", "fm_review")
    RULES_PATH = engine.config.get(
        "REPORT_RULES_PATH", "Files/ForecastMasterControls/ReportMeasureRules.csv"
    )
    FORCE_REBUILD_REPORTING_FACTS = engine.config.get(
        "FORCE_REBUILD_REPORTING_FACTS", False
    )
    EMBEDDED_RULES_CSV = embedded_rules

    def utc_now() -> str:
        return datetime.now(UTC).isoformat()

    try:
        raw_rules = [
            r.asDict()
            for r in spark.read.option("header", True)
            .option("encoding", "UTF-8")
            .csv(RULES_PATH)
            .collect()
        ]
        print("Measure definitions:", RULES_PATH)
    except Exception as exc:
        if "PATH_NOT_FOUND" not in str(exc) and "does not exist" not in str(exc):
            raise
        raw_rules = list(csv.DictReader(io.StringIO(EMBEDDED_RULES_CSV)))
        print("Measure definitions: embedded initial seven-metric configuration")
    required_rules = {
        "MetricKey",
        "Section",
        "Measure",
        "Unit",
        "Aggregation",
        "CutoffFamily",
        "NumeratorKey",
        "NumeratorSection",
        "NumeratorMeasure",
        "NumeratorManufacturer",
        "NumeratorRequireProduct",
        "DenominatorKey",
        "DenominatorSection",
        "DenominatorMeasure",
        "DenominatorManufacturer",
        "DenominatorRequireProduct",
        "SortIndex",
    }
    raw_rules = [
        {k: "" if v is None else str(v) for k, v in r.items()} for r in raw_rules
    ]
    if not raw_rules or any(not required_rules <= set(r) for r in raw_rules):
        raise ValueError(
            "ReportMeasureRules.csv is missing required columns or contains no definitions"
        )
    if len({r["MetricKey"] for r in raw_rules}) != len(raw_rules):
        raise ValueError("MetricKey must be unique")
    components: dict[str, tuple[str, str, str, bool]] = {}
    for r in raw_rules:
        if not all(r[k] for k in ("MetricKey", "Section", "Measure", "NumeratorKey")):
            raise ValueError(
                "Each metric needs a nonempty identity, label and numerator"
            )
        r["SortIndex"] = str(int(r["SortIndex"]))
        if r["Aggregation"] not in ("SUM", "RATIO") or r["CutoffFamily"] not in (
            "IMS",
            "EF",
        ):
            raise ValueError("Unknown aggregation/cutoff definition: " + r["MetricKey"])
        if r["Unit"] not in ("Units", "£", "%", "Litres", "Pounds"):
            raise ValueError("Define an explicit supported Unit for " + r["MetricKey"])
        if r["Aggregation"] == "RATIO" and (not r["DenominatorKey"]):
            raise ValueError("Ratio requires a denominator: " + r["MetricKey"])
        for part in ("Numerator", "Denominator"):
            key = r[part + "Key"]
            if not key:
                continue
            if str(r[part + "RequireProduct"]).lower() not in ("true", "false"):
                raise ValueError("RequireProduct must be true or false for " + key)
            rule = (
                r[part + "Section"],
                r[part + "Measure"],
                r[part + "Manufacturer"],
                str(r[part + "RequireProduct"]).lower() == "true",
            )
            if not rule[0] or not rule[1]:
                raise ValueError(
                    "Exact original source section/measure required for " + key
                )
            if key in components and components[key] != rule:
                raise ValueError("Conflicting definitions for component " + key)
            components[key] = rule
    rule_hash = hashlib.sha256(
        json.dumps(raw_rules, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    receipt_name = REPORT_PREFIX + "_projection_receipts"
    fact_name = REPORT_PREFIX + "_facts"
    source_rows = engine.report_sources()
    source_schema = ", ".join(k + " string" for k in source_rows[0])
    sources = spark.createDataFrame(source_rows, source_schema)
    report_signature = hashlib.sha256(
        json.dumps(
            {
                "rules": raw_rules,
                "sources": source_rows,
                "profiles": sorted(engine.allowed),
                "identityPolicy": "current-file-v1",
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    state_name = REPORT_PREFIX + "_refresh_state"
    required_helpers = [
        REPORT_PREFIX + "_" + name
        for name in (
            "facts",
            "files",
            "reference",
            "measures",
            "months",
            "axis",
            "periods",
            "series",
            "modes",
        )
    ]
    if spark.catalog.tableExists(state_name) and all(
        spark.catalog.tableExists(name) for name in required_helpers
    ):
        signatures = {
            r[0] for r in spark.table(state_name).select("Signature").collect()
        }
        if signatures == {report_signature}:
            print(
                "Reporting sources and rules unchanged: no reporting tables rewritten.",
                flush=True,
            )
            return False
    if sources.limit(1).count() == 0:
        raise ValueError(
            "No completed source revisions in the configured source profile"
        )
    if sources.groupBy("SourceRevisionID").count().where("count <> 1").limit(1).count():
        raise ValueError("SourceRevisionID is not unique")
    existing_ids = []
    rebuild = FORCE_REBUILD_REPORTING_FACTS or not spark.catalog.tableExists(fact_name)
    if spark.catalog.tableExists(receipt_name) and (not rebuild):
        receipts = spark.table(receipt_name)
        hashes = {r[0] for r in receipts.select("RuleHash").distinct().collect()}
        if "ContentRevisionID" not in receipts.columns:
            rebuild = True
        if hashes != {rule_hash}:
            rebuild = True
            print(
                "Report definitions changed: rebuilding derived reporting facts from retained source history."
            )
        else:
            if not rebuild:
                completed = {
                    r["SourceRevisionID"]: r["ContentRevisionID"]
                    for r in receipts.collect()
                }
                existing_ids = [
                    r["SourceRevisionID"]
                    for r in source_rows
                    if completed.get(r["SourceRevisionID"]) == r["RawSourceRevisionID"]
                ]
    pending = (
        sources
        if rebuild or not existing_ids
        else sources.where(~F.col("SourceRevisionID").isin(existing_ids))
    )
    pending_ids = [r[0] for r in pending.select("SourceRevisionID").collect()]
    if pending_ids:
        component_schema = "ComponentKey string, SourceSection string, SourceMeasure string, ManufacturerRule string, RequireProduct boolean"
        cfg = spark.createDataFrame(
            [(k, *v) for k, v in components.items()], component_schema
        ).alias("c")
        pending_map = pending.select(
            "RawSourceRevisionID", F.col("SourceRevisionID").alias("ReportRevisionID")
        ).alias("s")
        raw_ids = [
            r[0] for r in pending_map.select("RawSourceRevisionID").distinct().collect()
        ]
        raw_history = (
            spark.table(SOURCE_PREFIX + "_history")
            .where(F.col("SourceRevisionID").isin(raw_ids))
            .alias("raw")
        )
        history = (
            raw_history.join(
                F.broadcast(pending_map),
                F.col("raw.SourceRevisionID") == F.col("s.RawSourceRevisionID"),
                "inner",
            )
            .select(
                *[
                    F.col("raw." + name)
                    for name in raw_history.columns
                    if name != "SourceRevisionID"
                ],
                F.col("s.ReportRevisionID").alias("SourceRevisionID"),
            )
            .alias("h")
        )
        matched = history.join(
            F.broadcast(cfg),
            (F.col("h.Section") == F.col("c.SourceSection"))
            & (F.col("h.Measure") == F.col("c.SourceMeasure")),
            "inner",
        )
        matched = matched.where(
            (F.col("c.ManufacturerRule") == "*")
            | (
                F.lower(F.trim(F.col("h.Manufacturer")))
                == F.lower(F.col("c.ManufacturerRule"))
            )
        )
        matched = matched.where(
            ~F.col("c.RequireProduct")
            | (F.length(F.trim(F.coalesce(F.col("h.Product"), F.lit("")))) > 0)
        )
        numeric = (F.col("ValueKind") == "number") & F.col("ValueNumber").isNotNull()
        projection = matched.groupBy(
            "SourceRevisionID",
            "Channel",
            "SubChannel",
            "Sector",
            F.col("DemandMonth").alias("Month"),
            "ComponentKey",
        ).agg(
            F.sum(F.when(numeric, F.col("ValueNumber"))).alias("Amount"),
            F.sum(F.when(numeric, 1).otherwise(0)).cast("long").alias("NumericCells"),
            F.sum(F.when(numeric, 0).otherwise(1)).cast("long").alias("MissingCells"),
        )
        projection = projection.persist()
        try:
            count = projection.count()
            if count == 0:
                raise ValueError(
                    "No fact components matched the exact source definitions; check source section/measure identities"
                )
            projected_ids = {
                r[0] for r in projection.select("SourceRevisionID").distinct().collect()
            }
            unmatched_ids = set(pending_ids) - projected_ids
            if unmatched_ids:
                raise ValueError(
                    "No configured fact components matched these source revisions: "
                    + ", ".join(sorted(unmatched_ids))
                )
            if rebuild:
                engine.replace_snapshot(
                    fact_name,
                    projection,
                    [
                        "SourceRevisionID",
                        "Channel",
                        "SubChannel",
                        "Sector",
                        "Month",
                        "ComponentKey",
                    ],
                )
            else:
                # Replace the complete affected-file slice atomically. MERGE insert-only
                # would retain removed months, dimensions, and previous numeric values.
                predicate = (
                    "SourceRevisionID IN ("
                    + ",".join("'" + sid + "'" for sid in pending_ids)
                    + ")"
                )
                detail = (
                    DeltaTable.forName(spark, fact_name)
                    .detail()
                    .select("location")
                    .first()
                )
                if detail is None:
                    raise ValueError("Reporting table location is unavailable")
                projection.coalesce(2).write.format("delta").mode("overwrite").option(
                    "replaceWhere", predicate
                ).save(detail[0])
                engine.writes[fact_name] += 1
            receipt_schema = "SourceRevisionID string, RuleHash string, ProjectedAtUtc string, ContentRevisionID string"
            stamp = datetime.now(UTC).isoformat()
            new_receipts = spark.createDataFrame(
                [
                    (r["SourceRevisionID"], rule_hash, stamp, r["RawSourceRevisionID"])
                    for r in source_rows
                    if r["SourceRevisionID"] in pending_ids
                ],
                receipt_schema,
            )
            if rebuild:
                # First R04.1 run migrates the legacy receipts and facts together.
                if (
                    spark.catalog.tableExists(receipt_name)
                    and "ContentRevisionID" not in spark.table(receipt_name).columns
                ):
                    spark.sql(
                        "ALTER TABLE "
                        + receipt_name
                        + " ADD COLUMNS (ContentRevisionID STRING)"
                    )
                engine.replace_snapshot(
                    receipt_name, new_receipts, ["SourceRevisionID"]
                )
            else:
                engine.upsert(
                    receipt_name, new_receipts, ["SourceRevisionID"], update=True
                )
            print(
                "Projected",
                len(pending_ids),
                "source revisions into",
                count,
                "monthly component rows.",
            )
        finally:
            projection.unpersist()
    else:
        print("All source revisions already projected. Raw history was not rescanned.")
    active_report_ids = [r["SourceRevisionID"] for r in source_rows]
    for name in (fact_name, receipt_name):
        stale = ~F.col("SourceRevisionID").isin(active_report_ids)
        if spark.table(name).where(stale).limit(1).count():
            DeltaTable.forName(spark, name).delete(stale)
            engine.writes[name] += 1
    files = sources.select(
        "SourceRevisionID",
        "SourceFileName",
        "SourceRelativePath",
        "Country",
        "DemandCycle",
        "GrowthDriver",
        "SourceProfile",
        F.to_date("IMSActualsThrough").alias("IMSActualsThrough"),
        F.to_date("ExFactoryActualsThrough").alias("ExFactoryActualsThrough"),
        "PublicationStatus",
    )
    files = files.join(
        sources.select("SourceRevisionID", "PathFirstSeenAtUtc"),
        "SourceRevisionID",
        "inner",
    )
    files = files.withColumn(
        "FileLabel",
        F.concat(
            F.col("SourceFileName"),
            F.lit(" · Imported "),
            F.col("PathFirstSeenAtUtc"),
            F.lit(" · "),
            F.col("SourceRelativePath"),
            F.lit(" · "),
            F.substring("SourceRevisionID", 1, 8),
        ),
    ).drop("PathFirstSeenAtUtc")
    if (
        files.where(
            F.col("IMSActualsThrough").isNull()
            | F.col("ExFactoryActualsThrough").isNull()
        )
        .limit(1)
        .count()
    ):
        raise ValueError("A source receipt has no usable IMS/Ex-factory cutoff date")

    def save_small(name: str, frame: Any) -> None:
        keys = {
            "files": "SourceRevisionID",
            "reference": "SourceRevisionID",
            "measures": "MetricKey",
            "months": "Month",
            "axis": "Month",
            "periods": "PeriodKey",
            "series": "SeriesID",
            "modes": "Mode",
        }
        engine.replace_snapshot(REPORT_PREFIX + "_" + name, frame, [keys[name]])

    save_small("reference", files)
    metric_fields = [
        "MetricKey",
        "Section",
        "Measure",
        "Unit",
        "Aggregation",
        "CutoffFamily",
        "NumeratorKey",
        "DenominatorKey",
        "SortIndex",
    ]
    metric_schema = ", ".join(
        k + (" long" if k == "SortIndex" else " string") for k in metric_fields
    )
    save_small(
        "measures",
        spark.createDataFrame(
            [
                [int(r[k]) if k == "SortIndex" else r[k] for k in metric_fields]
                for r in raw_rules
            ],
            metric_schema,
        ),
    )
    calendar = spark.table(SOURCE_PREFIX + "_calendar").where(
        F.col("SourceRevisionID").isin([r["RawSourceRevisionID"] for r in source_rows])
    )
    bounds = calendar.agg(
        F.min("DemandMonth").alias("first"), F.max("DemandMonth").alias("last")
    ).first()
    if not bounds or not bounds["first"] or (not bounds["last"]):
        raise ValueError("Source calendar is empty; date limits cannot be inferred")
    months = spark.range(1).select(
        F.explode(
            F.sequence(
                F.lit(bounds["first"]),
                F.lit(bounds["last"]),
                F.expr("interval 1 month"),
            )
        ).alias("Month")
    )
    months = months.select(
        "Month",
        F.date_format("Month", "MMM yyyy").alias("MonthLabel"),
        F.year("Month").cast("long").alias("Year"),
        F.month("Month").cast("long").alias("MonthNumber"),
        F.months_between("Month", F.lit("2000-01-01")).cast("long").alias("MonthIndex"),
    )
    save_small("months", months)
    save_small("axis", months)
    kinds = spark.createDataFrame(
        [("FY", 0), ("YTD", 1), ("YTG", 2)], "PeriodType string, KindOrder long"
    )
    periods = (
        months.select("Year")
        .distinct()
        .crossJoin(kinds)
        .select(
            "Year",
            "PeriodType",
            F.concat_ws(":", F.col("Year").cast("string"), "PeriodType").alias(
                "PeriodKey"
            ),
            F.concat_ws(" ", F.col("Year").cast("string"), "PeriodType").alias("Label"),
            (F.col("Year") * 3 + F.col("KindOrder")).alias("SortIndex"),
        )
    )
    save_small("periods", periods)
    base_series = spark.createDataFrame(
        [
            ("actual", "ACTUAL", "", "Actuals · reference", 0),
            ("trend12", "TREND12", "", "Trend 12M", 1),
            ("trend24", "TREND24", "", "Trend 24M", 2),
        ],
        "SeriesID string, SeriesKind string, SourceRevisionID string, SeriesLabel string, SortIndex long",
    )
    plans = (
        files.select(
            F.concat(F.lit("plan:"), "SourceRevisionID").alias("SeriesID"),
            F.lit("PLAN").alias("SeriesKind"),
            "SourceRevisionID",
            "FileLabel",
        )
        .withColumnRenamed("FileLabel", "SeriesLabel")
        .withColumn("SortIndex", F.lit(10).cast("long"))
    )
    save_small("series", base_series.unionByName(plans))
    save_small(
        "modes",
        spark.createDataFrame(
            [("Selected files", 0), ("Reference only", 1)],
            "Mode string, SortIndex long",
        ),
    )
    print(
        "Reporting helpers ready:",
        *[
            REPORT_PREFIX + "_" + s
            for s in (
                "facts",
                "files",
                "reference",
                "measures",
                "months",
                "axis",
                "periods",
                "series",
                "modes",
            )
        ],
        sep="\n",
    )
    print(
        "Reporting helpers updated. Existing report relationships and measures are reused."
    )
    save_small("files", files)
    engine.replace_snapshot(
        state_name,
        spark.createDataFrame(
            [(report_signature, utc_now())], "Signature string, CompletedAtUtc string"
        ),
        ["Signature"],
    )
    engine.report_changed = True
    print("Selectable report files:", len(source_rows), flush=True)
    return True
