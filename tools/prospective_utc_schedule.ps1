$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$taskName='StochasticGPTLab_PC_A_ProspectiveUTC_v1'
$python=Join-Path $repo '.venv\Scripts\pythonw.exe'
$arguments='"'+(Join-Path $repo 'tools\prospective_utc_station.py')+'"'
$old=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if($old -and ($old.Actions.Execute -ne $python -or $old.Actions.Arguments -ne $arguments)){throw 'Task identity mismatch'}
$action=New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $repo
$user=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$triggers=@((New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)),(New-ScheduledTaskTrigger -AtLogOn -User $user))
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggers -Principal $principal -Settings $settings -Force | Out-Null
Write-Output 'WITNESS_AND_MONITOR_SCHEDULED_NATIVE_EA_ATTACHMENT_SEPARATE'
