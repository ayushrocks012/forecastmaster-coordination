# Developer-only synthetic qualification. Supply a task-owned Desktop engine port.
param([Parameter(Mandatory=$true)][int]$Port,[Parameter(Mandatory=$true)][string]$FixtureDirectory)
$ErrorActionPreference='Stop'
$bin='C:\Program Files\Microsoft Power BI Desktop\bin'
[Reflection.Assembly]::LoadFrom((Join-Path $bin 'Microsoft.PowerBI.Tabular.dll'))|Out-Null
[Reflection.Assembly]::LoadFrom((Join-Path $bin 'Microsoft.PowerBI.AdomdClient.dll'))|Out-Null
$db=[Microsoft.AnalysisServices.Tabular.JsonSerializer]::DeserializeDatabase([IO.File]::ReadAllText((Join-Path $FixtureDirectory 'synthetic-model.json')))
if($db.Name -notlike 'ForecastMasterNativeSynthetic*'){throw 'Refusing a non-synthetic fixture.'}
foreach($t in $db.Model.Tables){foreach($p in $t.Partitions){if($p.Source -isnot [Microsoft.AnalysisServices.Tabular.CalculatedPartitionSource]){throw 'All fixture partitions must be calculated.'}}}
$db.Name='ForecastMasterNativeSynthetic-'+[guid]::NewGuid().ToString('N');$db.ID=$db.Name
$out=Join-Path (Join-Path $FixtureDirectory 'engine-results') $db.Name
New-Item -ItemType Directory -Path $out|Out-Null
$s=New-Object Microsoft.AnalysisServices.Tabular.Server
$s.Connect("Data Source=localhost:$Port")
try {
 if($s.Databases.ContainsName($db.Name)){throw 'Unexpected synthetic ID collision.'}
 $s.Databases.Add($db);$db.Update([Microsoft.AnalysisServices.UpdateOptions]::ExpandFull)
 $db.Model.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full);$null=$db.Model.SaveChanges()
 foreach($t in $db.Model.Tables){foreach($p in $t.Partitions){if($p.ErrorMessage){throw ('Synthetic processing error: '+$p.ErrorMessage)}}}
 foreach($stem in @('queries','fx-queries','edge-queries')){
  $inputPath=Join-Path $FixtureDirectory ($stem+'.json');if(!(Test-Path $inputPath)){throw ('Missing '+$inputPath)}
  $c=New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$Port;Initial Catalog=$($db.Name)")
  $c.Open();$results=@()
  try {
   foreach($q in (Get-Content $inputPath -Raw|ConvertFrom-Json)){
    $cmd=$c.CreateCommand();$cmd.CommandText=$q.query;$cmd.CommandTimeout=120
    try {
     $r=$cmd.ExecuteReader();$rows=@()
     try {while($r.Read()){$row=[ordered]@{};for($i=0;$i -lt $r.FieldCount;$i++){$row[$r.GetName($i)]=if($r.IsDBNull($i)){$null}else{$r.GetValue($i)}};$rows+=,$row}}finally{$r.Close()}
     $results+=@{name=$q.name;rows=$rows}
    }catch{$results+=@{name=$q.name;error=$_.Exception.Message}}
   }
  }finally{$c.Close()}
  ConvertTo-Json -InputObject @($results) -Depth 20|Set-Content -Encoding UTF8 (Join-Path $out ($stem+'-results.json'))
 }
 Write-Output ('Synthetic native results: '+$out)
 Write-Output 'Run all three Python verifiers. Query success alone does not establish matching arithmetic or native UI behavior.'
}finally{$s.Disconnect()}
