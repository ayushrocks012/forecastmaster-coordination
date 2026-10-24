# R02 checkpointed task-owned fabricated model qualification. Never attaches an existing Desktop engine.
param([Parameter(Mandatory=$true)][string]$FixtureDirectory)
$ErrorActionPreference='Stop'
$binding=Join-Path $FixtureDirectory 'FROZEN-INPUTS.json'
if(!(Test-Path $binding)){throw 'Refuse unbound fixture; preserve failed build.'}
$hashes=(Get-Content $binding -Raw -Encoding UTF8|ConvertFrom-Json).Files
foreach($property in $hashes.PSObject.Properties){
 $file=Join-Path $FixtureDirectory $property.Name
 if(!(Test-Path $file) -or (Get-FileHash -Algorithm SHA256 $file).Hash.ToLowerInvariant() -ne $property.Value){throw 'Frozen input changed; no engine launch.'}
}
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
$engine=$null;$server=$null;$trace=$null;$results=@();$names=@{};$ordinal=0
try {
 $engine=Start-Process -FilePath (Join-Path $bin 'msmdsrv.exe') -ArgumentList @('-c','-s',('"'+$work+'"')) -PassThru -WindowStyle Hidden
 $until=(Get-Date).AddSeconds(45);$portFile=Join-Path $work 'msmdsrv.port.txt'
 while(!(Test-Path $portFile)) {if($engine.HasExited){throw 'Task-owned engine exited.'};if((Get-Date) -gt $until){throw 'Task-owned engine startup timed out.'};Start-Sleep -Milliseconds 250}
 $port=[int]([IO.File]::ReadAllText($portFile,[Text.Encoding]::Unicode).Trim([char]0).Trim())
 [Reflection.Assembly]::LoadFrom((Join-Path $bin 'Microsoft.PowerBI.Tabular.dll'))|Out-Null
 [Reflection.Assembly]::LoadFrom((Join-Path $bin 'Microsoft.PowerBI.AdomdClient.dll'))|Out-Null
 [Reflection.Assembly]::LoadFrom((Join-Path $bin 'Microsoft.PowerBI.Amo.Core.dll'))|Out-Null
 $server=New-Object Microsoft.AnalysisServices.Tabular.Server;$server.Connect("Data Source=localhost:$port")
 foreach($kind in @('baseline','candidate')) {
  $db=[Microsoft.AnalysisServices.Tabular.JsonSerializer]::DeserializeDatabase([IO.File]::ReadAllText((Join-Path $FixtureDirectory ($kind+'.json'))))
  if($db.Name -notlike 'ForecastMasterNativeSynthetic*'){throw 'Refusing non-synthetic fixture.'}
  foreach($t in $db.Model.Tables){foreach($p in $t.Partitions){if($p.Source -isnot [Microsoft.AnalysisServices.Tabular.CalculatedPartitionSource]){throw 'Refusing a non-calculated fixture partition.'}}}
  $db.Name='ForecastMasterNativeSynthetic-'+$kind+'-'+[guid]::NewGuid().ToString('N');$db.ID=$db.Name;$names[$kind]=$db.Name
  $server.Databases.Add($db);$db.Update([Microsoft.AnalysisServices.UpdateOptions]::ExpandFull)
  $refreshWatch=[Diagnostics.Stopwatch]::StartNew()
  $db.Model.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full);$null=$db.Model.SaveChanges()
  foreach($t in $db.Model.Tables){foreach($column in $t.Columns){if($column.ErrorMessage){Write-Output ('Column diagnostic: '+$t.Name+'['+$column.Name+'] '+$column.ErrorMessage)}}}
  foreach($t in $db.Model.Tables){foreach($p in $t.Partitions){if($p.ErrorMessage){throw ('Synthetic processing failed: '+$p.ErrorMessage)}}}
  Write-Output ('Fabricated '+$kind+' model processed in '+$refreshWatch.ElapsedMilliseconds+' ms.')
 }
 $traceSource=@"
using System;
using System.Collections.Generic;
using Microsoft.AnalysisServices.Tabular;
public class R178ProfileEvent {
 public string EventClass, SessionID, DatabaseName, TextData, RequestID;
 public long Duration, CpuTime;
}
public static class R178ProfileSink {
 static readonly List<R178ProfileEvent> data=new List<R178ProfileEvent>();
 public static void Receive(object sender,TraceEventArgs e) {
  var r=new R178ProfileEvent {EventClass=e.EventClass.ToString(),SessionID=e.SessionID,
   DatabaseName=e.DatabaseName,TextData=e.TextData,RequestID=e.RequestID,
   Duration=e.Duration,CpuTime=e.CpuTime};
  lock(data) { data.Add(r); }
 }
 public static int QueryEnds() { lock(data) { int n=0; foreach(var r in data) { if(r.EventClass=="QueryEnd") n++; } return n; } }
 public static void Attach(Trace trace) { trace.OnEvent += Receive; }
 public static R178ProfileEvent[] Snapshot() { lock(data) { return data.ToArray(); } }
}
"@
 Add-Type -TypeDefinition $traceSource -ReferencedAssemblies @((Join-Path $bin 'Microsoft.PowerBI.Tabular.dll'),(Join-Path $bin 'Microsoft.PowerBI.Amo.Core.dll'))
 $traceId='R178FabricatedProfile-'+[guid]::NewGuid().ToString('N')
 $trace=$server.Traces.Add($traceId,$traceId)
 foreach($class in @('QueryEnd','VertiPaqSEQueryEnd','DAXQueryPlan','ExecutionMetrics')) {
  $event=$trace.Events.Add([Microsoft.AnalysisServices.TraceEventClass]::$class)
  $columns=@('TextData','RequestID')
  if($class -ne 'ExecutionMetrics'){$columns+=@('SessionID','DatabaseName')}
  if($class -in @('QueryEnd','VertiPaqSEQueryEnd')){$columns+=@('Duration','CpuTime')}
  foreach($column in $columns) {
   $null=$event.Columns.Add([Microsoft.AnalysisServices.TraceColumn]::$column)
  }
 }
 $trace.Update()
 [R178ProfileSink]::Attach($trace)
 $trace.Start()
 Write-Output 'Native QueryEnd/SE/plan/execution-metric trace started on the task-owned engine.'
 foreach($case in (Get-Content (Join-Path $FixtureDirectory 'queries.json') -Raw -Encoding UTF8|ConvertFrom-Json)) {
  $ordinal+=1; Write-Output ("Starting synthetic query "+$ordinal+": "+$case.name+" ["+$case.model+"]")
  $connection=New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$port;Initial Catalog=$($names[$case.model])")
  try {
   $connection.Open();$command=$connection.CreateCommand();$command.CommandText=$case.query;$command.CommandTimeout=60
   $watch=[Diagnostics.Stopwatch]::StartNew();$reader=$command.ExecuteReader();$sets=@()
   try {do {$rows=@();$columns=@();for($i=0;$i -lt $reader.FieldCount;$i++){$columns+=,$reader.GetName($i)}
    while($reader.Read()){$row=[ordered]@{};for($i=0;$i -lt $reader.FieldCount;$i++){$row[$reader.GetName($i)]=if($reader.IsDBNull($i)){$null}else{$reader.GetValue($i)}};$rows+=,$row}
    $sets+=@{columns=$columns;rows=@($rows)}
   }while($reader.NextResult())}finally{$reader.Close()}
   $results+=@{name=$case.name;model=$case.model;elapsedMs=$watch.ElapsedMilliseconds;sessionID=$connection.SessionID;rows=@($sets[0].rows);resultSets=@($sets)}
  }catch{$results+=@{name=$case.name;model=$case.model;error=$_.Exception.Message}}finally{$connection.Close()}
  $checkpoint=Join-Path $FixtureDirectory ('query-'+$ordinal.ToString('0000')+'.json')
  if(Test-Path $checkpoint){throw 'Preserve existing query checkpoint'}
  ConvertTo-Json -InputObject $results[-1] -Depth 30|Set-Content -Encoding UTF8 $checkpoint
  Write-Output ("Completed synthetic query "+$ordinal)
 }
 ConvertTo-Json -InputObject @($results) -Depth 30|Set-Content -Encoding UTF8 (Join-Path $FixtureDirectory 'results.json')
 $traceDeadline=[DateTime]::UtcNow.AddSeconds(10)
 while([R178ProfileSink]::QueryEnds() -lt $results.Count -and [DateTime]::UtcNow -lt $traceDeadline){Start-Sleep -Milliseconds 100}
 $trace.Stop();$trace=$null
 ConvertTo-Json -InputObject @([R178ProfileSink]::Snapshot()) -Depth 8|Set-Content -Encoding UTF8 (Join-Path $FixtureDirectory 'trace.json')
 Write-Output ('Synthetic query executions: '+$results.Count)
}finally{
 if($trace -and $trace.IsStarted){try{$trace.Stop()}catch{Write-Output 'Trace stop failed; task engine shutdown follows.'}}
 if($server){$server.Disconnect()}
 if($engine -and !$engine.HasExited){Stop-Process -Id $engine.Id -ErrorAction SilentlyContinue}
 Write-Output ('Task-owned engine stopped; fabricated evidence directory: '+$work)
}
