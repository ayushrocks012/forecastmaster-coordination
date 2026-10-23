"""Developer-only fabricated engine regression for empty metadata counters."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BEFORE_QUERY='''EVALUATE ROW("Files",COUNTROWS('fm_native_files'),
 "Choices",DISTINCTCOUNT('fm_native_files'[FileChoiceLabel]),
 "MissingImportedAt",COUNTROWS(FILTER('fm_native_files',ISBLANK('fm_native_files'[ImportedAtUTC]))),
 "HashSuffixes",COUNTROWS(FILTER('fm_native_files',RIGHT('fm_native_files'[FileChoiceLabel],LEN('fm_native_files'[SourceRevisionID]))='fm_native_files'[SourceRevisionID])))'''


def current_query():
    tree=ast.parse((HERE/'verify_receiving.py').read_text())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='verify_installed')
    queries=[ast.literal_eval(n.value) for n in ast.walk(function) if isinstance(n,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id=='query' for t in n.targets)]
    if len(queries)!=1:raise ValueError('Expected one literal metadata query')
    return queries[0]


def model(invalid=False):
    columns=[('SourceRevisionID','string'),('FileChoiceLabel','string'),('ImportedAtUTC','dateTime')]
    suffix='b'*64 if invalid else 'good import'
    stamp='BLANK()' if invalid else '"2026-10-23 12:00:00"'
    expression='''DATATABLE("SourceRevisionID",STRING,"FileChoiceLabel",STRING,"ImportedAtUTC",DATETIME,{
{"'''+('a'*64)+'''","First.xlsm · good import","2026-10-23 12:00:00"},
{"'''+('b'*64)+'","Second.xlsm · '+suffix+'",'+stamp+'}})'
    table={'name':'fm_native_files','columns':[{'name':name,'dataType':kind,'type':'calculatedTableColumn',
      'sourceColumn':'['+name+']','summarizeBy':'none'} for name,kind in columns],
      'partitions':[{'name':'synthetic','mode':'import','source':{'type':'calculated','expression':expression}}]}
    return {'name':'ForecastMasterNativeSyntheticMetadataCounts','compatibilityLevel':1604,
            'model':{'culture':'en-GB','tables':[table]}}


def build(directory):
    directory.mkdir(parents=True,exist_ok=False)
    queries=[{'name':stage+'/'+state,'model':kind,'query':query}
      for stage,query in [('before',BEFORE_QUERY),('after',current_query())]
      for state,kind in [('healthy','baseline'),('invalid','candidate')]]
    for name,value in [('baseline',model()),('candidate',model(True)),('queries',queries)]:
        (directory/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False))
    return {'Queries':len(queries),'SyntheticOnly':True}


def verify(directory):
    queries=json.loads((directory/'queries.json').read_text())
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    expected={
      'before/healthy':{'[Files]':2,'[Choices]':2,'[MissingImportedAt]':None,'[HashSuffixes]':None},
      'after/healthy':{'[Files]':2,'[Choices]':2,'[MissingImportedAt]':0,'[HashSuffixes]':0},
      'before/invalid':{'[Files]':2,'[Choices]':2,'[MissingImportedAt]':1,'[HashSuffixes]':1},
      'after/invalid':{'[Files]':2,'[Choices]':2,'[MissingImportedAt]':1,'[HashSuffixes]':1}}
    failures=[]
    if len(results)!=4 or {r['name'] for r in results}!=set(expected):failures.append('Exact query population')
    for result in results:
        if 'error' in result or result.get('rows')!=[expected.get(result['name'])]:failures.append(result['name'])
    if next(q['query'] for q in queries if q['name']=='after/healthy')!=current_query():failures.append('Verifier query changed after bound native run')
    return {'Stage':'R178_VERIFIER_R02_METADATA_COUNTS_VERIFIED' if not failures else 'FAILED',
      'NativeQueries':len(results),'Failures':failures,'BeforeHealthyBlankCountersReproduced':True,
      'AfterHealthyCountersAreNumericZero':True,'PositiveErrorCountsPreserved':True,
      'SyntheticOnly':True,'CompanyRun':False,
      'InputSHA256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.json')}}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['build','verify']);parser.add_argument('directory',type=Path)
    args=parser.parse_args();result=build(args.directory) if args.mode=='build' else verify(args.directory)
    print(json.dumps(result,indent=2))
    raise SystemExit(bool(result.get('Failures')))
