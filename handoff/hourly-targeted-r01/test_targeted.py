"""Executable scope, retry and receipt-write regression checks; no Fabric access."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'candidate/Refresh/source'
NAME = 'UK_Example_Bridge_Jul 26_EF-Jun 26_IMS-May 26_ADS.xlsm'
A = '2026/07 Jul 26/Bridge Files/' + NAME
B = '2025/History/' + NAME


class WorkerRefreshError(RuntimeError):
    pass


def load_hourly():
    tree = ast.parse((SRC / 'hourly_worker.py').read_text(encoding="utf-8"))
    tree.body = [n for n in tree.body if not isinstance(n,(ast.Import,ast.ImportFrom))]
    ns = dict(hashlib=hashlib,json=json,re=re,Callable=Any,datetime=datetime,UTC=UTC,
              Any=Any,uuid4=uuid4,WorkerRefreshError=WorkerRefreshError,
              queue_utc=lambda: datetime.now(UTC).isoformat())
    exec(compile(tree,'hourly_worker.py','exec'),ns)
    return ns


H = load_hourly()


def rows():
    return [dict(Path=p,Bytes=10,ModifiedAtUtc='2026-10-19T12:00:00+00:00',ETag='v1') for p in (A,B)]


def snapshot(items=None, hour=13):
    items = rows() if items is None else items
    return dict(SchemaVersion=1,SourceRoot='Files/Demand',CapturedAtUtc=f'2026-10-19T{hour:02d}:00:00+00:00',
                Fingerprint=H['metadata_fingerprint'](items),Files=copy.deepcopy(items))


def baseline(items=None):
    return dict(**snapshot(items),Status='SUCCESS',RefreshRunID='before')


@pytest.mark.parametrize('old',[None,{},[],{'SchemaVersion':0},dict(baseline(),Fingerprint='bad')])
def test_missing_or_invalid_baseline_uses_all(old):
    plan=H['hourly_refresh_plan'](snapshot(hour=14),old)
    assert plan['Mode']=='ALL' and plan['ChangedFiles']==[B,A]


@given(st.integers(min_value=1,max_value=1000))
def test_historical_etag_correction_targets_only_its_exact_path(version):
    items=rows();items[1]['ETag']='v'+str(version+1)
    plan=H['hourly_refresh_plan'](snapshot(items,hour=14),baseline())
    assert plan==dict(Mode='FILES',ChangedFiles=[B],RemovedFiles=[])


def test_added_path_uses_files():
    items=rows()+[dict(rows()[0],Path='new/'+NAME)]
    plan=H['hourly_refresh_plan'](snapshot(items,hour=14),baseline())
    assert plan['Mode']=='FILES' and plan['ChangedFiles']==['new/'+NAME]


def test_removed_and_renamed_paths_use_all():
    plan=H['hourly_refresh_plan'](snapshot(rows()[:1],hour=14),baseline())
    assert plan['Mode']=='ALL' and plan['ChangedFiles']==[] and plan['RemovedFiles']==[B.casefold()]
    items=rows();items[1]['Path']='renamed/'+NAME
    assert H['hourly_refresh_plan'](snapshot(items,hour=14),baseline())['Mode']=='ALL'


def test_unchanged_skips_and_stale_snapshot_fails():
    assert H['hourly_refresh_plan'](snapshot(hour=14),baseline()) is None
    items=rows();items[0]['ETag']='old'
    with pytest.raises(ValueError,match='stale'):
        H['hourly_refresh_plan'](snapshot(items,hour=12),baseline())


def processed(items, mode='ALL', selected=None):
    return SimpleNamespace(config=dict(REFRESH_MODE=mode,SELECTED_RELATIVE_PATHS=selected or []),
       discovery_metadata=[dict(relative=r['Path'],size=r['Bytes'],modified=r['ModifiedAtUtc']) for r in items],
       events=[dict(SourceRelativePath=r['Path'],Status='SUCCEEDED') for r in items])


def test_files_validation_expects_only_selected_not_the_full_inventory():
    H['validate_processed_snapshot'](processed(rows()[1:],'FILES',[B]),snapshot())
    with pytest.raises(ValueError,match='paths changed'):
        H['validate_processed_snapshot'](processed(rows(),'FILES',[B]),snapshot())
    bad=processed(rows()[1:],'FILES',[B]);bad.discovery_metadata[0]['size']=11
    with pytest.raises(ValueError,match='changed after'):
        H['validate_processed_snapshot'](bad,snapshot())


class Store:
    def __init__(self):
        self.values={};self.held=False;self.fail='';self.writes=[]
    def acquire(self):
        self.held=True;return True
    def release(self):
        self.held=False
    def read(self,name):
        return copy.deepcopy(self.values.get(name))
    def write(self,name,value):
        if name==self.fail: raise OSError('injected')
        self.values[name]=copy.deepcopy(value);self.writes.append(name)


def success():
    return dict(Status='SUCCESS',RunID='after',StageErrors=[],FileResults={},ModelRefresh={'Status':'COMPLETED'})


@pytest.mark.parametrize('fail',['latest.json','metadata-success.json','partial','model','validation'])
def test_failed_stages_and_receipts_retain_baseline_and_release_lease(fail):
    store=Store();old=baseline();store.values['metadata-success.json']=old
    store.fail=fail
    items=rows();items[1]['ETag']='v2'
    s=success();e=processed(items[1:],'FILES',[B])
    if fail=='partial': s['Status']='PARTIAL'
    if fail=='model': s['ModelRefresh']['Status']='FAILED'
    if fail=='validation': e.discovery_metadata[0]['size']=99
    worker=H['HourlyWorker'](SimpleNamespace(mkdirs=lambda _:True),store,'state')
    with pytest.raises((OSError,WorkerRefreshError,ValueError)):
        worker.run(snapshot(items,hour=14),lambda plan:(e,s))
    assert store.values['metadata-success.json']==old and not store.held


def test_success_writes_metadata_pointer_last():
    store=Store();store.values['metadata-success.json']=baseline()
    items=rows();items[1]['ETag']='v2'
    worker=H['HourlyWorker'](SimpleNamespace(mkdirs=lambda _:True),store,'state')
    worker.run(snapshot(items,hour=14),lambda plan:(processed(items[1:],'FILES',[B]),success()))
    assert store.writes[-1]=='metadata-success.json' and not store.held


def test_invalid_ingestion_index_falls_back_without_workbook_reads():
    config={'TABLE_PREFIX':'test'}
    assert not H['targeted_index_valid'](SimpleNamespace(catalog=SimpleNamespace(tableExists=lambda _:False)),config,snapshot(),[B],'contract')
    pointers=[dict(SourceRelativePath=A,ReaderContract='contract',SourceRevisionID='sha',SourceBytes='10',SourceModifiedAt=rows()[0]['ModifiedAtUtc'])]
    class Spark:
        catalog=SimpleNamespace(tableExists=lambda _:True)
        def table(self,name):
            if name.endswith('_source_revisions'):
                return SimpleNamespace(select=lambda _:SimpleNamespace(collect=lambda:[('sha',)]))
            return SimpleNamespace(collect=lambda:pointers)
    assert H['targeted_index_valid'](Spark(),config,snapshot(),[B],'contract')
    pointers[0]['SourceBytes']='99'
    assert not H['targeted_index_valid'](Spark(),config,snapshot(),[B],'contract')


def test_detector_invalid_baseline_still_starts_reconciliation():
    ns={};exec((ROOT/'candidate/detector_helpers.py').read_text(encoding="utf-8"),ns)
    discovery=dict(Status='METADATA_VISIBLE',CompleteDirectoryListing=True,Files=rows(),MatchingBridgeFiles=2,MissingMetadataPaths=[])
    for old in (None,{},dict(baseline(),Fingerprint='bad')):
        decision=ns['prepareMetadataDecision'](discovery,old)
        assert decision['Status']=='BASELINE_REQUIRED' and decision['NeedsRefresh']


class Engine:
    def __init__(self,*args):
        self.completed={'sha':{}};self.stage_errors=[];self.failed_files=0;self.report_changed=False;self.report_signature='s1'
    def ingest(self): pass
    @contextmanager
    def stage(self,*args): yield
    def compact_current_sources(self): pass
    def summary(self): return dict(Status='PARTIAL' if self.stage_errors or self.failed_files else 'SUCCESS',StageErrors=self.stage_errors)


def runtime(store, signature='s1', model_status='COMPLETED', failed_files=0):
    tree=ast.parse((SRC/'run.py').read_text(encoding="utf-8"))
    tree.body=[n for n in tree.body if not isinstance(n,(ast.Import,ast.ImportFrom))]
    engine=Engine();engine.failed_files=failed_files;engine.report_signature=signature
    calls=[]
    ns=dict(json=json,Any=Any,FastRefresh=lambda *args:engine,update_catalog=lambda *args:None,
            update_reporting=lambda *args:False,
            refresh_model=lambda *args:(calls.append('model') or dict(Status=model_status)))
    exec(compile(tree,'run.py','exec'),ns)
    config=dict(MODEL_STATE_STORE=store,WORKSPACE_ID='workspace',SEMANTIC_MODEL_ID='model',REPORT_PREFIX='report')
    spark=SimpleNamespace(conf=SimpleNamespace(get=lambda _:8,set=lambda *args:None))
    utils=SimpleNamespace(credentials=SimpleNamespace(getToken=lambda _:'test'))
    _,result=ns['run_refresh'](spark,{},config,utils,'rules')
    return result,calls


def test_model_retry_after_reporting_commit_and_unchanged_skip():
    store=Store()
    result,calls=runtime(store,model_status='FAILED')
    assert calls==['model'] and 'model-success.json' not in store.values and result['Status']=='PARTIAL'
    result,calls=runtime(store)
    assert calls==['model'] and result['Status']=='SUCCESS'
    result,calls=runtime(store)
    assert calls==[] and result['ModelRefresh']['Status']=='UNCHANGED'
    result,calls=runtime(store,signature='s2')
    assert calls==['model']


def test_model_marker_write_failure_remains_retryable():
    store=Store();store.fail='model-success.json'
    assert runtime(store)[0]['Status']=='PARTIAL'
    store.fail=''
    assert runtime(store)[1]==['model']


def test_partial_ingestion_never_refreshes_model():
    assert runtime(Store(),failed_files=1)[1]==[]


def test_notebook_only_four_cells_change_and_retains_revision_and_slice_logic():
    before=json.loads((ROOT.parent / 'notebook-r05.4/ForecastMaster_Refresh.ipynb').read_text(encoding="utf-8"))
    after=json.loads((ROOT/'candidate/ForecastMaster_Refresh.ipynb').read_text(encoding="utf-8"))
    assert [i for i,(a,b) in enumerate(zip(before['cells'],after['cells'],strict=True)) if a!=b]==[4,8,10,12]
    assert 'replaceWhere' in ''.join(after['cells'][8]['source'])
    assert 'RETAIN_IMPORTED_REVISIONS' in ''.join(after['cells'][6]['source'])
    for cell in after['cells']:
        if cell['cell_type']=='code': compile(''.join(cell['source']),'cell','exec')


def test_detector_missing_timestamp_and_bool_schema_cannot_skip_recovery():
    ns={};exec((ROOT/'candidate/detector_helpers.py').read_text(encoding="utf-8"),ns)
    discovery=dict(Status='METADATA_VISIBLE',CompleteDirectoryListing=True,Files=rows(),MatchingBridgeFiles=2,MissingMetadataPaths=[])
    missing=baseline();missing.pop('CapturedAtUtc')
    for old in (missing,dict(baseline(),SchemaVersion=True)):
        assert ns['prepareMetadataDecision'](discovery,old)['Status']=='BASELINE_REQUIRED'


def test_exact_notebook_callback_selects_files_all_and_manual_rebuild():
    source=(ROOT/'candidate/build/execute_cell.txt').read_text(encoding="utf-8")
    tree=ast.parse(source)
    func=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='requested_refresh')
    keys=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='config_keys' for t in n.targets))
    ns=dict(fm_mode='HOURLY',fm_hourly_snapshot=snapshot(),targeted_index_valid=lambda *args:True,
            CONTRACT='test',spark=object(),notebookutils=object(),EMBEDDED_REPORT_RULES='rules',worker_store=Store())
    exec(compile(ast.Module(body=[keys],type_ignores=[]),'keys','exec'),ns)
    ns.update({k:False for k in ns['config_keys']})
    ns['run_refresh']=lambda spark,reader,config,utils,rules:config
    exec(compile(ast.Module(body=[func],type_ignores=[]),'callback','exec'),ns)
    plan=dict(Mode='FILES',ChangedFiles=[B],RemovedFiles=[])
    result=ns['requested_refresh'](plan)
    assert result['REFRESH_MODE']=='FILES' and result['SELECTED_RELATIVE_PATHS']==[B]
    assert result['FORCE_REHASH_PATHS']==[B] and result['FORCE_MODEL_REFRESH'] is False
    ns['targeted_index_valid']=lambda *args:False
    assert ns['requested_refresh'](plan)['REFRESH_MODE']=='ALL'
    ns['targeted_index_valid']=lambda *args:True
    ns['FORCE_REBUILD_REPORTING_FACTS']=True
    assert ns['requested_refresh'](plan)['REFRESH_MODE']=='ALL'
    ns['FORCE_REBUILD_REPORTING_FACTS']=False
    ns['fm_mode']='REQUESTS'
    assert ns['requested_refresh']()['REFRESH_MODE']=='ALL'


def test_actual_discovery_loads_only_selected_file_paths():
    source=(ROOT.parent / 'notebook-r05.4/Refresh/source/fast_refresh.py').read_text(encoding="utf-8")
    cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='FastRefresh')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='discover')
    seen=[]
    class Reader:
        def format(self,*args): return self
        def option(self,*args): return self
        def load(self,roots): seen.append(roots);return self
        def select(self,*args): return self
        def collect(self): return [object()]
    ns={'Any':Any,'FILE_GLOB':'pattern','filename_candidate':lambda _:True}
    exec(compile(ast.Module(body=[method],type_ignores=[]),'discover','exec'),ns)
    e=SimpleNamespace(config=dict(REFRESH_MODE='FILES',SELECTED_RELATIVE_PATHS=[B]),root='Files/Demand',
      spark=SimpleNamespace(read=Reader()),_metadata=lambda _:dict(path='uri',relative=B,name=NAME))
    assert len(ns['discover'](e))==1
    assert seen==[['Files/Demand/'+B]]


def test_metadata_only_stamp_does_not_change_report_signature():
    tree=ast.parse((SRC/'reporting.py').read_text(encoding="utf-8"))
    func=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='update_reporting')
    signature=next(n for n in func.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='report_signature' for t in n.targets))
    ns=dict(hashlib=hashlib,json=json,raw_rules=[{'MetricKey':'fact'}],engine=SimpleNamespace(allowed={'Ext'}),
       source_rows=[dict(RawSourceRevisionID='sha',SourceRevisionID='path-id',PathFirstSeenAtUtc='first')])
    code=compile(ast.Module(body=[signature],type_ignores=[]),'signature','exec')
    exec(code,ns);original=ns['report_signature']
    ns['source_rows'][0]['PathFirstSeenAtUtc']='later'
    exec(code,ns);assert ns['report_signature']==original
    ns['source_rows'][0]['RawSourceRevisionID']='corrected-sha'
    exec(code,ns);assert ns['report_signature']!=original


@pytest.mark.parametrize('failure',[TypeError('wrong JSON root'),json.JSONDecodeError('bad','',0)])
def test_malformed_stored_baseline_falls_back_to_all(failure):
    class MalformedStore(Store):
        def read(self,name):
            if name=='metadata-success.json': raise failure
            return super().read(name)
    store=MalformedStore()
    worker=H['HourlyWorker'](SimpleNamespace(mkdirs=lambda _:True),store,'state')
    captured=[]
    def refresh(plan):
        captured.append(plan)
        return processed(rows()),success()
    worker.run(snapshot(),refresh)
    assert captured[0]['Mode']=='ALL' and not store.held
