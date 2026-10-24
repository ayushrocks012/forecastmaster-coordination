"""Local fixture transport using small integer limbs and exact division.

Avoid POWER and 16-digit mantissa literals in the calculated fixture loader.
Input IEEE values are unchanged. This bounded transport is not a company data
schema; out-of-range fixture values refuse construction instead of rounding.
"""
import json
from pathlib import Path
import re
import shutil

import cache_prepare
import probe
import regression


def limbs(mantissa,exponent):
    if mantissa is None:return None,0,1
    if exponent>0:
        mantissa*=2**exponent;exponent=0
    denominator=2**(-exponent)
    if abs(mantissa)>=2**63 or denominator>=2**63:raise ValueError('Fixture rational exceeds exact int64 domain')
    high,low=divmod(mantissa,2**26)
    return high,low,denominator


def encode(table):
    expression=table['partitions'][0]['source']['expression']
    if not expression.startswith('VAR _encoded=DATATABLE('):raise ValueError('Require bound binary source')
    dt=expression[len('VAR _encoded='):].split('\nRETURN',1)[0];boundary=dt.index(',{')
    fields=re.findall(r'"([A-Za-z_][A-Za-z_0-9]*)",(INTEGER|STRING)',dt[len('DATATABLE('):boundary])
    rows=json.loads(dt[boundary+1:-1].replace('BLANK()','null').replace('{','[').replace('}',']'))
    result=[];schema=[];select=[];i=0
    while i<len(fields):
        name,kind=fields[i]
        if re.fullmatch('f[0-9]+m',name):
            stem=name[:-1]
            if fields[i+1]!=(stem+'e','INTEGER'):raise ValueError('Unknown binary limbs')
            original_index=int(stem[1:]);original=table['columns'][original_index]['name']
            schema.extend([(stem+'h','int64'),(stem+'l','int64'),(stem+'d','int64')])
            select.extend([json.dumps(original),f'IF(ISBLANK([{stem}h]),BLANK(),DIVIDE([{stem}h]*67108864+[{stem}l],[{stem}d]))'])
            i+=2
        else:
            schema.append((name,'string' if kind=='STRING' else 'int64'));select.extend([json.dumps(name),'['+name+']']);i+=1
    for row in rows:
        out=[];i=0
        while i<len(fields):
            if re.fullmatch('f[0-9]+m',fields[i][0]):out.extend(limbs(row[i],row[i+1]));i+=2
            else:out.append(row[i]);i+=1
        result.append(out)
    raw=cache_prepare.table('ratio_input',schema,result)['partitions'][0]['source']['expression']
    table['partitions'][0]['source']['expression']='VAR _ratios='+raw+'\nRETURN SELECTCOLUMNS(_ratios,'+','.join(select)+')'


def build(destination,source):
    if destination.exists():raise ValueError('Preserve rational transport attempt')
    bound=regression.checked(source)
    if bound.get('Prototype')!='native-grouped-snapshot':raise ValueError('Require native grouped input')
    db=json.loads((source/'candidate.json').read_text())
    for table in db['model']['tables']:
        if table['name'] in {'fm_cache_monthly','fm_leaf_kpi'}:encode(table)
    destination.mkdir(parents=True);(destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    for n in ('baseline.json','queries.json','expected.json','preparation.json','native-preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**bound,'Files':files,'Prototype':'rational-validated-snapshot',
        'ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'CompanyDeployment':False,'ExactReadinessGateUnchanged':True},indent=2))
    return {'Directory':str(destination),'Queries':26}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:3])),indent=2))
