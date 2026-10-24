"""Export the actual native source/sector/month grouping, not an oracle.

The formula is the same refresh coherence input. Stream its native doubles and
retain raw facts/files/catalog alongside for traceability. Calculated SAMPLE
only; does not connect to company Fabric or an existing Desktop engine.
"""
import json
from pathlib import Path
import shutil

import export_sample
import prepared
import probe
import regression
import snapshot_cells


def query():
    text=snapshot_cells.health()['partitions'][0]['source']['expression']
    prefix=text[:text.index('VAR _expected=')]
    return 'DEFINE\n'+prefix+'''EVALUATE SELECTCOLUMNS(_actual,"SourceID",[ID],"Sector",[Sector],"Month",[Month],
 "Metric",[Metric],"Display",[Display],"Amount",[A])'''


def build(destination,source,runner):
    module=prepared.load('monthly_native_export_private',Path(export_sample.__file__))
    module.EXPORTS={**module.EXPORTS,'monthly':query()}
    module.build(destination,source,runner)
    script=(destination/'run_profile.ps1').read_text()
    old='.ToString("R",CultureInfo.InvariantCulture)'
    if script.count(old)!=1:raise ValueError('Unknown exact native DOUBLE exporter')
    (destination/'run_profile.ps1').write_text(script.replace(old,'.ToString("G17",CultureInfo.InvariantCulture)'))
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    bound=json.loads((destination/'FROZEN-INPUTS.json').read_text())
    bound['Files']={p.name:probe.digest(p) for p in destination.iterdir() if p.name!='FROZEN-INPUTS.json'}
    bound.update(Prototype='native-monthly-export',ExpectedMonthlyRows=504000,DoubleFormat='G17',
        Purpose='Actual native grouping; preserves native summation and bad-member semantics.')
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps(bound,indent=2))
    return {'Directory':str(destination),'Exports':4}


def verify(directory):
    bound=regression.checked(directory)
    rows=json.loads((directory/'exports.json').read_text(encoding='utf-8-sig'))
    if set(rows)!={'facts','files','catalog','monthly'} or rows['facts']['Rows']!=504000 or rows['monthly']['Rows']!=504000 or rows['files']['Rows']!=20:
        raise AssertionError('Incomplete native monthly export')
    return {'Stage':'LOCAL_NATIVE_MONTHLY_EXPORTED','Exports':rows,'SourceHashes':bound['Files'],
        'ExportHashes':{n:probe.digest(directory/(n+'.csv')) for n in rows},
        'TaskOwnedEngineClosed':True,'CompanyData':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
