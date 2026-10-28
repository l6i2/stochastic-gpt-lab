param()
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$env:LOW_MEMORY_MODE = 'true'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
Push-Location $repo
try {
    & "$repo\.venv\Scripts\python.exe" "$PSScriptRoot\research_station_status.py"
    exit $LASTEXITCODE
} finally { Pop-Location }
