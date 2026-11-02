param([switch]$Remove)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$base=Join-Path $repo 'outputs\native_database_snapshots_v1'
$script=Join-Path $repo 'scripts\Watch-NativeDatabaseSnapshots.ps1'
$exe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$script+'"'
$command='"'+$exe+'" '+$arguments
$key='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$name='StochasticGPTLab_NativeDatabaseSnapshots_v1'
$old=(Get-Item -LiteralPath $key).GetValue($name,$null)
if($old -and $old -ne $command){throw 'EXISTING_AUTORUN_SCOPE_MISMATCH'}
if($Remove){
    [IO.File]::WriteAllText((Join-Path $base 'enabled.json'),'{"enabled":false}')
    if($old){Remove-ItemProperty -LiteralPath $key -Name $name}
    @{status='OWN_TRIAL_DISABLED_AUTORUN_REMOVED';prior_assets_unchanged=$true}|ConvertTo-Json -Compress;exit 0
}
if(!$old){New-ItemProperty -LiteralPath $key -Name $name -Value $command -PropertyType String | Out-Null}
if((Get-ItemPropertyValue -LiteralPath $key -Name $name) -ne $command){throw 'AUTORUN_VERIFICATION_FAILED'}
$launch=[guid]::NewGuid().ToString('N')
Start-Process $exe -ArgumentList $arguments -WorkingDirectory $repo -WindowStyle Hidden -RedirectStandardOutput (Join-Path $base ($launch+'.watchdog.stdout')) -RedirectStandardError (Join-Path $base ($launch+'.watchdog.stderr'))
@{status='PER_USER_AUTORUN_VERIFIED_WATCHDOG_REQUESTED';name=$name;requires_user_logon=$true;scheduled_task_installed=$false;old_tasks_modified=$false}|ConvertTo-Json -Compress
