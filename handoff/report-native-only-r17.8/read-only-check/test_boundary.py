import ast
import base64
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r178_boundary',HERE/'CHECK DATE BOUNDARY R02.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class Response:
    status_code=200
    def __init__(self,value):self.value=value
    def json(self):return self.value
class Client:
    def __init__(self):self.calls=[];self.wrong=False
    def get(self,path):
        self.calls.append(('GET',path))
        return Response({'id':'WRONG' if self.wrong else c.TEST,'displayName':c.NAME,'type':'SemanticModel'})
    def post(self,path):
        self.calls.append(('POST',path))
        assert path=='/v1/workspaces/'+c.WORKSPACE+'/semanticModels/'+c.TEST+'/getDefinition?format=TMSL'
        model={'model':{'tables':[{'name':t,'partitions':[{'mode':'directLake','source':{'type':'entity','entityName':t,'private':'PRIVATE'}}],
             'columns':[{'name':n,'dataType':'dateTime','sourceColumn':n} for n in ns]} for t,ns in c.FIELDS.items()]}}
        return Response({'definition':{'parts':[{'path':'model.bim','payload':base64.b64encode(json.dumps(model).encode()).decode()}]}})
class Frame:
    def to_dict(self,orient):return [{k:1 for k in ('FactMonthKeys','InvalidFactMonthKeys','AxisMonthKeys','InvalidAxisMonthKeys',
        'ReviewMonthKeys','InvalidReviewMonthKeys','StartMonthKeys','InvalidStartMonthKeys','EndMonthKeys','InvalidEndMonthKeys')}]

class Tests(unittest.TestCase):
    def test_metadata_only_routes_counts_and_complete_vs_partial(self):
        for full in (True,False):
            client=Client();calls=[]
            def evaluate(**kw):
                self.assertFalse(kw['use_readwrite_connection']);calls.append(kw);return Frame()
            delta={t:{'Status':'READ_COMPLETED' if full else 'PATH_MISSING_OR_AMBIGUOUS'} for t in c.FIELDS}
            out=io.StringIO()
            with redirect_stdout(out),patch.object(c,'physical',return_value=delta):r=c.safe_run(client,evaluate,None,None)
            self.assertEqual('R178_DATE_BOUNDARY_READS_COMPLETED' if full else 'R178_DATE_BOUNDARY_PARTIAL',r['Stage'])
            self.assertEqual(full,r['AllPhysicalDateReadsCompleted']);self.assertEqual(1,len(calls))
            self.assertEqual(2,len(client.calls));self.assertNotIn('PRIVATE',out.getvalue())
            for k in ('CompanyAmountsQueriedOrPrinted','SourceRecordsOrIdentifiersPrinted','ModelWriteRequested','LakehouseWriteRequested','RefreshRequested','ReportPublished'):
                self.assertIs(False,r[k])
    def test_wrong_identity_stops_before_query_and_physical_reads(self):
        client=Client();client.wrong=True
        out=io.StringIO()
        with redirect_stdout(out),patch.object(c,'physical') as physical:
            r=c.safe_run(client,lambda **kw:self.fail('wrong model queried'),None,None)
        self.assertEqual('R178_DATE_BOUNDARY_CHECK_STOPPED',r['Stage']);physical.assert_not_called()
    def test_private_errors_and_unexpected_value_types_never_print(self):
        out=io.StringIO()
        with redirect_stdout(out):r=c.safe_run(Client(),lambda **kw:(_ for _ in ()).throw(RuntimeError('PRIVATE_EXCEPTION')),None,None)
        self.assertNotIn('PRIVATE',out.getvalue());self.assertEqual('RuntimeError',r['ExceptionFamily'])
        with self.assertRaises(RuntimeError):c.safe_counts(type('F',(),{'to_dict':lambda self,orient:[{'[PRIVATE]':'PRIVATE'}]})())
    def test_no_writers_amount_columns_or_python_syntax_drift(self):
        s=(HERE/'CHECK DATE BOUNDARY R02.py').read_text();ast.parse(s,feature_version=(3,10))
        for token in ('[Amount]','[N Plan]','[N Benchmark]','updateDefinition','saveAsTable','save(','fs.put','client.delete'):
            self.assertNotIn(token,s)
        self.assertIn("df=df.select(*selected)",s)

if __name__=='__main__':unittest.main()
