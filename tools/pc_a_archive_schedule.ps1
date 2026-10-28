param([ValidateSet('start','stop')][string]$Action)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$taskName = 'StochasticGPTLab_PC_A_RawQuarantine_v1'
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    $expected = Join-Path $repo '.venv\Scripts\python.exe'
    $hiddenPython = Join-Path $repo '.venv\Scripts\pythonw.exe'
    $expectedArguments = '"' + (Join-Path $repo 'tools\research_station.py') + '" collect'
    if ($existing.Actions.Execute -notin @($expected, $hiddenPython) -or $existing.Actions.Arguments -ne $expectedArguments) {
        throw 'Existing task identity differs; refusing modification'
    }
}
if ($Action -eq 'stop') {
    if ($existing) { Disable-ScheduledTask -TaskName $taskName | Out-Null }
    Write-Output 'DISABLED_AFTER_CURRENT_ATOMIC_WINDOW'
    exit 0
}
$python = Join-Path $repo '.venv\Scripts\pythonw.exe'
$script = Join-Path $repo 'tools\research_station.py'
$taskAction = New-ScheduledTaskAction -Execute $python -Argument ('"' + $script + '" collect') -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 12)
Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Output 'REGISTERED_EVERY_MINUTE_INTERACTIVE_USER'
