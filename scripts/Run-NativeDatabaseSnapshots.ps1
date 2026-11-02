$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$logs=Join-Path $repo 'outputs\native_database_snapshots_v1\launch_logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$run=[guid]::NewGuid().ToString('N')
& (Join-Path $repo '.venv\Scripts\python.exe') (Join-Path $repo 'tools\native_database_snapshots.py') --serve 1> (Join-Path $logs ($run+'.stdout')) 2> (Join-Path $logs ($run+'.stderr'))
exit $LASTEXITCODE
