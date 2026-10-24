"""Reduce normal-path source joins; keep exact R03 fallback outside this scope.

One country/cycle and one admitted source per driver lets the actual selected
scope rows map directly to prepared keys. Multi-country/cycle, legacy line,
custom catalog/channel and converted-currency contexts retain the R03 path.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import prepared
import regression

PREFIX='''VAR _sourceOK=[N Source OK]=1
VAR _row=COALESCE(SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),"market")
VAR _display=[N Display]
VAR _country=VALUES('fm_review_files'[Country])
VAR _cycles=VALUES('fm_review_files'[DemandCycle])
VAR _drivers=VALUES('fm_native_scope'[GrowthDriver])
VAR _chosen=INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))
VAR _ids=CALCULATETABLE(VALUES('fm_native_files'[SourceRevisionID]),
 TREATAS(_chosen,'fm_native_files'[SourceRevisionID]),TREATAS(_country,'fm_native_files'[Country]),
 TREATAS(_cycles,'fm_native_files'[DemandCycle]),TREATAS(_drivers,'fm_native_files'[GrowthDriver]))
VAR _records=CALCULATETABLE('fm_native_files',TREATAS(_ids,'fm_native_files'[SourceRevisionID]))
VAR _dates=SELECTCOLUMNS(_records,"Cut",IF(_row="ef",'fm_native_files'[ExFactoryActualsThrough],'fm_native_files'[IMSActualsThrough]))
VAR _validDates=COUNTROWS(FILTER(_dates,ISBLANK([Cut])||[Cut]<DATE(2000,1,1)||[Cut]>=DATE(2100,1,1)))=0
VAR _cut=IF(_sourceOK&&_validDates,MINX(_dates,[Cut]))
VAR _common=IF(_sourceOK&&_validDates&&COUNTROWS(DISTINCT(_dates))=1,MAXX(_dates,[Cut]))
VAR _pairs=CALCULATETABLE(SUMMARIZE('fm_native_scope','fm_native_scope'[SourceRevisionID],'fm_native_scope'[Sector]),
 TREATAS(_ids,'fm_native_scope'[SourceRevisionID]))
VAR _keys=CALCULATETABLE(VALUES('fm_cache_series'[Key]),TREATAS(_pairs,'fm_cache_series'[SourceID],'fm_cache_series'[Sector]))
VAR _members=COUNTROWS(_keys)
VAR _currencies=SELECTCOLUMNS(_records,"CC",LOOKUPVALUE('fm_native_currency_map'[Currency],
 'fm_native_currency_map'[Country],'fm_native_files'[Country]))
VAR _single=COUNTROWS(DISTINCT(_currencies))=1&&COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0
VAR _eligible=_sourceOK&&NOT ISBLANK(_common)&&_members>0&&_members=COUNTROWS(_pairs)
 &&HASONEVALUE('fm_review_files'[Country])&&HASONEVALUE('fm_review_files'[DemandCycle])
 &&NOT ISFILTERED('fm_native_lines')&&NOT ISFILTERED('fm_native_scenario'[Scenario])
 &&_row IN {"market","abbott","share","pi","net","ef"}&&NOT ISFILTERED('fm_review_facts')
 &&(_display="Units"||(_display="Value"&&_single&&SELECTEDVALUE('fm_native_currency'[Currency],"USD")="Local"))
'''


def patch(database):
    fixed=deepcopy(database);measures=prepared.adapter.planning.measures(fixed)
    if not any(t['name']=='fm_cache_path' for t in fixed['model']['tables']):
        raise ValueError('Require gated candidate')
    for name in ('N Plan','N Benchmark'):
        body=measures[name]['expression']
        if body.count('VAR _y=')!=1 or body.count(' VAR _cut=[N Cutoff]')!=1 or "TREATAS({INT(NOT _ready)},'fm_cache_path'[Legacy])" not in body:
            raise ValueError('Unknown gated kernel')
        tail=body[body.index('VAR _y='):].replace(' VAR _cut=[N Cutoff]','')
        marker="VAR _selectedMonths=FILTER(ALL('fm_cache_monthly'[Month]),"
        if tail.count(marker)!=1:
            raise ValueError('Unknown prepared month set')
        tail=tail.replace(marker,"VAR _axisOrdinals=SELECTCOLUMNS(ALL('fm_review_axis'[Month]),\"Ordinal\",DATEDIFF(DATE(2000,1,1),'fm_review_axis'[Month],MONTH))\n"+marker)
        tail=tail.replace("'fm_cache_monthly'[Month]>=_startOrdinal&&'fm_cache_monthly'[Month]<=_endOrdinal)",
            "'fm_cache_monthly'[Month]>=_startOrdinal&&'fm_cache_monthly'[Month]<=_endOrdinal&&'fm_cache_monthly'[Month] IN _axisOrdinals)")
        measures[name]['expression']=PREFIX+tail
    return fixed


def build(destination,source):
    if destination.exists():
        raise ValueError('Preserve previous lean test')
    binding=regression.checked(source)
    before=json.loads((source/'candidate.json').read_text())
    after=patch(before)
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(after,ensure_ascii=False))
    for name in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/name,destination/name)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**binding,'Files':files,'Prototype':'source-cache-lean-gated',
        'SourceCandidateSHA256':hashlib.sha256((source/'candidate.json').read_bytes()).hexdigest(),
        'CompanyDeployment':False},indent=2))
    return {'Directory':str(destination),'Queries':len(json.loads((source/'queries.json').read_text()))}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:3])),indent=2))
