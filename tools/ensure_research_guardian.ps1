param([switch]$Install)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$name='StochasticGPTLab_PC_A_RecoveryGuardian_v1'
$script=Join-Path $repo 'tools\research_recovery.ps1'
$exe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$script+'"'
$existing=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
if($existing){
    if($existing.Actions.Count -ne 1 -or $existing.Actions[0].Execute -ne $exe -or $existing.Actions[0].Arguments -ne $arguments){throw 'EXISTING_TASK_SCOPE_MISMATCH'}
}elseif($Install){
    $user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
    $action=New-ScheduledTaskAction -Execute $exe -Argument $arguments -WorkingDirectory $repo
    $logon=New-ScheduledTaskTrigger -AtLogOn -User $user
    $periodic=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
    $principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
    $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $name -Action $action -Trigger @($logon,$periodic) -Principal $principal -Settings $settings -Description 'Own research guardian only; existing mutex prevents duplicate XM/watchdog/worker/reporters. No global power/network changes.' | Out-Null
    $existing=Get-ScheduledTask -TaskName $name
}
if(!$existing){@{status='NOT_INSTALLED';task=$name}|ConvertTo-Json -Compress;exit 0}
$info=$existing|Get-ScheduledTaskInfo
@{status='SCOPED_TASK_REGISTERED';task=$name;state=[string]$existing.State;action=$existing.Actions[0].Execute;arguments=$existing.Actions[0].Arguments;last_result=$info.LastTaskResult;next_run=$info.NextRunTime.ToString('o');scope='OWN_GUARDIAN_USER_LOGON_REQUIRED_NO_SYSTEM_POLICY_CHANGE';rollback="Unregister-ScheduledTask -TaskName '$name' -Confirm:`$false"}|ConvertTo-Json -Compress
