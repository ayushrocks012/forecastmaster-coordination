"""TEST-only processing order, safe holds, backup/readback and date parity."""
import ast
from contextlib import redirect_stdout
from datetime import date,datetime
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote,urlsplit

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r178_reset',HERE/'RESET TEST DATE CACHE R01.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
RID=['20000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000002']


class Response:
    def __init__(self,data,status=200,headers=None):self.data=data;self.status_code=status;self.headers=headers or {}
    def json(self):return self.data


class Fabric:
    def __init__(self):self.wrong=False;self.calls=[]
    def get(self,path):
        self.calls.append(path)
        if path==p.ITEM:return Response({'id':'WRONG' if self.wrong else p.TEST,'displayName':p.NAME,'type':'SemanticModel'})
        if path==p.ITEM+'/connections':return Response({'value':[{'id':'PRIVATE_CONNECTION'}]})
        raise AssertionError('unexpected Fabric route')


class PBI:
    def __init__(self):self.calls=[];self.posts=[];self.active=False;self.ambiguous=False;self.fail_clear=False;self.full=False;self.foreign=False
    def get(self,url):
        self.calls.append(('GET',url))
        if url==p.PBI_BASE+'/refreshes?$top=5':return Response({'value':[{'status':'Unknown' if self.active else 'Completed'}]})
        if url==p.PBI_BASE+'/refreshes/'+RID[0]:return Response({'status':'Failed' if self.fail_clear else 'Completed'})
        if url==p.PBI_BASE+'/refreshes/'+RID[1]:self.full=True;return Response({'status':'Completed'})
        raise AssertionError('unexpected Power BI route')
    def post(self,url,json):
        self.calls.append(('POST',url));self.posts.append(json)
        assert url==p.PBI_BASE+'/refreshes'
        if self.ambiguous:raise RuntimeError('PRIVATE_LOST_RESPONSE')
        n=len(self.posts)-1
        location=('https://private.example/' if self.foreign else p.PBI_BASE+'/refreshes/')+RID[n]
        return Response({},202,{'Location':location})


class FS:
    def __init__(self):self.files={};self.dirs=set();self.corrupt=False
    def exists(self,path):return path in self.files or path in self.dirs
    def mkdirs(self,path):self.dirs.add(path)  # Some SDKs return None.
    def put(self,path,text,overwrite):
        if path in self.files and not overwrite:return False
        self.files[path]=text.encode();return True
    def cp(self,src,dst,recurse):
        Path(unquote(urlsplit(dst).path)).write_bytes(self.files[src]+(b'CORRUPT' if self.corrupt else b''));return True


def snapshot():
    expr='AzureStorage.DataLake("https://onelake.dfs.fabric.microsoft.com/'+p.WORKSPACE+'/'+p.LAKEHOUSE+'")'
    tables=[{'name':table,'partitions':[{'source':{'expressionSource':'DL'}}]} for table in p.FIELDS]
    tables.extend({'name':name} for name in ('fm_native_files','fm_native_measures'))
    db={'model':{'tables':tables,'expressions':[{'name':'DL','expression':expr}]}}
    bindings={table:{'PartitionCount':1,'Mode':'directLake','SourceType':'entity','EntityNameMatchesExpected':True,
        'Columns':{name:{'ModelDataType':'dateTime','SourceColumnMatchesExpected':True} for name in columns}} for table,columns in p.FIELDS.items()}
    return {'parts':[{'path':'model.bim','payload':'PRIVATE_DEFINITION'}]},db,bindings


def dates():
    return {kind:[('SYNTHETIC_ID' if kind.endswith(('IMS','EF')) else '', '2026-01-01')] for kind in p.KINDS}


class Frame:
    def __init__(self,data):self.data=data
    def to_dict(self,orient):return self.data


class Tests(unittest.TestCase):
    def run_case(self,client=None,pbi=None,fs=None,already=False,still_bad=False,definition_change=False):
        client=client or Fabric();pbi=pbi or PBI();fs=fs or FS();physical=dates()
        def semantic(*args):
            got=dates()
            if still_bad or not already and not pbi.full:got['Axis']=[('', '1899-12-30')]
            return got
        calls=[0]
        def definition(*args):
            calls[0]+=1;v=snapshot()
            if definition_change and calls[0]==(3 if definition_change=='after' else 2):v[0]['changed']='PRIVATE_CHANGE'
            return v
        out=io.StringIO()
        with redirect_stdout(out),patch.object(p,'read_definition',side_effect=definition),patch.object(p,'physical_dates',return_value=physical),patch.object(p,'semantic_dates',side_effect=semantic):
            r=p.run(client,pbi,None,None,fs)
        for token in ('PRIVATE_CONNECTION','PRIVATE_DEFINITION','PRIVATE_LOST_RESPONSE','PRIVATE_PRIOR_ATTEMPT','PRIVATE_CHANGE','SYNTHETIC_ID'):
            self.assertNotIn(token,out.getvalue())
        return r,pbi,fs

    def test_success_requires_clear_then_full_and_exact_post_dates(self):
        r,pbi,fs=self.run_case()
        self.assertEqual('TEST_R178_DATE_CACHE_RESET_VERIFIED',r['Stage'])
        self.assertEqual(['clearValues','full'],[x['type'] for x in pbi.posts])
        for body in pbi.posts:
            self.assertEqual(0,body['retryCount']);self.assertEqual('transactional',body['commitMode'])
            self.assertEqual(1,body['maxParallelism']);self.assertFalse(body['applyRefreshPolicy'])
        self.assertTrue(r['DateParityVerified']);self.assertTrue(r['OtherModelDefinitionPreserved']);self.assertTrue(r['CloudConnectionPreserved'])
        self.assertEqual(4,len(fs.files));self.assertIn(p.PRIVATE+'/ATTEMPT.json',fs.files)
        for field in ('ModelDefinitionWriteRequested','LakehouseTableWriteRequested','OriginalModelWriteRequested','CompanyAmountQuerySubmitted','CompanyAmountsPrintedOrStoredByScript','ReportPublished','NativeR178AdapterInstalled'):
            self.assertIs(False,r[field])

    def test_currently_valid_dates_skip_all_processing_and_backups(self):
        r,pbi,fs=self.run_case(already=True)
        self.assertEqual('TEST_R178_DATES_ALREADY_MATCH_NO_RESET',r['Stage']);self.assertFalse(pbi.posts);self.assertFalse(fs.files)

    def test_wrong_identity_stops_before_definition_or_processing(self):
        client=Fabric();client.wrong=True
        r,pbi,fs=self.run_case(client=client)
        self.assertEqual('TEST_IDENTITY_MISMATCH',r['Failure']['Reason']);self.assertFalse(pbi.calls);self.assertFalse(fs.files)
        _,db,bindings=snapshot();db['model']['expressions'][0]['expression']='AzureStorage.DataLake("OTHER_SYNTHETIC_SOURCE")'
        with self.assertRaises(p.CheckStopped) as caught:p.routing(db,bindings)
        self.assertEqual('KNOWN_LAKEHOUSE_ROUTE_UNPROVEN',caught.exception.code)

    def test_existing_attempt_prevents_resubmission(self):
        fs=FS();fs.files[p.PRIVATE+'/ATTEMPT.json']=b'PRIVATE_PRIOR_ATTEMPT'
        r,pbi,fs=self.run_case(fs=fs)
        self.assertEqual('RESET_ALREADY_ATTEMPTED_SEND_PRIOR_RESULT',r['Failure']['Reason']);self.assertFalse(pbi.calls)

    def test_active_refresh_prevents_backup_and_processing(self):
        pbi=PBI();pbi.active=True
        r,pbi,fs=self.run_case(pbi=pbi)
        self.assertEqual('TEST_REFRESH_ACTIVE_OR_UNKNOWN',r['Failure']['Reason']);self.assertFalse(pbi.posts);self.assertFalse(fs.files)

    def test_backup_corruption_prevents_any_processing(self):
        fs=FS();fs.corrupt=True
        r,pbi,fs=self.run_case(fs=fs)
        self.assertEqual('PRIVATE_BACKUP_FULL_UTF8_VERIFICATION_FAILED',r['Failure']['Reason']);self.assertFalse(pbi.posts)

    def test_concurrent_definition_change_prevents_processing(self):
        r,pbi,fs=self.run_case(definition_change=True)
        self.assertEqual('TEST_METADATA_CHANGED_NO_RESET',r['Failure']['Reason']);self.assertFalse(pbi.posts)

    def test_lost_submit_response_never_retries_or_claims_no_action(self):
        pbi=PBI();pbi.ambiguous=True
        r,pbi,fs=self.run_case(pbi=pbi)
        self.assertEqual(1,len(pbi.posts));self.assertTrue(r['Processing']['clearValuesRequested']);self.assertFalse(r['Processing']['clearValuesCompleted'])
        self.assertFalse(r['Processing']['fullRequested']);self.assertEqual('EXCEPTION_WITHHELD',r['Failure']['Reason'])

    def test_failed_clear_never_submits_full_and_foreign_location_not_followed(self):
        for failure in ('fail_clear','foreign'):
            pbi=PBI();setattr(pbi,failure,True)
            r,pbi,fs=self.run_case(pbi=pbi)
            self.assertEqual(1,len(pbi.posts));self.assertFalse(r['Processing']['fullRequested'])
            self.assertTrue(all(url.startswith(p.PBI_BASE) for _,url in pbi.calls))

    def test_successful_refresh_does_not_substitute_for_date_parity(self):
        r,pbi,fs=self.run_case(still_bad=True)
        self.assertEqual('DATES_STILL_DIFFER_AFTER_RESET',r['Failure']['Reason'])
        self.assertFalse(r['DateParityVerified']);self.assertTrue(r['Processing']['fullCompleted']);self.assertEqual(2,len(pbi.posts))

    def test_pending_202_waits_for_clear_before_full(self):
        class Pending(PBI):
            def __init__(self):super().__init__();self.pending=set();self.clear_done=False
            def get(self,url):
                if any(url.endswith('/'+rid) for rid in RID) and url not in self.pending:
                    self.pending.add(url);return Response({'status':'Unknown','extendedStatus':'InProgress'},202)
                response=super().get(url)
                if url.endswith('/'+RID[0]):self.clear_done=True
                return response
            def post(self,url,json):
                if json['type']=='full':assert self.clear_done
                return super().post(url,json)
        with patch.object(p.time,'sleep') as sleep:r,pbi,fs=self.run_case(pbi=Pending())
        self.assertEqual('TEST_R178_DATE_CACHE_RESET_VERIFIED',r['Stage']);self.assertEqual(2,sleep.call_count)

    def test_post_refresh_metadata_change_requires_review_even_when_dates_match(self):
        r,pbi,fs=self.run_case(definition_change='after')
        self.assertFalse(r['OtherModelDefinitionPreserved']);self.assertTrue(r['DateParityVerified'])
        self.assertEqual('TEST_METADATA_READBACK_NEEDS_REVIEW',r['Failure']['Reason'])

    def test_exact_date_comparison_checks_values_ids_and_not_only_range(self):
        expected=dates();actual=dates();actual['SourceIMS']=[('OTHER_SYNTHETIC_ID','2026-01-01')]
        actual['Axis']=[('', '2026-02-01')]
        result=p.compare(expected,actual)
        self.assertEqual(0,result['Axis']['InvalidSemanticDates']);self.assertFalse(result['Axis']['ExactRowsMatch'])
        self.assertFalse(result['SourceIMS']['ExactRowsMatch'])

    def test_semantic_metadata_values_stay_private_and_no_financial_query(self):
        def evaluate(**kw):
            self.assertFalse(kw['use_readwrite_connection']);self.assertNotIn('[Amount]',kw['dax_string'])
            return Frame([{'[Kind]':'Axis','[ID]':'','[D]':date(2026,1,1)}])
        result=p.semantic_dates(evaluate,{})
        self.assertEqual([('', '2026-01-01')],result['Axis'])
        self.assertIsNone(p.as_date(datetime(2026,1,1,12,0)))

    def test_utf8_backup_is_full_file_verified(self):
        fs=FS();p.verified_backup(fs,'test.json',{'sample':'SYNTHETIC café £'})
        self.assertIn('café'.encode(),fs.files['test.json'])

    def test_python_310_static_routes_and_no_definition_or_table_writers(self):
        source=(HERE/'RESET TEST DATE CACHE R01.py').read_text();tree=ast.parse(source,feature_version=(3,10))
        posts=[ast.unparse(n) for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='post']
        self.assertEqual(2,len(posts));self.assertTrue(any('/getDefinition?format=TMSL' in x for x in posts))
        self.assertTrue(any("PBI_BASE + '/refreshes'" in x for x in posts))
        for token in ('updateDefinition','saveAsTable','client.delete','[Amount]','[N Plan]','[N Benchmark]'):
            self.assertNotIn(token,source)
        self.assertIn("'total':0",source);self.assertIn("'allowed_methods':['GET']",source)


if __name__=='__main__':unittest.main()
