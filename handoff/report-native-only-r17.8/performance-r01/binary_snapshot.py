"""Exact DOUBLE transport for calculated-only local fixture partitions.

Encode IEEE values as integer mantissa and binary exponent, avoiding a decimal
DAX literal round trip. This is a fabricated-fixture transport, not the company
serving-table design. No tolerance or refresh coherence gate is relaxed.
"""
import json
import math
from pathlib import Path
import re
import shutil

import cache_prepare
import probe
import regression


def parts(value):
    if value is None:return None,0
    value=float(value)
    if not math.isfinite(value):raise ValueError('Nonfinite DOUBLE transport')
    if value==0:return 0,0
    mantissa,exponent=math.frexp(value)
    return int(math.ldexp(mantissa,53)),exponent-53


def encode_table(table):
    source=table['partitions'][0]['source']['expression']
    if not source.startswith('DATATABLE(') or not source.endswith(')'):raise ValueError('Literal fixture source only')
    boundary=source.index(',{');header=source[len('DATATABLE('):boundary]
    fields=re.findall(r'"([A-Za-z_][A-Za-z_0-9]*)",(INTEGER|DOUBLE|STRING)',header)
    if ','.join(json.dumps(n)+','+kind for n,kind in fields)!=header:raise ValueError('Unexpected literal schema')
    if any(kind=='STRING' and n!='Kind' for n,kind in fields):raise ValueError('This transport admits only period-kind string values')
    body=source[boundary+1:-1].replace('BLANK()','null').replace('{','[').replace('}',']')
    def reject(value):raise ValueError('Nonfinite JSON token: '+value)
    rows=json.loads(body,parse_constant=reject)
    schema=[];selectors=[]
    for i,(name,kind) in enumerate(fields):
        if kind=='DOUBLE':
            schema.extend([(f'f{i}m','int64'),(f'f{i}e','int64')])
            selectors.extend([json.dumps(name),f'IF(ISBLANK([f{i}m]),BLANK(),([f{i}m]*POWER(2,MAX([f{i}e],-1022)))*POWER(2,MIN([f{i}e]+1022,0)))'])
        else:
            schema.append((name,'int64' if kind=='INTEGER' else 'string'));selectors.extend([json.dumps(name),'['+name+']'])
    encoded=[]
    for row in rows:
        if len(row)!=len(fields):raise ValueError('Unexpected fixture row width')
        out=[]
        for value,(_,kind) in zip(row,fields,strict=True):
            if kind=='DOUBLE':out.extend(parts(value))
            elif kind=='STRING':
                if value not in {'FY','YTD','YTG','H1','H2'}:raise ValueError('Unknown period kind')
                out.append(value)
            else:out.append(value)
        encoded.append(out)
    raw=cache_prepare.table('binary_transport',schema,encoded)['partitions'][0]['source']['expression']
    table['partitions'][0]['source']['expression']='VAR _encoded='+raw+'\nRETURN SELECTCOLUMNS(_encoded,'+','.join(selectors)+')'
    return {'Table':table['name'],'Rows':len(rows),'DoubleFields':sum(kind=='DOUBLE' for _,kind in fields)}


def build(destination,source):
    if destination.exists():raise ValueError('Preserve binary transport attempt')
    bound=regression.checked(source)
    if bound.get('Prototype')!='precise-validated-snapshot':raise ValueError('Require precise CSV snapshot')
    db=json.loads((source/'candidate.json').read_text())
    encoded=[encode_table(t) for t in db['model']['tables'] if t['name'] in {'fm_cache_monthly','fm_leaf_kpi'}]
    if len(encoded)!=2:raise ValueError('Missing prepared partitions')
    destination.mkdir(parents=True);(destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    for n in ('baseline.json','queries.json','expected.json','preparation.json','precise-preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**bound,'Files':files,'Prototype':'binary-validated-snapshot',
        'ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'EncodedTables':encoded,'CompanyDeployment':False,
        'Purpose':'Lossless local DOUBLE transport; company Delta DOUBLE columns would not use DAX constants.',
        'ExactReadinessGateUnchanged':True},indent=2))
    return {'Directory':str(destination),'Encoded':encoded}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:3])),indent=2))
