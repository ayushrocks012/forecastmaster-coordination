"""Single ordered invocation for the embedded Fabric notebook."""

import json
from typing import Any



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
        if engine.completed and not engine.failed_files and not engine.stage_errors:
            try:
                with engine.stage("Update measure catalog"):
                    update_catalog(engine)
            except Exception as exc:  # noqa: BLE001 -- retain stage diagnostics and surface failure
                engine.stage_errors.append("Catalog: " + str(exc))
            try:
                if engine.stage_errors:
                    raise RuntimeError("Catalog update failed; reporting/model deferred")
                with engine.stage("Update changed reporting projections"):
                    update_reporting(engine, embedded_rules)
                # A reporting commit is not proof that its model refresh completed.
                # The marker advances only after confirmed completion, so retry even
                # if update_reporting() finds the already-committed tables unchanged.
                store = config["MODEL_STATE_STORE"]
                identity = {"Signature": engine.report_signature,
                            "WorkspaceID": config["WORKSPACE_ID"],
                            "ModelID": config["SEMANTIC_MODEL_ID"],
                            "ReportPrefix": config["REPORT_PREFIX"]}
                try:
                    confirmed = store.read("model-success.json")
                except (TypeError, ValueError, UnicodeDecodeError):
                    confirmed = None
                if confirmed != identity:
                    with engine.stage("Refresh ForecastMaster Demand Model"):
                        model_result = refresh_model(
                            config, notebookutils.credentials.getToken
                        )
                    if model_result["Status"] != "COMPLETED":
                        engine.stage_errors.append(
                            "Model refresh: " + json.dumps(model_result)
                        )
                    else:
                        store.write("model-success.json", identity)
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
                with engine.stage("Preserve imported source revisions"):
                    engine.compact_current_sources()
            except Exception as exc:  # noqa: BLE001 -- report retention failure honestly
                engine.stage_errors.append("History preservation: " + str(exc))
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
