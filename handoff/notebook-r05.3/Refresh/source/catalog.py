"""Versioned measure catalog. Source value semantics are unchanged."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pyspark.sql import functions as F
from pyspark.sql import types as T


def update_catalog(engine: Any) -> bool:
    spark = engine.spark
    TABLE_PREFIX = engine.prefix
    normalize_catalog = engine.reader["normalize_catalog"]
    MEASURE_CATALOG_TABLE = engine.config.get("MEASURE_CATALOG_TABLE", "")
    MEASURE_CATALOG_FILE = engine.config.get(
        "MEASURE_CATALOG_FILE", "Files/ForecastMasterControls/MeasureCatalog.csv"
    )
    CONFIGURATIONS = TABLE_PREFIX + "_measure_configuration_snapshots"
    try:
        if MEASURE_CATALOG_TABLE:
            config_source = spark.table(MEASURE_CATALOG_TABLE)
        else:
            config_source = (
                spark.read.option("header", True)
                .option("mode", "FAILFAST")
                .option("multiLine", True)
                .option("escape", chr(34))
                .csv(MEASURE_CATALOG_FILE)
            )
        input_rules = [r.asDict() for r in config_source.toLocalIterator()]
        rules = normalize_catalog(input_rules)
        configuration_id = hashlib.sha256(
            json.dumps(rules, sort_keys=True, ensure_ascii=False, default=str).encode(
                "utf-8"
            )
        ).hexdigest()
        signature = hashlib.sha256(
            json.dumps(
                [
                    configuration_id,
                    sorted(r["RawSourceRevisionID"] for r in engine.report_sources()),
                ],
                sort_keys=True,
            ).encode()
        ).hexdigest()
        state_name = TABLE_PREFIX + "_catalog_refresh_state"
        if (
            spark.catalog.tableExists(state_name)
            and spark.catalog.tableExists(TABLE_PREFIX + "_measure_assignments")
        ) and {r[0] for r in spark.table(state_name).select("Signature").collect()} == {
            signature
        }:
            print(
                "Measure catalog and completed sources unchanged: assignments reused.",
                flush=True,
            )
            return False
        known = [
            "MeasureKey",
            "SourceSection",
            "SourceMeasure",
            "DisplayName",
            "ReportingEnabled",
            "EffectiveFromCycle",
            "EffectiveToCycle",
            "ValueRole",
            "Unit",
            "AggregationRule",
            "ComparisonRule",
            "DefinitionStatus",
            "Owner",
            "ChangeReason",
            "RawConfigurationJson",
            "CanonicalSection",
            "Family",
            "Dependency",
        ]
        config_names = ["ConfigurationID", "CapturedAtUtc", *known]
        config_schema = T.StructType(
            [T.StructField(name, T.StringType(), True) for name in config_names]
        )
        captured = datetime.now(UTC).isoformat()
        config_rows = [
            [configuration_id, captured, *[r.get(name, "") for name in known]]
            for r in rules
        ]
        if not spark.catalog.tableExists(CONFIGURATIONS):
            spark.createDataFrame([], config_schema).write.format("delta").mode(
                "errorifexists"
            ).saveAsTable(CONFIGURATIONS)
        if (
            not spark.table(CONFIGURATIONS)
            .where(F.col("ConfigurationID") == configuration_id)
            .limit(1)
            .count()
        ):
            spark.createDataFrame(config_rows, config_schema).write.format(
                "delta"
            ).mode("append").saveAsTable(CONFIGURATIONS)
        print("Configuration snapshot:", configuration_id, "Rules:", len(rules))
        complete_sources = (
            spark.table(TABLE_PREFIX + "_file_state")
            .select("SourceRevisionID")
            .distinct()
        )
        source_measures = (
            spark.table(TABLE_PREFIX + "_source_measures")
            .join(complete_sources, "SourceRevisionID", "inner")
            .alias("h")
        )
        config = (
            spark.table(CONFIGURATIONS)
            .where(F.col("ConfigurationID") == configuration_id)
            .alias("c")
        )
        match = (
            (F.col("h.MeasureKey") == F.col("c.MeasureKey"))
            & (F.col("h.DemandCycle") >= F.col("c.EffectiveFromCycle"))
            & (F.col("h.DemandCycle") <= F.col("c.EffectiveToCycle"))
        )
        fields = [
            "DisplayName",
            "ReportingEnabled",
            "Family",
            "Dependency",
            "ValueRole",
            "AggregationRule",
            "ComparisonRule",
            "Unit",
            "EffectiveFromCycle",
            "EffectiveToCycle",
            "DefinitionStatus",
            "Owner",
            "ChangeReason",
        ]
        assignments = source_measures.join(config, match, "left").select(
            "h.*",
            *[F.col("c." + name) for name in fields],
            F.lit(configuration_id).alias("ConfigurationID"),
            F.when(F.col("c.MeasureKey").isNull(), "UNMAPPED")
            .otherwise("MAPPED")
            .alias("CatalogState"),
        )
        engine.replace_snapshot(
            TABLE_PREFIX + "_measure_assignments", assignments, ["SourceMeasureID"]
        )
        discovered = source_measures.select(
            "MeasureKey", "Section", "Measure"
        ).distinct()
        configured = spark.createDataFrame(
            [[r["MeasureKey"]] for r in rules],
            T.StructType([T.StructField("MeasureKey", T.StringType(), False)]),
        ).distinct()
        print(
            "Unmapped source measure identities:",
            discovered.join(configured, "MeasureKey", "left_anti").count(),
            flush=True,
        )
        engine.replace_snapshot(
            state_name,
            spark.createDataFrame(
                [(signature, datetime.now(UTC).isoformat())],
                "Signature string, CompletedAtUtc string",
            ),
            ["Signature"],
        )
        return True
    except Exception as error:
        print("Measure configuration was not captured:", str(error))
        print(
            "Raw bridge history remains available. Supply or correct the List/CSV connection before accepting configured reporting."
        )
        raise
