"""History survives cleanup without scanning large source tables or purging files."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
import run as refresh_run
from fast_refresh import FastRefresh


class NoStorageAccess:
    def __getattr__(self, name):
        raise AssertionError("Preservation must not access Spark storage: " + name)


def engine_with_revisions():
    engine = FastRefresh(
        NoStorageAccess(),
        {"CONTRACT": "synthetic"},
        {
            "TABLE_PREFIX": "test",
            "SOURCE_ROOT": "Files/Demand",
            "ALLOWED_PROFILES": ["Ext"],
        },
    )
    engine.completed = {
        "old": {"SourceRevisionID": "old", "NumericZero": 0, "Unavailable": None},
        "current": {"SourceRevisionID": "current", "Value": 100},
        "retired-path": {"SourceRevisionID": "retired-path", "Value": 50},
    }
    return engine


def test_compatibility_cleanup_retains_old_current_and_retired_revisions():
    engine = engine_with_revisions()
    before = deepcopy(engine.completed)
    assert engine.compact_current_sources() == {}
    assert engine.completed == before
    assert not engine.writes
    assert engine.compact_current_sources() == {}
    assert engine.completed == before


def test_storage_maintenance_never_opens_or_purges_delta_tables():
    engine = engine_with_revisions()
    before = deepcopy(engine.completed)
    engine.maintain_storage()
    assert engine.completed == before
    assert not engine.writes


def test_summary_distinguishes_retained_history_from_current_report_selection():
    engine = engine_with_revisions()
    summary = engine.summary()
    assert summary["StoragePolicy"] == "RETAIN_IMPORTED_REVISIONS"
    assert summary["ReportSelectionPolicy"] == "CURRENT_FILE_PER_PATH"


@pytest.mark.parametrize("report_changed", [False, True])
def test_successful_runtime_keeps_history_after_reporting_and_model_confirmation(
    monkeypatch, report_changed
):
    engine = engine_with_revisions()
    before = deepcopy(engine.completed)
    stages = []
    engine.report_changed = report_changed
    engine.ingest = lambda: stages.append("ingestion")
    original_preserve = engine.compact_current_sources

    def preserve():
        stages.append("preservation")
        return original_preserve()

    engine.compact_current_sources = preserve
    monkeypatch.setattr(refresh_run, "FastRefresh", lambda *args: engine)
    monkeypatch.setattr(
        refresh_run, "update_catalog", lambda *args: stages.append("catalog")
    )
    monkeypatch.setattr(
        refresh_run, "update_reporting", lambda *args: stages.append("reporting")
    )

    def refresh_model(*args):
        stages.append("model")
        return {"Status": "COMPLETED"}

    monkeypatch.setattr(refresh_run, "refresh_model", refresh_model)
    spark = SimpleNamespace(
        conf=SimpleNamespace(get=lambda key: "2", set=lambda *args: None)
    )
    utils = SimpleNamespace(
        credentials=SimpleNamespace(getToken=lambda key: "synthetic")
    )
    result, summary = refresh_run.run_refresh(spark, {}, {}, utils, "synthetic rules")
    assert result is engine and summary["Status"] == "SUCCESS"
    assert engine.completed == before and not engine.writes
    assert stages == ["ingestion", "catalog", "reporting"] + (
        ["model"] if report_changed else []
    ) + ["preservation"]
    assert summary["ModelRefresh"]["Status"] == (
        "COMPLETED" if report_changed else "UNCHANGED"
    )
