param([switch]$Install)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$name='StochasticGPTLab_PC_A_XMHistoricalDiagnostics_v1'
$python=Join-Path $repo '.venv\Scripts\pythonw.exe'
$arguments='"'+(Join-Path $repo 'tools\xm_historical_recovery.py')+'" --budget 6'
$task=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
if($task){
    if($task.Actions.Count -ne 1 -or $task.Actions[0].Execute -ne $python -or $task.Actions[0].Arguments -ne $arguments){throw 'HISTORICAL_TASK_SCOPE_CHANGED'}
}elseif($Install){
    $user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
    $action=New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $repo
    $logon=New-ScheduledTaskTrigger -AtLogOn -User $user
    $periodic=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 5)
    $principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
    $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $name -Action $action -Trigger @($logon,$periodic) -Principal $principal -Settings $settings -Description 'Read-only post-cut XM historical diagnostics. Separate retrospective archive, no prospective imports, fits or orders.' | Out-Null
    $task=Get-ScheduledTask -TaskName $name
}
if(!$task){@{status='NOT_INSTALLED'}|ConvertTo-Json -Compress;exit 0}
$info=$task|Get-ScheduledTaskInfo
@{status='HISTORICAL_DIAGNOSTIC_TASK_VERIFIED';state=[string]$task.State;last_result=$info.LastTaskResult;next_run=$info.NextRunTime.ToString('o');logon_required=$true;global_power_changed=$false;rollback="Unregister-ScheduledTask -TaskName '$name' -Confirm:`$false"}|ConvertTo-Json -Compress
