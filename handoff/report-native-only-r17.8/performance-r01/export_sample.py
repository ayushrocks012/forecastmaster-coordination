"""Stream calculated SAMPLE facts for independent preparation-time experiments.

Only a frozen fabricated model is admitted. A task-owned engine is used and
closed; no existing Desktop, credentials, Fabric or company source is queried.
"""
import hashlib
import json
from pathlib import Path
import shutil

import regression

HERE=Path(__file__).resolve().parent

EXPORTS={
    'facts': '''EVALUATE SELECTCOLUMNS('fm_review_facts',
 "SourceID",[SourceRevisionID],"Sector",[Sector],"Month",DATEDIFF(DATE(2000,1,1),[Month],MONTH),
 "Component",[ComponentKey],"Channel",[Channel],"SubChannel",[SubChannel],"Amount",[Amount],"MissingCells",[MissingCells])''',
    'files': '''EVALUATE SELECTCOLUMNS('fm_native_files',
 "SourceID",[SourceRevisionID],"Country",[Country],"Driver",[GrowthDriver],
 "IMS",DATEDIFF(DATE(2000,1,1),[IMSActualsThrough],MONTH),
 "EF",DATEDIFF(DATE(2000,1,1),[ExFactoryActualsThrough],MONTH),
 "Currency",LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],[Country]))''',
    'catalog': '''EVALUATE SELECTCOLUMNS(FILTER('fm_native_catalog',[RowID] IN {"market","abbott","share","pi","net"}),
 "Metric",[RowID],"Display",[Display],"Component",[Component],"Denominator",[Denominator],"Channel",[Channel],"SubChannel",[SubChannel])'''
}

STREAM=r'''
 $streamSource=@"
using System;
using System.IO;
using System.Text;
using System.Globalization;
using Microsoft.AnalysisServices.AdomdClient;
public static class R178StreamCsv {
 static string Q(object v) {
  if(v==null || v==DBNull.Value) return "";
  string s = v is double ? ((double)v).ToString("R",CultureInfo.InvariantCulture) : Convert.ToString(v,CultureInfo.InvariantCulture);
  return "\""+s.Replace("\"","\"\"")+"\"";
 }
 public static long Dump(AdomdConnection connection,string sql,string path) {
  using(var command=connection.CreateCommand()) {
   command.CommandText=sql;command.CommandTimeout=60;
   using(var reader=command.ExecuteReader())
   using(var stream=new StreamWriter(File.Open(path,FileMode.CreateNew,FileAccess.Write,FileShare.None),new UTF8Encoding(false))) {
    string[] fields=new string[reader.FieldCount];
    for(int i=0;i<fields.Length;i++) fields[i]=Q(reader.GetName(i));
    stream.WriteLine(String.Join(",",fields));long rows=0;
    while(reader.Read()) {
     for(int i=0;i<fields.Length;i++) fields[i]=Q(reader.GetValue(i));
     stream.WriteLine(String.Join(",",fields));rows++;
    }
    return rows;
   }
  }
 }
}
"@
 Add-Type -TypeDefinition $streamSource -ReferencedAssemblies @((Join-Path $bin 'Microsoft.PowerBI.AdomdClient.dll'),'System.Data.dll')
 $exports=Get-Content (Join-Path $FixtureDirectory 'queries.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $counts=@{}
 $connection=New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$port;Initial Catalog=$($names['candidate'])")
 try {
  $connection.Open()
  foreach($export in $exports) {
   $watch=[Diagnostics.Stopwatch]::StartNew()
   $rows=[R178StreamCsv]::Dump($connection,$export.query,(Join-Path $FixtureDirectory ($export.name+'.csv')))
   $counts[$export.name]=@{Rows=$rows;ElapsedMs=$watch.ElapsedMilliseconds}
   Write-Output ('Completed calculated-only export '+$export.name+': '+$rows+' rows')
  }
 }finally{$connection.Close()}
 ConvertTo-Json -InputObject $counts -Depth 5|Set-Content -Encoding UTF8 (Join-Path $FixtureDirectory 'exports.json')
'''


def build(destination, source, runner):
    if destination.exists():
        raise ValueError('Preserve previous export')
    regression.checked(source);regression.checked(runner)
    db=json.loads((source/'candidate.json').read_text())
    if not db['name'].startswith('ForecastMasterNativeSynthetic') or any(
        p['source']['type']!='calculated' for t in db['model']['tables'] for p in t.get('partitions',[])):
        raise ValueError('Calculated fabricated model only')
    base=(runner/'run_profile.ps1').read_text()
    start,end=base.index(' $traceSource=@"'),base.index('}finally{\n if($trace')
    script=base[:start]+STREAM+base[end:]
    script=script.replace("@('baseline','candidate')","@('candidate')")
    destination.mkdir(parents=True)
    shutil.copy2(source/'candidate.json',destination/'candidate.json')
    shutil.copy2(source/'launch_synthetic_engine.ps1',destination/'launch_synthetic_engine.ps1')
    shutil.copy2(Path(__file__),destination/'export_sample.py')
    (destination/'run_profile.ps1').write_text(script)
    (destination/'queries.json').write_text(json.dumps([{'name':n,'query':q} for n,q in EXPORTS.items()]))
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'FabricatedOnly':True,
        'ExpectedFactRows':504000,'SourceModelSHA256':files['candidate.json']},indent=2))
    return {'Directory':str(destination),'ExpectedFacts':504000}


def verify(directory):
    bound=regression.checked(directory)
    rows=json.loads((directory/'exports.json').read_text(encoding='utf-8-sig'))
    if set(rows)!=set(EXPORTS) or rows['facts']['Rows']!=504000 or rows['files']['Rows']!=20:
        raise AssertionError('Changed source population')
    return {'Stage':'LOCAL_CALCULATED_SAMPLE_FACTS_EXPORTED','Exports':rows,
        'SourceHashes':bound['Files'],
        'ExportHashes':{n:hashlib.sha256((directory/(n+'.csv')).read_bytes()).hexdigest() for n in EXPORTS},
        'TaskOwnedEngineClosed':True,'CompanyData':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
