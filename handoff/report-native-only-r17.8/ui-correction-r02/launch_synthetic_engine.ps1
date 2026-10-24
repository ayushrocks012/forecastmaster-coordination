param([string]$FixtureDirectory,[string]$Runner)
$ErrorActionPreference='Stop'
if(Test-Path (Join-Path $FixtureDirectory 'launch.json')){throw 'Preserve existing launch'}
$p=Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$Runner+'" -FixtureDirectory "'+$FixtureDirectory+'"') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $FixtureDirectory 'stdout.txt') -RedirectStandardError (Join-Path $FixtureDirectory 'stderr.txt') -PassThru
@{Pid=$p.Id;StartedUTC=[DateTime]::UtcNow.ToString('o');Isolation='Task-owned calculated-only engine; Windows process independent of WSL shell lifetime'}|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $FixtureDirectory 'launch.json')
Write-Output ('Started isolated local qualification PID '+$p.Id)
