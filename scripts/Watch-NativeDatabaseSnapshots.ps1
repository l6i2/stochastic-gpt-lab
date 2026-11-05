$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$base=Join-Path $repo 'outputs\native_database_snapshots_v1'
$script=Join-Path $repo 'tools\native_database_snapshots.py'
$mutex=New-Object System.Threading.Mutex($false,'Local\StochasticGPTLab_NativeDatabaseSnapshots_v1')
if(!$mutex.WaitOne(0)){$mutex.Dispose();exit 0}
$lastLaunch=[datetime]::MinValue
$lastStallRecovery=[datetime]::MinValue
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
            # An IPC call can remain stuck after XM disappears. Existence of
            # Python processes alone is not proof of a live producer. Allow a
            # five-minute operational grace, then restart only the scoped leaf.
            $staleSeconds=([datetime]::UtcNow-(Get-Item -LiteralPath $statusPath).LastWriteTimeUtc).TotalSeconds
            if($processes.Count -gt 0 -and $staleSeconds -ge 300 -and ([datetime]::UtcNow-$lastStallRecovery).TotalSeconds -ge 300){
                $parents=@($processes|ForEach-Object {$_.ParentProcessId})
                $leaves=@($processes|Where-Object {$_.ProcessId -notin $parents -and ([datetime]::UtcNow-$_.CreationDate.ToUniversalTime()).TotalSeconds -ge 300})
                foreach($leaf in $leaves){Stop-Process -Id $leaf.ProcessId -Force -ErrorAction SilentlyContinue}
                if($leaves.Count -gt 0){
                    $action='RESTART_STALLED_OWN_IPC_CLIENT_FRESH_CUT_NO_BACKFILL'
                    $incident=@{host_utc=[datetime]::UtcNow.ToString('o');reason=$action;stale_seconds=$staleSeconds;prior_chain_head=$status.chain_head;prior_records=$status.records;terminated_leaf_pids=@($leaves|ForEach-Object {$_.ProcessId});data_rewritten=$false}
                    $folder=Join-Path $base 'recovery_events';New-Item -ItemType Directory -Force -Path $folder|Out-Null
                    $incident|ConvertTo-Json -Depth 5|Out-File -LiteralPath (Join-Path $folder ([guid]::NewGuid().ToString('N')+'.json')) -Encoding utf8 -NoClobber
                    $lastStallRecovery=[datetime]::UtcNow
                }
            }
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
