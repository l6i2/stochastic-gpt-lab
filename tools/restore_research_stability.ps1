$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'install_research_recovery.ps1') -Remove
$target=Join-Path $PSScriptRoot 'research_recovery.ps1'
Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'powershell.exe' -and $_.CommandLine -like ('*"'+$target+'"*')} | ForEach-Object {Stop-Process -Id $_.ProcessId -ErrorAction Stop}
& (Join-Path $PSScriptRoot 'research_power.ps1') -Action Restore
# Existing collector watchdog, MT5 and previous NTS tasks continue untouched.
