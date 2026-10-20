"""Single ordered invocation for the embedded Fabric notebook."""

import json
from typing import Any

from catalog import update_catalog
from fast_refresh import FastRefresh
from model_refresh import refresh_model
from reporting import update_reporting


def run_refresh(
    spark: Any,
    reader_namespace: dict[str, Any],
    config: dict[str, Any],
    notebookutils: Any,
    embedded_rules: str,
) -> tuple[FastRefresh, dict[str, Any]]:
    engine = FastRefresh(spark, reader_namespace, config)
    old_shuffle = spark.conf.get("spark.sql.shuffle.partitions")
    spark.conf.set(
        "spark.sql.shuffle.partitions", str(config.get("SHUFFLE_PARTITIONS", 8))
    )
    model_result = {"Status": "NOT_REQUESTED"}
    try:
        try:
            engine.ingest()
        except Exception as exc:  # noqa: BLE001 -- retain stage diagnostics and surface failure
            engine.stage_errors.append("Ingestion: " + str(exc))
            print("Ingestion stage failed:", str(exc), flush=True)
        if engine.completed:
            try:
                with engine.stage("Update measure catalog"):
                    update_catalog(engine)
            except Exception as exc:  # noqa: BLE001 -- retain stage diagnostics and surface failure
                engine.stage_errors.append("Catalog: " + str(exc))
            try:
                with engine.stage("Update changed reporting projections"):
                    update_reporting(engine, embedded_rules)
                if engine.report_changed or config.get("FORCE_MODEL_REFRESH", False):
                    with engine.stage("Refresh ForecastMaster Demand Model"):
                        model_result = refresh_model(
                            config, notebookutils.credentials.getToken
                        )
                    if model_result["Status"] != "COMPLETED":
                        engine.stage_errors.append(
                            "Model refresh: " + json.dumps(model_result)
                        )
                else:
                    model_result = {
                        "Status": "UNCHANGED",
                        "Message": "Report tables unchanged; no model refresh needed.",
                    }
            except Exception as exc:  # noqa: BLE001 -- retain stage diagnostics and surface failure
                engine.stage_errors.append("Reporting/model refresh: " + str(exc))
                print("Reporting/model stage:", str(exc), flush=True)
        if (
            model_result["Status"] in {"COMPLETED", "UNCHANGED"}
            and not engine.stage_errors
        ):
            try:
                with engine.stage("Compact superseded file data"):
                    engine.compact_current_sources()
            except Exception as exc:  # noqa: BLE001 -- report retention failure honestly
                engine.stage_errors.append("Current-file compaction: " + str(exc))
        summary = engine.summary()
        summary["ModelRefresh"] = model_result
        print(json.dumps(summary, indent=2), flush=True)
        if summary["Status"] == "SUCCESS":
            print(
                "Refresh complete. In Power BI Desktop, refresh the report to retrieve the updated model results.",
                flush=True,
            )
        else:
            print(
                "PARTIAL: inspect FAILED file rows and StageErrors. Successful existing sources remain available.",
                flush=True,
            )
        return engine, summary
    finally:
        spark.conf.set("spark.sql.shuffle.partitions", old_shuffle)
