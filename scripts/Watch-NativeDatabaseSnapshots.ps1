$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$base=Join-Path $repo 'outputs\native_database_snapshots_v1'
$script=Join-Path $repo 'tools\native_database_snapshots.py'
$mutex=New-Object System.Threading.Mutex($false,'Local\StochasticGPTLab_NativeDatabaseSnapshots_v1')
if(!$mutex.WaitOne(0)){$mutex.Dispose();exit 0}
$lastLaunch=[datetime]::MinValue
$auditChild=$null;$pendingCount=0;$pendingFolder='';$auditedCount=0
$auditCheckpoint=Join-Path $base 'monitor_checkpoint.json'
if(Test-Path -LiteralPath $auditCheckpoint){$auditedCount=(Get-Content -LiteralPath $auditCheckpoint -Raw | ConvertFrom-Json).accepted_m5}
try{
    while((Get-Content -LiteralPath (Join-Path $base 'enabled.json') -Raw | ConvertFrom-Json).enabled){
        $processes=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'pythonw.exe' -and $_.CommandLine -like ('*"'+$script+'" --serve*')})
        $action='NONE'
        if($processes.Count -eq 0 -and ([datetime]::UtcNow-$lastLaunch).TotalSeconds -ge 60){
            $id=[guid]::NewGuid().ToString('N');$logs=Join-Path $base 'launch_logs';New-Item -ItemType Directory -Force -Path $logs | Out-Null
            Start-Process (Join-Path $repo '.venv\Scripts\pythonw.exe') -ArgumentList ('"'+$script+'" --serve') -WorkingDirectory $repo -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs ($id+'.stdout')) -RedirectStandardError (Join-Path $logs ($id+'.stderr'))
            $lastLaunch=[datetime]::UtcNow;$action='START_OWN_DATABASE_PRODUCER'
        }
        if($null -ne $auditChild -and ((Test-Path -LiteralPath (Join-Path $pendingFolder 'audit_complete.json')) -or $auditChild.HasExited)){
            $completePath=Join-Path $pendingFolder 'audit_complete.json';$verified=$false
            if(Test-Path -LiteralPath $completePath){
                $complete=Get-Content -LiteralPath $completePath -Raw|ConvertFrom-Json;$verified=$true
                foreach($file in $complete.files.PSObject.Properties){
                    $path=Join-Path $pendingFolder $file.Name
                    if(!(Test-Path -LiteralPath $path)){$verified=$false;continue}
                    $algorithm=[Security.Cryptography.SHA256]::Create()
                    try{$hash=([BitConverter]::ToString($algorithm.ComputeHash([IO.File]::ReadAllBytes($path)))).Replace('-','').ToLowerInvariant()}finally{$algorithm.Dispose()}
                    if($hash -ne $file.Value){$verified=$false}
                }
            }
            if($verified){
                $auditedCount=$pendingCount
                [IO.File]::WriteAllText($auditCheckpoint,(@{accepted_m5=$auditedCount;audit_folder=$pendingFolder}|ConvertTo-Json -Compress))
            }else{$action='INDEPENDENT_AUDIT_FAILED_QUARANTINE_REMAINS'}
            $auditChild=$null
        }
        $pointer=Get-Content -LiteralPath (Join-Path $base 'current.json') -Raw | ConvertFrom-Json
        $statusPath=Join-Path (Join-Path $base $pointer.capture_id) 'status.json'
        if(Test-Path -LiteralPath $statusPath){
            $status=Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
            if($null -eq $auditChild -and $status.accepted.'300' -gt $auditedCount){
                $pendingCount=$status.accepted.'300';$id=[guid]::NewGuid().ToString('N');$pendingFolder=Join-Path $base ('monitor_reports\'+$id)
                $audit=Join-Path $repo 'tools\audit_native_database_trial.py'
                $auditChild=Start-Process (Join-Path $repo '.venv\Scripts\pythonw.exe') -ArgumentList ('"'+$audit+'" --out "'+$pendingFolder+'"') -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $base ($id+'.audit.stdout')) -RedirectStandardError (Join-Path $base ($id+'.audit.stderr'))
            }
        }
        $value=@{watchdog_pid=$PID;observed_host_utc=[datetime]::UtcNow.ToString('o');matching_python_processes=$processes.Count;action=$action;audited_m5=$auditedCount;scope='NEW_DATABASE_TRIAL_ONLY';training_authorized=$false;live_trading=$false}
        $temp=Join-Path $base ('watchdog.'+[guid]::NewGuid().ToString('N')+'.tmp');[IO.File]::WriteAllText($temp,($value | ConvertTo-Json -Compress));Move-Item -LiteralPath $temp -Destination (Join-Path $base 'watchdog_status.json') -Force
        Start-Sleep -Seconds 10
    }
}finally{$mutex.ReleaseMutex();$mutex.Dispose()}
