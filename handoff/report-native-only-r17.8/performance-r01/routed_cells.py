"""Route fast and fallback cells through mutually exclusive zero/one-row sets.

The eligibility expression is unchanged. An eligible BLANK remains BLANK;
missing/unsupported cells still evaluate the complete original calculation.
"""
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil

import cell_fact
import prepared
import probe
import regression
import shared_gate


def patch(database):
    fixed=deepcopy(database);m=prepared.adapter.planning.measures(fixed)
    if shared_gate.GATE not in m:raise ValueError('Require exact shared admission')
    m[cell_fact.VALUE]['expression']='''VAR _display=[N Display]
VAR _scenario=IF(SELECTEDVALUE('fm_native_lines'[Chart])="demand",BLANK(),
 COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario])))
VAR _use=['''+shared_gate.GATE+''']=1
VAR _fast=FILTER({1},_use)
VAR _slow=FILTER({1},NOT _use)
RETURN COALESCE(SUMX(_fast,'''+cell_fact.filtered('Amount',True)+'''),
 SUMX(_slow,[N Summary Cell]))'''
    return fixed


def eligibility_query(q):
    begin=q.index('"N_Summary_Cell",');end=q.index("'fm_native_measures'[N GM Summary Color])",begin)+len("'fm_native_measures'[N GM Summary Color])")
    q=q[:begin]+'"G",['+shared_gate.GATE+']'+q[end:]
    q=q.replace('EVALUATE __DS0Core', '''EVALUATE ROW("EligibleLeaves",COUNTROWS(FILTER(__DS0Core,[G]=1&&NOT [IsDM1Total])),
 "EligibleAggregates",COUNTROWS(FILTER(__DS0Core,[G]=1&&[IsDM1Total])))''')
    cleaned=re.sub(r'/\*.*?\*/|"(?:""|[^"])*"|\'(?:\'\'|[^\'])*\'', '', q, flags=re.S)
    balance=0
    for char in cleaned:
        balance+=(char=='(')-(char==')')
        if balance<0:raise ValueError('Generated diagnostic has extra closing parenthesis')
    if balance:raise ValueError('Generated diagnostic is not balanced')
    return q


def build(destination,source):
    if destination.exists():raise ValueError('Preserve routed-cell attempt')
    b=regression.checked(source)
    if b.get('Prototype')!='actual-value-presentation':raise ValueError('Unknown exact presentation parent')
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(patch(json.loads((source/'candidate.json').read_text())),ensure_ascii=False))
    for n in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    queries=json.loads((destination/'queries.json').read_text())
    q=next(q['query'] for q in queries if q['name']=='share-expanded/full-core/candidate')
    q=eligibility_query(q)
    queries.append({'name':'eligibility-count','model':'candidate','query':q})
    (destination/'queries.json').write_text(json.dumps(queries))
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**b,'Files':files,'Prototype':'routed-prepared-cells',
        'ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'GuardAndFallbackRetained':True,
        'CompanyDeployment':False},indent=2))
    return {'Directory':str(destination),'Queries':len(queries)}


if __name__=='__main__':
    import sys
    print(json.dumps(cell_fact.verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
