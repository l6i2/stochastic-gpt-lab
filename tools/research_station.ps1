param([ValidateSet('start','stop','resume','verify','collect','validate','reports','historical')][string]$Action = 'reports')
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
& "$repo\.venv\Scripts\python.exe" "$PSScriptRoot\research_station.py" $Action
exit $LASTEXITCODE
