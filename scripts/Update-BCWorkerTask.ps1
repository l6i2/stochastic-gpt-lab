$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$name='StochasticGPTLab_PC_A_BCTrainAcquisition_v1'
if(!(Test-Path -LiteralPath (Join-Path $repo 'research\studies\bc_train_future_eval_v1\operational_wrapper_v2.json'))){throw 'BC_WRAPPER_NOT_SEALED'}
$action=New-ScheduledTaskAction -Execute (Join-Path $repo '.venv\Scripts\pythonw.exe') -Argument ('"'+(Join-Path $repo 'tools\bc_study_worker.py')+'" --budget 6') -WorkingDirectory $repo
Set-ScheduledTask -TaskName $name -Action $action | Out-Null
$task=Get-ScheduledTask -TaskName $name
if($task.Actions.Arguments -notlike '*bc_study_worker.py*'){throw 'BC_WORKER_ACTION_NOT_APPLIED'}
Start-ScheduledTask -TaskName $name
$task | Select-Object TaskName,State
