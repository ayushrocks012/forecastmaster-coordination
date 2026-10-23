import ast
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r178_check',HERE/'CHECK BLANK VISUALS AND CUTOFFS.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)

class Response:
    status_code=200
    def json(self):return {'id':check.TEST_MODEL,'displayName':check.TEST_NAME,'type':'SemanticModel'}
class Client:
    def get(self,path):
        assert path==check.ITEM
        return Response()
class Frame:
    def __init__(self,row):self.row=row
    def to_dict(self,orient):return [self.row]

class Tests(unittest.TestCase):
    def test_two_sequential_metadata_queries_and_only_counts(self):
        calls=[]
        def evaluate(**kw):
            self.assertFalse(kw['use_readwrite_connection'])
            self.assertEqual(check.TEST_MODEL,kw['dataset'])
            calls.append(kw['dax_string'])
            return Frame({'['+key+']':None if key.endswith('Mismatch') else 1 for key in check.FIELDS['Files' if len(calls)==1 else 'Guards']})
        with redirect_stdout(io.StringIO()):r=check.safe_run(Client(),evaluate)
        self.assertEqual('R178_METADATA_READS_COMPLETED',r['Stage'])
        self.assertEqual(2,len(calls))
        for k in ('CompanyAmountsQueriedOrPrinted','ModelWriteRequested','RefreshRequested','ReportPublished'):self.assertIs(False,r[k])
    def test_raw_error_and_unknown_fields_never_print(self):
        for evaluate in (lambda **kw:(_ for _ in ()).throw(RuntimeError('PRIVATE_ERROR')),
                         lambda **kw:Frame({'PRIVATE_COLUMN':'PRIVATE_VALUE'})):
            out=io.StringIO()
            with redirect_stdout(out):r=check.safe_run(Client(),evaluate)
            self.assertEqual('R178_METADATA_CHECK_STOPPED',r['Stage'])
            self.assertNotIn('PRIVATE',out.getvalue())
    def test_no_amount_query_or_writer_and_python310(self):
        s=(HERE/'CHECK BLANK VISUALS AND CUTOFFS.py').read_text()
        ast.parse(s,feature_version=(3,10))
        for forbidden in ('[Amount]','[N Plan]','[N Benchmark]','updateDefinition','client.post','fs.put'):
            self.assertNotIn(forbidden,s)
        with self.assertRaises(ValueError):check.counts(Frame({'[SourceOK]':'PRIVATE'}),{'SourceOK'})

if __name__=='__main__':unittest.main()
