$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PythonExe = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$Collector = Join-Path $RepoRoot 'python\future_validation_collector.py'
$CohortDir = Join-Path $RepoRoot 'outputs\future_validation_cohort\cohort_20261019'
$LogPath = Join-Path $CohortDir 'scheduler.log'

if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) { throw 'Project virtualenv Python is missing.' }
if (-not (Test-Path -LiteralPath $Collector -PathType Leaf)) { throw 'Collector source is missing.' }
New-Item -ItemType Directory -Path $CohortDir -Force | Out-Null
Set-Location -LiteralPath $RepoRoot
$Started = [DateTime]::UtcNow.ToString('o')
$Output = & $PythonExe $Collector collect 2>&1
$ExitCode = $LASTEXITCODE
$Record = [ordered]@{ started_utc = $Started; exit_code = $ExitCode; output = ($Output -join "`n") }
Add-Content -LiteralPath $LogPath -Value (ConvertTo-Json $Record -Compress) -Encoding UTF8
exit $ExitCode
