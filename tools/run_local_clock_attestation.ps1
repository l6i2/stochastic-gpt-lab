param([string]$TerminalPath = '', [string]$Mapping = '')
& "$PSScriptRoot\local_finalize.ps1" -TerminalPath $TerminalPath -Mapping $Mapping
exit $LASTEXITCODE
