"""Current-file policy: stable identities, replacement and deployable worker."""
from __future__ import annotations

import base64
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given, strategies as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Refresh/source'))
from fast_refresh import FastRefresh, report_identity, current_content_ids

spec = importlib.util.spec_from_file_location('r041_notebook_upgrade', ROOT / 'build/notebook_upgrade.py')
upgrade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upgrade)
NAME = 'UK_Core Oral_Bridge_Oct 26_EF-Sep 26_IMS-Aug 26_ADS.xlsm'


@given(st.lists(st.binary(min_size=1, max_size=40), min_size=1, max_size=100))
def test_arbitrary_edits_do_not_create_scenarios(contents):
    assert len({report_identity(value.hex(), 'My Work/' + NAME) for value in contents}) == 1
    assert report_identity('same bytes', 'My Work/' + NAME) != report_identity('same bytes', 'Scenarios/' + NAME)


def test_current_sources_never_expand_the_entire_import_history():
    class Row(dict):
        def asDict(self):
            return dict(self)
    rows = [Row(SourceRevisionID='sha-99', SourceRelativePath='My Work/' + NAME, SourcePath='file:one', LastSuccessAtUtc='2026-10-19T18:00:00Z'),
            Row(SourceRevisionID='sha-22', SourceRelativePath='Scenarios/' + NAME, SourcePath='file:two', LastSuccessAtUtc='2026-10-19T17:00:00Z')]
    class Spark:
        catalog = SimpleNamespace(tableExists=lambda name: name == 'test_file_state')
        def table(self, name):
            assert name == 'test_file_state', 'Never scan the event log to create file entries'
            return SimpleNamespace(collect=lambda: rows)
    engine = FastRefresh(Spark(), {'CONTRACT':'test'}, {'TABLE_PREFIX':'test', 'SOURCE_ROOT':'Files/Demand', 'ALLOWED_PROFILES':['Ext']})
    engine.completed = {'sha-'+str(i):dict(SourceRevisionID='sha-'+str(i), SourceRelativePath='My Work/'+NAME, SourceProfile='Ext') for i in range(100)}
    current = engine.report_sources()
    assert len(current) == 2
    assert {r['RawSourceRevisionID'] for r in current} == {'sha-99', 'sha-22'}
    assert len({r['SourceRevisionID'] for r in current}) == 2


class Response:
    status_code = 200
    headers = {}
    def __init__(self, value): self.value = value
    def json(self): return self.value


class Store:
    def __init__(self, acquire=True): self.available=acquire;self.writes=[];self.released=False
    def acquire(self): return self.available
    def release(self): self.released=True
    def write(self, name, value): self.writes.append((name,value))


class HTTP:
    def __init__(self):
        self.calls=[]
        self.definition={'format':'ipynb','parts':[{'path':'notebook-content.ipynb','payloadType':'InlineBase64','payload':base64.b64encode(json.dumps({'cells':[{'cell_type':'markdown','source':['old']}],'metadata':{'attachedLakehouse':'company-original'}}).encode()).decode()}]}
    def request(self, method, url, **kwargs):
        self.calls.append((method,url,kwargs))
        if url.endswith('/updateDefinition'):
            self.definition=kwargs['json']['definition'];return Response({})
        if url.endswith('/getDefinition?format=ipynb'):return Response({'definition':self.definition})
        assert method=='GET' and url.endswith(upgrade.ITEM)
        return Response({'displayName':'ForecastMaster_Refresh','id':upgrade.NOTEBOOK})


def test_installer_updates_existing_id_preserves_attachment_backup_and_releases_lease():
    http,store=HTTP(),Store()
    notebook={'metadata':{},'cells':[{'cell_type':'code','source':['result = 1\n']}]}
    upgrade.install(http,lambda _: 'synthetic-test-token',store,notebook)
    saved=upgrade.content(http.definition)
    assert saved['metadata']=={'attachedLakehouse':'company-original'}
    assert saved['cells']==notebook['cells']
    assert len(store.writes)==1 and store.released
    assert all('NotebookID' in value and value['NotebookID']==upgrade.NOTEBOOK for _,value in store.writes)
    assert sum(url.endswith('/updateDefinition') for _,url,_ in http.calls)==1
    assert not any('/schedules' in url or '/dataPipelines' in url or 'create' in url for _,url,_ in http.calls)


def test_busy_worker_prevents_notebook_update():
    http,store=HTTP(),Store(acquire=False)
    with pytest.raises(RuntimeError,match='writer is active'):
        upgrade.install(http,lambda _: 'synthetic',store,{'cells':[]})
    assert len(http.calls)==1 and not store.writes


def test_all_shipped_notebook_code_compiles_and_nochange_skips_forced_model_refresh():
    notebook=json.loads((ROOT/'ForecastMaster_Refresh.ipynb').read_text())
    for cell in notebook['cells']:
        if cell['cell_type']=='code':compile(''.join(cell['source']),'notebook','exec')
    assert 'FORCE_MODEL_REFRESH = False' in ''.join(notebook['cells'][2]['source'])


def test_retention_guard_accepts_exact_current_set_and_rejects_incomplete_pointers():
    assert current_content_ids([{"SourceRevisionID":"current"}], {"current"}) == ["current"]
    with pytest.raises(ValueError): current_content_ids([], {"old"})
    with pytest.raises(ValueError): current_content_ids([{"SourceRevisionID":"missing"}], {"old"})
