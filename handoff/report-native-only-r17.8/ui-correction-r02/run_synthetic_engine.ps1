# R02 checkpointed task-owned fabricated model qualification. Never attaches an existing Desktop engine.
param([Parameter(Mandatory=$true)][string]$FixtureDirectory)
$ErrorActionPreference='Stop'
$bin='C:\Program Files\Microsoft Power BI Desktop\bin'
$work=Join-Path $env:TEMP ('ForecastMasterR178Synthetic-'+[guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $work
$listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0)
$listener.Start();$listenPort=$listener.LocalEndpoint.Port;$listener.Stop()
$config=@"
<ConfigurationSettings>
<DataDir>$work</DataDir><TempDir>$work</TempDir><LogDir>$work</LogDir><BackupDir>$work</BackupDir>
<DeploymentMode>2</DeploymentMode><RecoveryModel>1</RecoveryModel><DisklessModeRequested>1</DisklessModeRequested>
<CleanDataFolderOnStartup>1</CleanDataFolderOnStartup><Port>$listenPort</Port><PrivateProcess>$PID</PrivateProcess><InstanceVisible>0</InstanceVisible>
<Network><ListenOnlyOnLocalConnections>1</ListenOnlyOnLocalConnections></Network>
<Feature><DynamicFormatStringDefinitionEnabled>1</DynamicFormatStringDefinitionEnabled><ManagedCodeEnabled>1</ManagedCodeEnabled></Feature>
<DAX><EnableExtensionFunctions>1</EnableExtensionFunctions><ExtensionDir>$bin</ExtensionDir><ExtensionLibraries>Microsoft.InfoNav.Analytics.AnalyticsEngine.dll;AI\Microsoft.AI.Dax.Extensions.dll</ExtensionLibraries></DAX>
</ConfigurationSettings>
"@
[IO.File]::WriteAllText((Join-Path $work 'msmdsrv.ini'),$config)
$engine=$null;$server=$null;$results=@();$names=@{};$ordinal=0
try {
 $engine=Start-Process -FilePath (Join-Path $bin 'msmdsrv.exe') -ArgumentList @('-c','-s',('"'+$work+'"')) -PassThru -WindowStyle Hidden
 $until=(Get-Date).AddSeconds(45);$portFile=Join-Path $work 'msmdsrv.port.txt'
 while(!(Test-Path $portFile)) {if($engine.HasExited){throw 'Task-owned engine exited.'};if((Get-Date) -gt $until){throw 'Task-owned engine startup timed out.'};Start-Sleep -Milliseconds 250}
 $port=[int]([IO.File]::ReadAllText($portFile,[Text.Encoding]::Unicode).Trim([char]0).Trim())
 [Reflection.Assembly]::LoadFrom((Join-Path $bin 'Microsoft.PowerBI.Tabular.dll'))|Out-Null
 [Reflection.Assembly]::LoadFrom((Join-Path $bin 'Microsoft.PowerBI.AdomdClient.dll'))|Out-Null
 $server=New-Object Microsoft.AnalysisServices.Tabular.Server;$server.Connect("Data Source=localhost:$port")
 foreach($kind in @('baseline','candidate')) {
  $db=[Microsoft.AnalysisServices.Tabular.JsonSerializer]::DeserializeDatabase([IO.File]::ReadAllText((Join-Path $FixtureDirectory ($kind+'.json'))))
  if($db.Name -notlike 'ForecastMasterNativeSynthetic*'){throw 'Refusing non-synthetic fixture.'}
  foreach($t in $db.Model.Tables){foreach($p in $t.Partitions){if($p.Source -isnot [Microsoft.AnalysisServices.Tabular.CalculatedPartitionSource]){throw 'Refusing a non-calculated fixture partition.'}}}
  $db.Name='ForecastMasterNativeSynthetic-'+$kind+'-'+[guid]::NewGuid().ToString('N');$db.ID=$db.Name;$names[$kind]=$db.Name
  $server.Databases.Add($db);$db.Update([Microsoft.AnalysisServices.UpdateOptions]::ExpandFull)
  $db.Model.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full);$null=$db.Model.SaveChanges()
  foreach($t in $db.Model.Tables){foreach($p in $t.Partitions){if($p.ErrorMessage){throw ('Synthetic processing failed: '+$p.ErrorMessage)}}}
  Write-Output ('Fabricated '+$kind+' model processed.')
 }
 foreach($case in (Get-Content (Join-Path $FixtureDirectory 'queries.json') -Raw|ConvertFrom-Json)) {
  $ordinal+=1; Write-Output ("Starting synthetic query "+$ordinal+": "+$case.name+" ["+$case.model+"]")
  $connection=New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$port;Initial Catalog=$($names[$case.model])")
  try {
   $connection.Open();$command=$connection.CreateCommand();$command.CommandText=$case.query;$command.CommandTimeout=60
   $watch=[Diagnostics.Stopwatch]::StartNew();$reader=$command.ExecuteReader();$rows=@()
   try {while($reader.Read()){$row=[ordered]@{};for($i=0;$i -lt $reader.FieldCount;$i++){$row[$reader.GetName($i)]=if($reader.IsDBNull($i)){$null}else{$reader.GetValue($i)}};$rows+=,$row}}finally{$reader.Close()}
   $results+=@{name=$case.name;model=$case.model;elapsedMs=$watch.ElapsedMilliseconds;rows=$rows}
  }catch{$results+=@{name=$case.name;model=$case.model;error=$_.Exception.Message}}finally{$connection.Close()}
  ConvertTo-Json -InputObject @($results) -Depth 30|Set-Content -Encoding UTF8 (Join-Path $FixtureDirectory 'results.partial.json')
  Write-Output ("Completed synthetic query "+$ordinal)
 }
 ConvertTo-Json -InputObject @($results) -Depth 30|Set-Content -Encoding UTF8 (Join-Path $FixtureDirectory 'results.json')
 Write-Output ('Synthetic query executions: '+$results.Count)
}finally{
 if($server){$server.Disconnect()}
 if($engine -and !$engine.HasExited){Stop-Process -Id $engine.Id -ErrorAction SilentlyContinue}
 Write-Output ('Task-owned engine stopped; fabricated evidence directory: '+$work)
}
