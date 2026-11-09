$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$python=Join-Path $repo '.venv\Scripts\pythonw.exe'
$script=Join-Path $repo 'tools\bc_pretraining_worker.py'
if(!(Test-Path -LiteralPath (Join-Path $repo 'outputs\bc_train_future_eval_v1\current.json'))){throw 'BC_NOT_ACTIVATED'}
$name='StochasticGPTLab_PC_A_BCTrainAcquisition_v1'
$user=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action=New-ScheduledTaskAction -Execute $python -Argument ('"'+$script+'" --budget 2') -WorkingDirectory $repo
$logon=New-ScheduledTaskTrigger -AtLogOn -User $user
$periodic=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $name -Action $action -Trigger @($logon,$periodic) -Settings $settings -Principal $principal -Description 'Authorized isolated B+C native-history TRAIN acquisition, no training or scoring. File mutex; post-cut bounds only.' -Force | Out-Null
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State
