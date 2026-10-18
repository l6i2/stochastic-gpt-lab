param([switch]$ReplaceExisting)
$ErrorActionPreference = 'Stop'
$TaskName = 'StochasticGptLabFutureValidationCollector'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Runner = Join-Path $PSScriptRoot 'run_future_validation_collector.ps1'
$StartAt = [DateTime]::ParseExact('2026-10-19 00:15', 'yyyy-MM-dd HH:mm', [Globalization.CultureInfo]::InvariantCulture)

if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) { throw 'Collector task runner is missing.' }
if ($StartAt -le (Get-Date)) { throw 'Scheduled start has passed; review the start rule before registering.' }
$Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($Existing -and -not $ReplaceExisting) {
    throw "Task already exists; inspect it first or pass -ReplaceExisting: $TaskName"
}

$PowerShellExe = Join-Path $PSHOME 'powershell.exe'
$Arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$Runner`""
$Action = New-ScheduledTaskAction -Execute $PowerShellExe -Argument $Arguments -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -Once -At $StartAt `
    -RepetitionInterval (New-TimeSpan -Minutes 15) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 40)
$Description = 'Read-only capture of future US30Cash M5 bars and ticks; no orders; starts 2026-10-19 local time.'
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Principal $Principal -Settings $Settings -Description $Description -Force:$ReplaceExisting | Out-Null
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State
