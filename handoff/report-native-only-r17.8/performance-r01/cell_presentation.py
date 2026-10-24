"""Format the actual numeric result; colour its exact percentage sibling.

Avoid repeating the full eligibility/fallback expression inside presentation.
The displayed value still enforces every guard. Percent sibling uses the same
value measure, period, sources and correct aggregate Share calculation.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import cell_fact
import prepared
import probe
import regression


def patch(database):
    fixed=deepcopy(database);m=prepared.adapter.planning.measures(fixed)
    fmt=m['N Summary Cell']['formatStringDefinition']['expression']
    if fmt.count('SELECTEDMEASURE()')!=1:raise ValueError('Unknown complete cell format')
    m[cell_fact.VALUE]['formatStringDefinition']['expression']=fmt.replace('SELECTEDMEASURE()','['+cell_fact.VALUE+']')
    m[cell_fact.COLOR]['expression']='''VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])
VAR _window=SELECTEDVALUE('fm_native_columns'[Window])
RETURN IF(HASONEVALUE('fm_native_metric'[RowID])&&HASONEVALUE('fm_native_columns'[ColumnKey])
 &&_key<>"plan"&&_window IN VALUES('fm_native_trend'[Window]),
 VAR _pctkey=FORMAT(_window,"0")&":pct"
 VAR _value=CALCULATE(['''+cell_fact.VALUE+'''],REMOVEFILTERS('fm_native_columns'),
 TREATAS({_pctkey},'fm_native_columns'[ColumnKey]))
 RETURN IF(NOT ISBLANK(_value),VAR _size=ABS(_value)
 RETURN SWITCH(TRUE(),_size<=0.05,"#E5F2E6",_size<=0.10,"#FFF3CD","#F9E1E3")))'''
    return fixed


def build(destination,source):
    if destination.exists():raise ValueError('Preserve actual-value presentation probe')
    bound=regression.checked(source)
    if bound.get('Prototype') not in {'prepared-executive-cells','shared-prepared-cell-guard'}:
        raise ValueError('Unknown prepared-cell parent')
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(patch(json.loads((source/'candidate.json').read_text())),ensure_ascii=False))
    for n in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**bound,'Files':files,'Prototype':'actual-value-presentation',
        'ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'CompanyDeployment':False},indent=2))
    return {'Directory':str(destination),'Queries':len(json.loads((source/'queries.json').read_text()))}


if __name__=='__main__':
    import sys
    print(json.dumps(cell_fact.verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
