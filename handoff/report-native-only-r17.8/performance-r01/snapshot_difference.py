"""Read-only fabricated diagnostic of refresh versus query input comparison."""
import json
from pathlib import Path
import shutil

import export_sample
import prepared
import probe
import regression
import snapshot_cells


def build(destination,source,runner):
    if destination.exists():raise ValueError('Preserve refresh/query diagnostic')
    regression.checked(source)
    prefix=snapshot_cells.health()['partitions'][0]['source']['expression'].split('RETURN ROW(',1)[0]
    # There are no earlier RETURN ROW expressions in the health source.
    keys='"ID",[ID]&"","S",[Sector]&"","M",[Month]+0,"Metric",[Metric]&"","Display",[Display]&"",'
    join='''VAR _a=SELECTCOLUMNS(_actual,'''+keys+'''"Actual",[A])
VAR _e=SELECTCOLUMNS(_expected,'''+keys+'''"Expected",[A])
VAR _both=NATURALINNERJOIN(_a,_e)
VAR _diff=FILTER(_both,ISBLANK([Actual])<>ISBLANK([Expected])||[Actual]<>[Expected])
'''
    expressions={'counts':'DEFINE\n'+prefix+join+'''EVALUATE ROW(
 "RefreshReady",SUM('fm_serving_health'[Ready]),"ActualOnly",COUNTROWS(EXCEPT(_actual,_expected)),
 "ExpectedOnly",COUNTROWS(EXCEPT(_expected,_actual)),"Actual",COUNTROWS(_actual),"Expected",COUNTROWS(_expected),
 "Joined",COUNTROWS(_both),"NumericDifferent",COUNTROWS(_diff),
 "BlankDifferent",COUNTROWS(FILTER(_diff,ISBLANK([Actual])<>ISBLANK([Expected]))),
 "MaxAbsoluteDelta",MAXX(_diff,ABS([Actual]-[Expected])))''',
        'different':'DEFINE\n'+prefix+join+'''EVALUATE TOPN(20,_diff,[ID],ASC,[S],ASC,[M],ASC,[Metric],ASC,[Display],ASC)'''}
    module=prepared.load('snapshot_difference_private_export',Path(export_sample.__file__));module.EXPORTS=expressions
    module.build(destination,source,runner)
    script=(destination/'run_profile.ps1').read_text().replace('.ToString("R",CultureInfo.InvariantCulture)',
        '.ToString("G17",CultureInfo.InvariantCulture)')
    (destination/'run_profile.ps1').write_text(script)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    binding=json.loads((destination/'FROZEN-INPUTS.json').read_text());binding['Files']={p.name:probe.digest(p) for p in destination.iterdir() if p.name!='FROZEN-INPUTS.json'}
    binding.update(Prototype='snapshot-difference-diagnostic',CompanyData=False,Deployable=False,DoubleFormat='G17')
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps(binding,indent=2))
    return {'Directory':str(destination),'Exports':2}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:4])),indent=2))
