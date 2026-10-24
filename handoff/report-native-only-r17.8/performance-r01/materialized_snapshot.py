"""Compare stored DOUBLE inputs with stored DOUBLE snapshot inputs.

The old comparison read an intermediate GROUPBY/SUMX expression. Materialize
that native business grouping once at refresh, typed DOUBLE, before exact
comparison. No tolerance, amount, blank rule or fallback is changed.
"""
import json
from pathlib import Path
import shutil

import probe
import regression
import snapshot_cells

ACTUAL='fm_current_monthly'


def patch(database):
    tables={t['name']:t for t in database['model']['tables']}
    if ACTUAL in tables:raise ValueError('Current monthly reference already installed')
    source=tables[snapshot_cells.HEALTH]['partitions'][0]['source']
    expression=source['expression'];split=expression.index('VAR _expected=')
    compute=expression[:split]
    fields=[('SourceID','string','ID'),('Sector','string','Sector'),('Month','int64','Month'),
        ('Metric','string','Metric'),('Display','string','Display'),('Amount','double','A')]
    current={'name':ACTUAL,'isHidden':True,'columns':[{'name':n,'dataType':kind,'type':'calculatedTableColumn',
        'sourceColumn':'['+n+']','summarizeBy':'none'} for n,kind,_ in fields],
        'partitions':[{'name':ACTUAL,'mode':'import','source':{'type':'calculated','expression':compute+
            'RETURN SELECTCOLUMNS(_actual,'+','.join(json.dumps(n)+',['+old+']' for n,_,old in fields)+')'}}]}
    database['model']['tables'].append(current)
    source['expression']="VAR _actual=SELECTCOLUMNS('"+ACTUAL+"',"+','.join(json.dumps(old)+",'"+ACTUAL+"'["+n+']' for n,_,old in fields)+')\n'+expression[split:]
    return database


def build(destination,source):
    if destination.exists():raise ValueError('Preserve stored DOUBLE comparison attempt')
    bound=regression.checked(source)
    if bound.get('Prototype')!='rational-validated-snapshot':raise ValueError('Require exact current snapshot')
    db=patch(json.loads((source/'candidate.json').read_text()))
    destination.mkdir(parents=True);(destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    for n in ('baseline.json','queries.json','expected.json','preparation.json','native-preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**bound,'Files':files,'Prototype':'stored-double-snapshot',
        'ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'CompanyDeployment':False,
        'ExactComparison':'Materialized native DOUBLE inputs against stored prepared DOUBLE inputs; no tolerance.'},indent=2))
    return {'Directory':str(destination),'Queries':26}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:3])),indent=2))
