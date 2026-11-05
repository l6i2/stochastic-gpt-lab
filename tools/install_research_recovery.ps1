param([switch]$Remove)
$ErrorActionPreference='Stop'
$key='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$name='StochasticGPTLab_PC_A_Recovery_v1'
$taskName='StochasticGPTLab_PC_A_RecoveryGuardian_v1'
$script=Join-Path $PSScriptRoot 'research_recovery.ps1'
$repo=Split-Path -Parent $PSScriptRoot
$exe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$script+'"'
$command='"'+$exe+'" '+$arguments
$task=Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue
if($task -and ($task.Actions.Count -ne 1 -or $task.Actions[0].Execute -ne $exe -or $task.Actions[0].Arguments -ne $arguments -or $task.Actions[0].WorkingDirectory -ne $repo)){
    throw 'RECOVERY_TASK_ACTION_CONFLICT'
}
$legacy=Get-ItemPropertyValue -LiteralPath $key -Name $name -ErrorAction SilentlyContinue
if($legacy -and $legacy -ne $command){throw 'RECOVERY_STARTUP_CONFLICT'}
if($Remove){
    if($task){Disable-ScheduledTask -InputObject $task | Out-Null}
    if($legacy){Remove-ItemProperty -LiteralPath $key -Name $name}
    return
}
if(!(Test-Path -LiteralPath $script) -or !(Test-Path -LiteralPath (Join-Path $repo '.venv\Scripts\pythonw.exe'))){throw 'RECOVERY_WORKSPACE_INCOMPLETE'}
if(!$task){
    $user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
    $action=New-ScheduledTaskAction -Execute $exe -Argument $arguments -WorkingDirectory $repo
    $trigger=New-ScheduledTaskTrigger -AtLogOn -User $user
    $principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
    $settings=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    $task=Register-ScheduledTask -TaskName $taskName -TaskPath '\' -Action $action -Trigger $trigger -Principal $principal -Settings $settings
}
if($task.State -eq 'Disabled'){Enable-ScheduledTask -InputObject $task | Out-Null}
if($task.State -ne 'Running'){Start-ScheduledTask -InputObject $task}
if($legacy){Remove-ItemProperty -LiteralPath $key -Name $name}
Get-ScheduledTask -TaskName $taskName -TaskPath '\' | Select-Object TaskName,State
