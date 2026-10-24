"""Diagnose exact monthly snapshot mismatch; fabricated native model only."""
import json
from pathlib import Path
import shutil

import cache_prepare
import precise_snapshot
import probe
import regression
import snapshot_cells


def build(destination,source,export):
    if destination.exists():raise ValueError('Preserve precision diagnostic')
    bound=regression.checked(source);regression.checked(export)
    if bound.get('Prototype')!='precise-validated-snapshot':raise ValueError('Require exact precise model')
    db=json.loads((source/'candidate.json').read_text())
    expression=next(t for t in db['model']['tables'] if t['name']==snapshot_cells.HEALTH)['partitions'][0]['source']['expression']
    prefix=expression.rsplit('RETURN ROW(',1)[0]
    keys='"ID",[ID]&"","S",[Sector]&"","M",[Month]+0,"Metric",[Metric]&"","Display",[Display]&"",'
    join='''VAR _a=SELECTCOLUMNS(_actual,'''+keys+'''"Actual",[A])
VAR _e=SELECTCOLUMNS(_expected,'''+keys+'''"Expected",[A])
VAR _both=NATURALINNERJOIN(_a,_e)
VAR _diff=FILTER(_both,ISBLANK([Actual])<>ISBLANK([Expected])||[Actual]<>[Expected])
EVALUATE ROW("ActualRows",COUNTROWS(_a),"ExpectedRows",COUNTROWS(_e),"JoinedRows",COUNTROWS(_both),
 "Different",COUNTROWS(_diff),"BlankMismatch",COUNTROWS(FILTER(_diff,ISBLANK([Actual])<>ISBLANK([Expected]))),
 "AboveExistingNumericTolerance",COUNTROWS(FILTER(_diff,ABS([Actual]-[Expected])>MAX(1e-7,1e-9*MAX(ABS([Actual]),ABS([Expected]))))),
 "MaxAbsoluteDelta",MAXX(_diff,ABS([Actual]-[Expected])))'''
    queries=[{'name':'monthly-key-and-precision-counts','model':'candidate','query':'DEFINE\n'+prefix+join}]
    old=cache_prepare.read(export/'facts.csv');exact=precise_snapshot.read_round_trip(export/'facts.csv')
    different=old.Amount.ne(exact.Amount)&old.Amount.notna()&exact.Amount.notna()
    if not different.any():raise ValueError('Require a source parser regression example')
    row=exact[different].iloc[0];value=float(row.Amount);mantissa,den=value.as_integer_ratio();exponent=-(den.bit_length()-1)
    if abs(mantissa)>=2**53:raise ValueError('Unexpected diagnostic amount range')
    filters=["TREATAS({"+json.dumps(str(row[c]))+"},'fm_review_facts'["+target+'])' for c,target in
        [('SourceID','SourceRevisionID'),('Sector','Sector'),('Component','ComponentKey'),('Channel','Channel'),('SubChannel','SubChannel')]]
    filters.append("TREATAS({EDATE(DATE(2000,1,1),"+str(int(row.Month))+")},'fm_review_facts'[Month])")
    q="EVALUATE ROW(\"Raw\",CALCULATE(SELECTEDVALUE('fm_review_facts'[Amount]),"+','.join(filters)+'''),
 "Literal",MAXX(DATATABLE("V",DOUBLE,{{'''+format(value,'.17g')+'''}}),[V]),
 "BinaryParts",MAXX(DATATABLE("M",INTEGER,"E",INTEGER,{{'''+str(mantissa)+','+str(exponent)+'''}}),[M]*POWER(2,[E])))'''
    queries.append({'name':'native-double-constant-boundary','model':'candidate','query':q})
    destination.mkdir(parents=True);shutil.copy2(source/'candidate.json',destination/'candidate.json')
    (destination/'queries.json').write_text(json.dumps(queries));(destination/'expected.json').write_text(json.dumps({'Raw':value}))
    for n in ('run_profile.ps1','launch_synthetic_engine.ps1'):shutil.copy2(source/n,destination/n)
    script=(destination/'run_profile.ps1').read_text().replace("foreach($kind in @('baseline','candidate'))","foreach($kind in @('candidate'))")
    (destination/'run_profile.ps1').write_text(script)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Prototype':'monthly-precision-diagnostic',
        'SourceSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'ParserDifferentCount':int(different.sum()),
        'CompanyData':False,'Deployable':False},indent=2))
    return {'Directory':str(destination),'Queries':len(queries)}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:4])),indent=2))
