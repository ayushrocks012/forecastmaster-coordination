"""Bounded metadata-shape/privacy checks for the second read-only probe."""
import base64
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import check_readable_probe as api

ROOT=Path(__file__).resolve().parent.parent
SOURCE=(ROOT/'SOURCE ROUTE - READ ONLY.py').read_text()


def execute(model):
    data={'parts':[{'path':'model.bim','payload':base64.b64encode(json.dumps({'model':model}).encode()).decode()}]}
    client=api.Client([api.Response(200,{'definition':data})])
    with patch.object(api,'SOURCE',SOURCE):
        return api.execute(client)


def model(source=None,expressions=None,data_sources=None):
    return {'tables':[{'name':'fm_review_facts','partitions':[{'mode':'directLake',
             'source':source or {'type':'entity','expressionSource':'Source'}}]}],
            'expressions':expressions or [],'dataSources':data_sources or []}


class SourceRouteTests(unittest.TestCase):
    def test_sql_and_onelake_connector_hints(self):
        for connector in ('Sql.Database','Sql.Databases','AzureStorage.DataLake','OneLake.SqlAnalytics'):
            with self.subTest(connector=connector):
                result,calls,text=execute(model(expressions=[{'name':'Source','kind':'m',
                    'expression':f'{connector}("PRIVATE_HOST","PRIVATE_DATABASE")'}]))
                hint=result['ExpressionHints'][0]
                self.assertTrue(hint['ReferencedByFact'])
                self.assertEqual(hint['ConnectorHints'],[connector])
                self.assertNotIn('PRIVATE_',text)
                self.assertEqual(len(calls),1)
                self.assertFalse(result['ModelUpdated'])

    def test_structured_tds_reference_without_m_expression(self):
        data=model(source={'type':'entity','dataSource':'PRIVATE_NAME','schemaName':'dbo',
                           'entityName':'fm_review_facts'},data_sources=[{
            'name':'PRIVATE_NAME','type':'structured','connectionDetails':{
            'protocol':'tds','address':{'server':'PRIVATE_SERVER','database':'PRIVATE_DB'}},
            'credential':{'password':'PRIVATE_PASSWORD'}}])
        result,_,text=execute(data)
        self.assertTrue(result['HasDataSourceReference'])
        self.assertFalse(result['HasExpressionSourceReference'])
        self.assertTrue(result['DataSourceHints'][0]['ReferencedByFact'])
        self.assertEqual(result['DataSourceHints'][0]['Protocol'],'tds')
        self.assertEqual(result['DataSourceHints'][0]['AddressKeys'],['database','server'])
        self.assertNotIn('PRIVATE_',text)

    def test_provider_connection_string_is_not_printed(self):
        result,_,text=execute(model(source={'type':'entity','dataSource':'PRIVATE_NAME'},
            data_sources=[{'name':'PRIVATE_NAME','type':'provider',
                           'connectionString':'Server=PRIVATE_HOST;Password=PRIVATE_PASSWORD'}]))
        self.assertTrue(result['DataSourceHints'][0]['HasConnectionString'])
        self.assertNotIn('PRIVATE_',text)

    def test_unrelated_expression_is_distinguished(self):
        result,_,_=execute(model(expressions=[{'name':'Other','kind':'m',
            'expression':'Sql.Database("private.invalid","private")'}]))
        self.assertFalse(result['ExpressionHints'][0]['ReferencedByFact'])

    def test_malformed_or_json_connection_details(self):
        for details in ('invalid','[1,2]',json.dumps({'protocol':'tds','address':{'server':'PRIVATE'}})):
            with self.subTest(details=details):
                result,_,text=execute(model(data_sources=[{'name':'Other','type':'structured',
                                                        'connectionDetails':details}]))
                self.assertNotIn('PRIVATE',text)
                self.assertEqual(len(result['DataSourceHints']),1)

    def test_m_expression_lines_and_case(self):
        result,_,_=execute(model(expressions=[{'name':'Source','kind':'m',
                       'expression':['let','source = sql.database ("private", "private")','in source']}]))
        self.assertEqual(result['ExpressionHints'][0]['ConnectorHints'],['Sql.Database'])

    def test_missing_fact_remains_a_read_only_result(self):
        result,_,_=execute({'tables':[]})
        self.assertEqual(result['FactPartitionCount'],0)
        self.assertFalse(result['ModelUpdated'])

    def test_transport_and_no_installer_are_preserved(self):
        prefix=api.SOURCE[:api.SOURCE.index('def describe_model(')]
        source_prefix=SOURCE[:SOURCE.index('def connector_hints(')]
        self.assertEqual(prefix.replace('import json\n','import json\nimport re\n').replace(
            '# Paste this entire short file into ONE NEW code cell in ForecastMaster_GM_Setup.',
            '# Step 2: source-reference metadata only. Paste into ONE NEW setup-notebook cell.'),source_prefix)
        self.assertLess(len(SOURCE.encode()),6000)
        self.assertLessEqual(max(map(len,SOURCE.splitlines())),110)
        for forbidden in ('updateDefinition','saveAsTable','spark.sql','notebookutils','SPEC='):
            self.assertNotIn(forbidden,SOURCE)


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(SourceRouteTests)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    (ROOT/'VALIDATION-SOURCE-ROUTE-PROBE.json').write_text(json.dumps({
        'Tests':result.testsRun,'Passed':result.wasSuccessful(),'SourceBytes':len(SOURCE.encode()),
        'Evidence':'Synthetic mocked metadata only; connection values not echoed. Company source route remains unresolved.',
        'BusinessCodeOrInstallerChanged':False,'LiveCompanyExecution':False},indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
