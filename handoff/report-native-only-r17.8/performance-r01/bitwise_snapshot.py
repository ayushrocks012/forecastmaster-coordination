"""Exact native IEEE64 validation for the declared stored DOUBLE inputs.

Check all keys, null states, CLR types and all64 bits, not a tolerance. Keep the
old DAX comparator as a diagnostic. The immutable SAMPLE starts unverified;
only its task-owned refresh harness may set its matching validation row after
checking every pair. Company/live Direct Lake integration remains unqualified.
"""
import json
from pathlib import Path
import shutil

import cache_prepare
import probe
import regression
import snapshot_cells

TABLE='fm_snapshot_validation'

CHECK=r'''
 $nativeSource=@"
using System;
using System.Collections.Generic;
using System.Globalization;
using Microsoft.AnalysisServices.AdomdClient;
public static class R178ExactInput {
 public static long[] Verify(string connectionString,string dax,long expected) {
  long count=0,nonblank=0,blank=0;
  var keys=new HashSet<string>();
  using(var connection=new AdomdConnection(connectionString)) {
   connection.Open(); using(var command=connection.CreateCommand()) {
    command.CommandText=dax;command.CommandTimeout=60;
    using(var reader=command.ExecuteReader()) {
     if(reader.FieldCount!=7 || reader.GetFieldType(5)!=typeof(double) || reader.GetFieldType(6)!=typeof(double))
      throw new InvalidOperationException("Exact check requires declared DOUBLE operands.");
     while(reader.Read()) {
      string key="";
      for(int i=0;i<5;i++) { if(reader.IsDBNull(i))throw new InvalidOperationException("Missing input key.");
       string part=Convert.ToString(reader.GetValue(i),CultureInfo.InvariantCulture);
       key+=part.Length.ToString(CultureInfo.InvariantCulture)+":"+part;
      }
      if(!keys.Add(key))throw new InvalidOperationException("Duplicate exact input key.");
      bool a=reader.IsDBNull(5),b=reader.IsDBNull(6);
      if(a!=b)throw new InvalidOperationException("Exact blank-state mismatch; readiness refused.");
      if(!a) {
       double x=reader.GetDouble(5),y=reader.GetDouble(6);
       if(Double.IsNaN(x)||Double.IsInfinity(x)||Double.IsNaN(y)||Double.IsInfinity(y)||
          BitConverter.DoubleToInt64Bits(x)!=BitConverter.DoubleToInt64Bits(y))
        throw new InvalidOperationException("Exact DOUBLE bits differ; readiness refused.");
       nonblank++;
      } else blank++;
      count++;
     }
    }
   }
  }
  if(count!=expected)throw new InvalidOperationException("Incomplete exact input population.");
  return new long[]{count,nonblank,blank};
 }
}
"@
 Add-Type -TypeDefinition $nativeSource -ReferencedAssemblies @((Join-Path $bin 'Microsoft.PowerBI.AdomdClient.dll'),'System.Data.dll')
 $exactConnection="Data Source=localhost:$port;Initial Catalog=$($names['candidate'])"
 $exactQuery=[IO.File]::ReadAllText((Join-Path $FixtureDirectory 'bitwise-query.dax'))
 $exact=[R178ExactInput]::Verify($exactConnection,$exactQuery,504000)
 $candidate=$server.Databases.FindByName($names['candidate'])
 if(!$candidate -or $candidate.Name -notlike 'ForecastMasterNativeSynthetic*'){throw 'Refuse non-synthetic validation write.'}
 $verification=$candidate.Model.Tables.Find('fm_snapshot_validation')
 $verification.Partitions[0].Source.Expression=[IO.File]::ReadAllText((Join-Path $FixtureDirectory 'verified-control.dax'))
 $verification.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
 $candidate.Model.Tables.Find('fm_serving_health').RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
 $null=$candidate.Model.SaveChanges()
 $again=[R178ExactInput]::Verify($exactConnection,$exactQuery,504000)
 @{Stage='NATIVE_DOUBLE_BITS_AND_KEYS_EXACT';Rows=$again[0];Nonblank=$again[1];Blank=$again[2];Passes=2;Tolerance=0;AmountsPrinted=$false;Scope='Frozen calculated SAMPLE; not a company/live refresh controller'} |
  ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $FixtureDirectory 'native-bitwise-proof.json')
 [IO.File]::WriteAllText((Join-Path $FixtureDirectory 'verified-candidate.json'),[Microsoft.AnalysisServices.Tabular.JsonSerializer]::SerializeDatabase($candidate))
 Write-Output ('Exact native DOUBLE validation completed twice: '+$exact[0]+' keys; no values printed.')
'''


def query(health):
    prefix=health[:health.index('VAR _scope=')]
    keys='"ID",[ID]&"","S",[Sector]&"","M",[Month]+0,"Metric",[Metric]&"","Display",[Display]&"",'
    return 'DEFINE\n'+prefix+'''VAR _a=SELECTCOLUMNS(_actual,'''+keys+'''"Actual",CONVERT([A],DOUBLE))
VAR _e=SELECTCOLUMNS(_expected,'''+keys+'''"Expected",CONVERT([A],DOUBLE))
VAR _both=NATURALINNERJOIN(_a,_e)
EVALUATE SELECTCOLUMNS(_both,"ID",[ID],"S",[S],"M",[M],"Metric",[Metric],"Display",[Display],"Actual",[Actual],"Expected",[Expected])'''


def build(destination,source):
    if destination.exists():raise ValueError('Preserve exact-bit snapshot attempt')
    bound=regression.checked(source)
    if bound.get('Prototype')!='explicit-double-snapshot':raise ValueError('Require explicit stored DOUBLE prototype')
    db=json.loads((source/'candidate.json').read_text());health=next(t for t in db['model']['tables'] if t['name']==snapshot_cells.HEALTH)
    text=health['partitions'][0]['source']['expression'];dax=query(text)
    marker='INT(_amounts&&_keys&&_cuts&&_cal&&_coverage&&_share)'
    if text.count(marker)!=1 or text.count('"Amounts",INT(_amounts)')!=1:raise ValueError('Unknown exact health contract')
    text=text.replace(marker,"INT(SUM('"+TABLE+"'[Verified])=1&&_keys&&_cuts&&_cal&&_coverage&&_share)")
    text=text.replace('"Amounts",INT(_amounts)',"\"Amounts\",INT(SUM('"+TABLE+"'[Verified])=1),\"DaxDiagnostic\",INT(_amounts)")
    health['partitions'][0]['source']['expression']=text
    health['columns'].append({'name':'DaxDiagnostic','dataType':'int64','type':'calculatedTableColumn','sourceColumn':'[DaxDiagnostic]','summarizeBy':'none'})
    def control(value):return cache_prepare.table(TABLE,[('Verified','int64'),('InputSHA256','string')],[(value,bound['Files']['candidate.json'])])
    db['model']['tables'].append(control(0))
    destination.mkdir(parents=True);(destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    (destination/'bitwise-query.dax').write_text(dax)
    (destination/'verified-control.dax').write_text(control(1)['partitions'][0]['source']['expression'])
    for n in ('baseline.json','queries.json','expected.json','preparation.json','native-preparation.json','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    runner=(source/'run_profile.ps1').read_text();marker=' $traceSource=@"'
    if runner.count(marker)!=1:raise ValueError('Unknown exact native runner')
    (destination/'run_profile.ps1').write_text(runner.replace(marker,CHECK+'\n'+marker))
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**bound,'Files':files,'Prototype':'native-bitwise-snapshot',
        'ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'CompanyDeployment':False,
        'ExactInputGate':'Every key unique, same blanks, CLR Double type and exact64bits,504000 pairs twice; no tolerance.',
        'Control':'Initially0; set only inside task-owned frozen model after exact check; coherent snapshot only; not a live Direct Lake controller.'},indent=2))
    return {'Directory':str(destination),'Queries':26,'ExactInputPairs':504000}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:3])),indent=2))
