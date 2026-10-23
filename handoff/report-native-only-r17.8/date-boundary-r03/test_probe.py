"""Mock read routes, asynchronous definition responses, and partial evidence.

No company or Spark runtime claimed. Fabricated metadata only.
"""
import ast
import base64
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r178_boundary_r03',HERE/'CHECK DATE BOUNDARY R03.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
OP='10000000-0000-4000-8000-000000000001'


def model():
    return {'model':{'tables':[{'name':t,'partitions':[{'mode':'directLake','source':
        {'type':'entity','entityName':t,'private':'PRIVATE_TOKEN'}}],
        'columns':[{'name':n,'dataType':'dateTime','sourceColumn':n} for n in ns]} for t,ns in p.FIELDS.items()]}}


class Response:
    def __init__(self,data=None,status=200,headers=None):self.data=data;self.status_code=status;self.headers=headers or {}
    def json(self):return self.data


def definition():
    return Response({'definition':{'parts':[{'path':'model.bim','payload':base64.b64encode(json.dumps(model()).encode()).decode()}]}})


class Client:
    def __init__(self):self.calls=[];self.response=definition();self.wrong=False;self.states=['Running','Succeeded']
    def get(self,path):
        self.calls.append(('GET',path))
        if path.endswith('/items/'+p.TEST):
            return Response({'id':'WRONG' if self.wrong else p.TEST,'displayName':p.NAME,'type':'SemanticModel'})
        if path=='/v1/operations/'+OP:return Response({'status':self.states.pop(0)})
        if path=='/v1/operations/'+OP+'/result':return definition()
        raise AssertionError('unexpected read route')
    def post(self,path):
        self.calls.append(('POST',path))
        assert path=='/v1/workspaces/'+p.WORKSPACE+'/semanticModels/'+p.TEST+'/getDefinition?format=TMSL'
        return self.response


class Frame:
    def to_dict(self,orient):return [{prefix+name:0 for prefix in ('','Invalid') for name in
        ('FactMonthKeys','AxisMonthKeys','ReviewMonthKeys','StartMonthKeys','EndMonthKeys')}]


def delta():return {t:{'Status':'READ_COMPLETED','Data':{'RowsOrDistinctFactMonthKeys':1}} for t in p.FIELDS}


class Expr:
    def __getattr__(self,name):return lambda *args:self
    def __lt__(self,other):return self
    def __ge__(self,other):return self
    def __eq__(self,other):return self
    def __or__(self,other):return self
    def __and__(self,other):return self


class DF:
    def __init__(self,table,events):self.table=table;self.events=events;self.schema=self
    def __getitem__(self,name):return types.SimpleNamespace(dataType=types.SimpleNamespace(simpleString=lambda:'date'))
    def select(self,*names):self.events.append(('select',self.table,names));return self
    def filter(self,*args):return self
    def distinct(self):return self
    def join(self,*args):return self
    def agg(self,*args):return self
    def collect(self):
        row={'Rows':1,**{n:0 for n in p.FIELDS[self.table]}}
        return [types.SimpleNamespace(asDict=lambda:row)]


class Tests(unittest.TestCase):
    def run_probe(self,client=None,evaluate=None,physical=None):
        out=io.StringIO()
        with redirect_stdout(out),patch.object(p,'physical',physical or (lambda spark,fs:delta())):
            r=p.run(client or Client(),evaluate or (lambda **kw:Frame()),None,None)
        self.assertNotIn('PRIVATE',out.getvalue())
        return r

    def test_complete_read_no_write_and_exact_query_flags(self):
        client=Client();calls=[]
        def evaluate(**kw):calls.append(kw);return Frame()
        r=self.run_probe(client,evaluate)
        self.assertEqual('R178_DATE_BOUNDARY_R03_COMPLETED',r['Stage'])
        self.assertTrue(r['AllRequestedReadsCompleted']);self.assertEqual(2,len(client.calls))
        self.assertEqual(p.QUERY,calls[0]['dax_string']);self.assertFalse(calls[0]['use_readwrite_connection'])
        for key in ('ModelWriteRequested','LakehouseWriteRequested','RefreshRequested','ReportPublished','CompanyAmountsQueriedOrPrinted'):
            self.assertIs(False,r[key])

    def test_identity_mismatch_prevents_all_other_reads(self):
        client=Client();client.wrong=True
        r=self.run_probe(client,lambda **kw:self.fail('wrong identity queried'),lambda *args:self.fail('wrong identity read physically'))
        self.assertEqual('R178_DATE_BOUNDARY_R03_STOPPED',r['Stage'])
        self.assertEqual('TEST_IDENTITY_MISMATCH',r['Checks']['Identity']['Failure']['Reason'])
        self.assertEqual(1,len(client.calls))

    def test_definition_http_failure_retains_independent_semantic_and_physical_results(self):
        client=Client();client.response=Response({'error':'PRIVATE_HTTP_BODY'},403)
        r=self.run_probe(client)
        self.assertEqual('R178_DATE_BOUNDARY_R03_PARTIAL',r['Stage'])
        failure=r['Checks']['Definition']['Failure']
        self.assertEqual(('DEFINITION_REQUEST',403,'HTTP_NOT_EXPECTED'),(failure['Step'],failure['HTTPStatus'],failure['Reason']))
        self.assertEqual('READ_COMPLETED',r['Checks']['SemanticMonths']['Status'])
        self.assertEqual('READ_COMPLETED',r['Checks']['PhysicalDates']['Status'])

    def test_documented_operation_id_polling_and_retry_after(self):
        client=Client();client.response=Response(status=202,headers={'x-ms-operation-id':OP,'Retry-After':'20'})
        with patch.object(p.time,'sleep') as sleep:r=self.run_probe(client)
        self.assertEqual('R178_DATE_BOUNDARY_R03_COMPLETED',r['Stage'])
        self.assertEqual([20,5],[call.args[0] for call in sleep.call_args_list])
        self.assertEqual(1,sum(method=='POST' for method,path in client.calls))
        self.assertEqual('/v1/operations/'+OP+'/result',client.calls[-1][1])

    def test_known_location_fallback_and_foreign_locations_refused(self):
        for prefix in ('/v1/operations/','/operations/','https://api.fabric.microsoft.com/v1/operations/'):
            self.assertEqual('/v1/operations/'+OP,p.operation_path({'Location':prefix+OP}))
        for location in ('https://private.example/v1/operations/'+OP,'/v1/operations/'+OP+'?PRIVATE=1',
                         '/v1/operations/'+OP+'/result','//private.example/v1/operations/'+OP):
            with self.assertRaises(p.CheckStopped):p.operation_path({'Location':location})
        with self.assertRaises(p.CheckStopped):p.operation_path({'x-ms-operation-id':'PRIVATE_NOT_UUID'})

    def test_operation_failure_and_timeout_keep_safe_step(self):
        for states,reason in ((['Failed'],'DEFINITION_OPERATION_FAILED'),(['Running']*72,'DEFINITION_OPERATION_TIMEOUT')):
            client=Client();client.states=states;client.response=Response(status=202,headers={'x-ms-operation-id':OP})
            clock=[0]
            def sleep(delay):clock[0]+=delay
            with patch.object(p.time,'sleep',side_effect=sleep),patch.object(p.time,'monotonic',side_effect=lambda:clock[0]):
                r=self.run_probe(client)
            self.assertEqual(reason,r['Checks']['Definition']['Failure']['Reason'])
            self.assertEqual('READ_COMPLETED',r['Checks']['PhysicalDates']['Status'])

    def test_semantic_exception_retains_other_reads_without_raw_error(self):
        def evaluate(**kw):raise RuntimeError('PRIVATE_ERROR_AND_RECORDS')
        r=self.run_probe(evaluate=evaluate)
        self.assertEqual('SEMANTIC_MONTH_QUERY',r['Checks']['SemanticMonths']['Failure']['Step'])
        self.assertEqual('EXCEPTION_WITHHELD',r['Checks']['SemanticMonths']['Failure']['Reason'])
        self.assertEqual('READ_COMPLETED',r['Checks']['Definition']['Status'])
        self.assertEqual('READ_COMPLETED',r['Checks']['PhysicalDates']['Status'])

    def test_unexpected_count_fields_and_values_have_specific_safe_reason(self):
        with self.assertRaises(p.CheckStopped) as caught:p.safe_counts(types.SimpleNamespace(to_dict=lambda **kw:[{'PRIVATE':'PRIVATE'}]))
        self.assertEqual('METADATA_FIELDS_UNEXPECTED',caught.exception.code)
        rows=Frame().to_dict('records');rows[0]['FactMonthKeys']='PRIVATE_VALUE'
        with self.assertRaises(p.CheckStopped) as caught:p.safe_counts(types.SimpleNamespace(to_dict=lambda **kw:rows))
        self.assertEqual('METADATA_COUNT_TYPE_INVALID',caught.exception.code)

    def test_physical_failure_is_per_table_and_no_amount_columns_projected(self):
        events=[]
        functions=types.SimpleNamespace(**{name:(lambda *args:Expr()) for name in ('count','lit','col','year','sum','when')},broadcast=lambda x:x)
        modules={'pyspark':types.ModuleType('pyspark'),'pyspark.sql':types.SimpleNamespace(functions=functions)}
        read=types.SimpleNamespace(format=lambda value:types.SimpleNamespace(load=lambda path:DF(path.split('/')[-1],events)))
        spark=types.SimpleNamespace(read=read)
        class FS:
            def exists(self,path):
                if 'fm_review_files/' in path:raise RuntimeError('PRIVATE_PATH')
                return '/dbo/' not in path
        out=io.StringIO()
        with patch.dict('sys.modules',modules),redirect_stdout(out):r=p.physical(spark,FS())
        self.assertNotIn('PRIVATE',out.getvalue())
        self.assertEqual('PHYSICAL_PATH_CHECK',r['fm_review_files']['Failure']['Step'])
        self.assertEqual('READ_COMPLETED',r['fm_review_months']['Status'])
        self.assertEqual('READ_COMPLETED',r['fm_review_axis']['Status'])
        self.assertEqual('PHYSICAL_FILE_SCOPE_UNAVAILABLE',r['fm_review_facts']['Failure']['Reason'])
        self.assertTrue(events);self.assertFalse(any('Amount' in names for _,_,names in events))
        partial=self.run_probe(physical=lambda *args:r)
        self.assertFalse(partial['AllRequestedReadsCompleted'])

    def test_python_310_grammar_and_read_only_ast_routes(self):
        source=(HERE/'CHECK DATE BOUNDARY R03.py').read_text();tree=ast.parse(source,feature_version=(3,10))
        for token in ('[Amount]','[N Plan]','[N Benchmark]','updateDefinition','saveAsTable','fs.put','client.delete'):
            self.assertNotIn(token,source)
        posts=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='post']
        self.assertEqual(1,len(posts));self.assertIn('/getDefinition?format=TMSL',ast.unparse(posts[0]))


if __name__=='__main__':unittest.main()
