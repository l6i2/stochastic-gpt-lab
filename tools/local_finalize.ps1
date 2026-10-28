param([string]$TerminalPath = '', [string]$Mapping = '', [string]$ResumeFolder = '',
      [string]$SourceManifest = '')
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$python = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Python environment missing. Run py -3.12 -m venv .venv, then .venv\Scripts\python.exe -m pip install -r configs\controller_requirements.txt' }
$arguments = @('python\local_finalize.py')
if ($TerminalPath) { $arguments += @('--terminal', $TerminalPath) }
if ($Mapping) { $arguments += @('--mapping', $Mapping) }
if ($ResumeFolder) { $arguments += @('--resume-folder', $ResumeFolder) }
if ($SourceManifest) { $arguments += @('--source-manifest', $SourceManifest) }
& $python @arguments
exit $LASTEXITCODE
