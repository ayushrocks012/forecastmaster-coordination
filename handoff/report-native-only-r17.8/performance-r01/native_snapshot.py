"""Prepare period cells from actual native monthly grouping, not an oracle.

Preserve the engine's grouped input doubles, blank bad groups and all source
identities. Recompute fits and weighted period Share from those monthly inputs.
Exact refresh comparison and complete raw fallback remain unchanged.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import time

import binary_snapshot
import cache_prepare
import leaf_prepare
import native_monthly_export
import precise_snapshot
import prepared
import probe
import regression


def prepare(export):
    import pandas as pd
    start=time.monotonic();proof=native_monthly_export.verify(export)
    def read(path):
        if path.name!='facts.csv':return precise_snapshot.read_round_trip(path)
        data=pd.read_csv(export/'monthly.csv',keep_default_na=False,float_precision='round_trip',na_values={'[Amount]':['']})
        data.columns=[c.removeprefix('[').removesuffix(']') for c in data.columns]
        catalog=precise_snapshot.read_round_trip(export/'catalog.csv')
        defs=catalog[catalog.Metric.isin(('market','abbott','pi','net'))][['Metric','Display','Component','Channel','SubChannel']]
        ef=pd.DataFrame([{'Metric':'ef','Display':d,'Component':'ef-ads-'+d.lower(),'Channel':'*','SubChannel':'*'} for d in ('Units','Value')])
        data=data.merge(pd.concat([defs,ef]),on=['Metric','Display'],validate='many_to_one')
        if len(data)!=504000:raise ValueError('Changed native monthly population')
        data['MissingCells']=data.Amount.isna().astype(int)
        return data[['SourceID','Sector','Month','Component','Channel','SubChannel','Amount','MissingCells']]
    cache=prepared.load('native_monthly_private_cache',Path(cache_prepare.__file__))
    cache.read=read;cache.export_sample=native_monthly_export
    monthly=cache.prepare(export)
    def cached_prepare(path):
        if path.resolve()!=export.resolve():raise ValueError('Changed native export')
        return monthly
    cache.prepare=cached_prepare
    leaf=prepared.load('native_monthly_private_leaf',Path(leaf_prepare.__file__));leaf.cache_prepare=cache
    kpi=leaf.prepare(export)
    tables=cache.tables(monthly)[:2]+leaf.tables(kpi)
    for table in tables:
        if table['name'] in {'fm_cache_monthly','fm_leaf_kpi'}:binary_snapshot.encode_table(table)
    return tables,{'SourceExport':proof,'PreparationMs':round((time.monotonic()-start)*1000),
        'LeafRows':len(kpi['rows']),'Series':len(kpi['dimension']),
        'Method':'Actual native monthly grouping; round-trip parse; complete-history fits and weighted Share; binary local DOUBLE transport.',
        'ExpectedResultGeneratorUsed':False,'ThresholdsRelaxed':False}


def build(destination,source,export):
    if destination.exists():raise ValueError('Preserve native monthly serving attempt')
    bound=regression.checked(source);eb=regression.checked(export)
    if bound.get('Prototype')!='binary-validated-snapshot' or eb.get('SourceModelSHA256')!=bound['Files']['candidate.json']:
        raise ValueError('Native export does not match the source model exactly')
    newtables,receipt=prepare(export)
    db=deepcopy(json.loads((source/'candidate.json').read_text()));current={t['name']:t for t in db['model']['tables']}
    for table in newtables:current[table['name']]['partitions']=table['partitions']
    regression.checked(export)
    destination.mkdir(parents=True);(destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    for n in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    (destination/'native-preparation.json').write_text(json.dumps(receipt,indent=2))
    for path in (Path(__file__),Path(binary_snapshot.__file__)):
        shutil.copy2(path,destination/path.name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**bound,'Files':files,'Prototype':'native-grouped-snapshot',
        'ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'NativeExportSHA256':probe.digest(export/'FROZEN-INPUTS.json'),
        'CompanyDeployment':False,'ExactReadinessGateUnchanged':True},indent=2))
    return {'Directory':str(destination),'PreparationMs':receipt['PreparationMs'],'Queries':26}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:4])),indent=2))
