"""Build an isolated R05.4 patch for review; never install or edit the input."""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'notebook-r05.4'
OUT = ROOT / 'candidate'


def once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError('Unexpected preimage: ' + old[:100])
    return text.replace(old, new)


PLAN = '''def hourly_refresh_plan(snapshot: dict[str, Any], baseline: Any) -> dict[str, Any] | None:
    """Choose scope again under the existing lease, using the committed baseline."""
    try:
        checked_snapshot(baseline)
        if baseline.get("Status") != "SUCCESS" or not baseline.get("RefreshRunID"):
            raise ValueError("Invalid committed baseline")
    except (KeyError, TypeError, ValueError):
        baseline = None
    changed = hourly_changes(snapshot, baseline)
    if changed is None:
        return None
    removed = sorted(set(metadata_inventory(baseline["Files"]))
                     - set(metadata_inventory(snapshot["Files"]))) if baseline else []
    mode = "ALL" if baseline is None or removed else "FILES"
    return {"Mode": mode, "ChangedFiles": changed, "RemovedFiles": removed}


def targeted_index_valid(spark: Any, config: dict[str, Any], snapshot: dict[str, Any],
                         changed: list[str], contract: str) -> bool:
    """Only compact metadata: untouched paths must already have complete pointers."""
    prefix = config["TABLE_PREFIX"]
    if not all(spark.catalog.tableExists(prefix + suffix)
               for suffix in ("_file_state", "_source_revisions")):
        return False
    expected = metadata_inventory(snapshot["Files"])
    changed_keys = {path.casefold() for path in changed}
    complete = {r[0] for r in spark.table(prefix + "_source_revisions")
                .select("SourceRevisionID").collect()}
    found = set()
    try:
        for row in spark.table(prefix + "_file_state").collect():
            key = row["SourceRelativePath"].casefold()
            if (key in found or key not in expected or row["ReaderContract"] != contract
                    or row["SourceRevisionID"] not in complete):
                return False
            found.add(key)
            if key not in changed_keys:
                modified = datetime.fromisoformat(row["SourceModifiedAt"])
                if modified.utcoffset() is None:
                    modified = modified.replace(tzinfo=UTC)
                if (int(row["SourceBytes"]) != expected[key]["Bytes"]
                        or modified.astimezone(UTC).isoformat() != expected[key]["ModifiedAtUtc"]):
                    return False
    except (KeyError, TypeError, ValueError):
        return False
    return set(expected) - changed_keys <= found


'''

EXECUTE = '''def requested_refresh(plan=None):
    refresh_config = {key: globals()[key] for key in config_keys}
    mode = plan["Mode"] if fm_mode == "HOURLY" else "ALL"
    changed = plan["ChangedFiles"] if fm_mode == "HOURLY" else []
    # A missing/broken ingestion index cannot safely serve a partial inventory.
    if mode == "FILES" and not targeted_index_valid(
        spark, refresh_config, fm_hourly_snapshot, changed,
        CONTRACT + "|affiliate-bridge-cycle-ef-ims-any-suffix-v1",
    ):
        mode = "ALL"
    if FORCE_REBUILD_REPORTING_FACTS or FORCE_REHASH:
        mode = "ALL"
    refresh_config.update(
        SOURCE_ROOT="Files/Demand", REFRESH_MODE=mode,
        SELECTED_RELATIVE_PATHS=changed if mode == "FILES" else [],
        ALLOWED_PROFILES=["Local", "Ext"], REFRESH_SEMANTIC_MODEL=True,
        FORCE_MODEL_REFRESH=False, FORCE_REHASH_PATHS=changed,
        MODEL_STATE_STORE=worker_store,
    )
    return run_refresh(spark, globals(), refresh_config, notebookutils, EMBEDDED_REPORT_RULES)
'''


def build() -> None:
    if OUT.exists():
        raise FileExistsError(OUT)
    (OUT / 'Refresh/source').mkdir(parents=True)
    (OUT / 'build').mkdir()
    diffs = []
    sources = {}
    for name in ('hourly_worker', 'reporting', 'run'):
        original = (BASE / 'Refresh/source' / (name + '.py')).read_text(encoding="utf-8")
        text = original
        if name == 'hourly_worker':
            text = once(text, 'def validate_processed_snapshot(', PLAN + 'def validate_processed_snapshot(')
            text = once(text, '    expected = metadata_inventory(snapshot["Files"])\n    found:', '''    expected = metadata_inventory(snapshot["Files"])
    config = getattr(engine, "config", {})
    if config.get("REFRESH_MODE", "ALL") == "FILES":
        selected = {p.casefold() for p in config["SELECTED_RELATIVE_PATHS"]}
        if not selected or not selected <= set(expected):
            raise ValueError("Invalid selected snapshot scope")
        expected = {key: row for key, row in expected.items() if key in selected}
    found:''')
            text = once(text, 'refresh: Callable[[list[str]], tuple[Any, dict[str, Any]]]', 'refresh: Callable[[dict[str, Any]], tuple[Any, dict[str, Any]]]')
            text = once(text, '            changed = hourly_changes(snapshot, self.store.read("metadata-success.json"))\n            if changed is None:', '''            try:
                baseline = self.store.read("metadata-success.json")
            except (TypeError, ValueError, UnicodeDecodeError):
                baseline = None
            plan = hourly_refresh_plan(snapshot, baseline)
            if plan is None:''')
            text = once(text, '                len(changed),', '                len(plan["ChangedFiles"]),')
            text = once(text, '            engine, summary = refresh(changed)', '            engine, summary = refresh(plan)')
            text = once(text, '"ContentChecksRequested": len(changed),', '''"ContentChecksRequested": len(plan["ChangedFiles"]),
                "RefreshMode": engine.config["REFRESH_MODE"],''')
            text = once(text, '''            self.store.write("metadata-success.json", baseline)
            self.store.write("latest.json", result)''', '''            self.store.write("latest.json", result)
            self.store.write("metadata-success.json", baseline)''')
        elif name == 'reporting':
            text = once(text, '                "sources": source_rows,', '''                "sources": [{k: v for k, v in row.items() if k != "PathFirstSeenAtUtc"}
                            for row in source_rows],''')
            text = once(text, '    state_name = REPORT_PREFIX + "_refresh_state"', '''    engine.report_signature = report_signature
    state_name = REPORT_PREFIX + "_refresh_state"''')
            text = once(text, '        if signatures == {report_signature}:', '        if signatures == {report_signature} and not FORCE_REBUILD_REPORTING_FACTS:')
        else:
            text = once(text, '        if engine.completed:', '        if engine.completed and not engine.failed_files and not engine.stage_errors:')
            text = once(text, '''                with engine.stage("Update changed reporting projections"):
                    update_reporting(engine, embedded_rules)
                if engine.report_changed or config.get("FORCE_MODEL_REFRESH", False):''', '''                if engine.stage_errors:
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
                if confirmed != identity:''')
            text = once(text, '''                            "Model refresh: " + json.dumps(model_result)
                        )
                else:''', '''                            "Model refresh: " + json.dumps(model_result)
                        )
                    else:
                        store.write("model-success.json", identity)
                else:''')
        ast.parse(text)
        sources[name] = text
        (OUT / 'Refresh/source' / (name + '.py')).write_text(text, encoding="utf-8")
        diffs.append(''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
                     fromfile='R05.4/Refresh/source/' + name + '.py',
                     tofile='candidate/Refresh/source/' + name + '.py')))
    original = (BASE / 'build/execute_cell.txt').read_text(encoding="utf-8")
    start, end = original.index('def requested_refresh('), original.index('\nif fm_mode == "HOURLY":')
    execute = original[:start] + EXECUTE + original[end:]
    (OUT / 'build/execute_cell.txt').write_text(execute, encoding="utf-8")
    diffs.append(''.join(difflib.unified_diff(original.splitlines(True), execute.splitlines(True),
                 fromfile='R05.4/build/execute_cell.txt', tofile='candidate/build/execute_cell.txt')))
    notebook = json.loads((BASE / 'ForecastMaster_Refresh.ipynb').read_text(encoding="utf-8"))
    for index, name in ((8, 'reporting'), (10, 'run')):
        source = sources[name]
        if name == 'run':
            source = ''.join(line for line in source.splitlines(True)
                            if not line.startswith(('from catalog import ', 'from fast_refresh import ',
                                                    'from model_refresh import ', 'from reporting import ')))
        notebook['cells'][index]['source'] = source.splitlines(True)
    notebook['cells'][4]['source'] = (sources['hourly_worker'].replace(
        'from request_worker import WorkerRefreshError, queue_utc\n', '') + '\n' +
        (BASE / 'build/preflight_cell.txt').read_text(encoding="utf-8")).splitlines(True)
    notebook['cells'][12]['source'] = execute.splitlines(True)
    for index, cell in enumerate(notebook['cells']):
        if cell['cell_type'] == 'code':
            compile(''.join(cell['source']), f'cell-{index}', 'exec')
    (OUT / 'ForecastMaster_Refresh.ipynb').write_text(json.dumps(notebook, indent=1) + '\n', encoding="utf-8")
    (ROOT / 'minimal.patch').write_text(''.join(diffs), encoding="utf-8")
    manifest = {'InputNotebook': str(BASE / 'ForecastMaster_Refresh.ipynb'),
                'InputSHA256': hashlib.sha256((BASE / 'ForecastMaster_Refresh.ipynb').read_bytes()).hexdigest(),
                'ChangedNotebookCellIndices': [4, 8, 10, 12],
                'FabricInstallation': 'NOT_RUN', 'FabricCapacityMeasurement': 'NOT_RUN'}
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding="utf-8")


if __name__ == '__main__':
    build()
