param([Parameter(Mandatory=$true)][string]$NativeFile,
      [Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
& "$repo\.venv\Scripts\python.exe" "$PSScriptRoot\windows_clock_capture.py" --native $NativeFile --output $OutputDirectory
exit $LASTEXITCODE
