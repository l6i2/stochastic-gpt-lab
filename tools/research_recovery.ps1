param([switch]$Once,[switch]$DryRun)
function Test-HeadlessCaptureStall {
    param([long]$WindowHandle,[double]$ProcessAgeSeconds,[double]$CallbackAgeMs,[double]$StatusAgeSeconds)
    # Operational restart grace, never a scientific coverage tolerance.
    return $WindowHandle -eq 0 -and $ProcessAgeSeconds -ge 300 -and $CallbackAgeMs -ge 300000 -and $StatusAgeSeconds -ge 0 -and $StatusAgeSeconds -le 120
}
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$base=Join-Path $repo 'outputs\pc_a_stability'
$terminal='C:\Program Files\XM Global SC MT5 Terminal\terminal64.exe'
$data=Join-Path $env:APPDATA 'MetaQuotes\Terminal\20C285FE08971A9A2E814AAC44AFC9D2'
$mutex=New-Object System.Threading.Mutex($false,'Local\StochasticGPTLab_PC_A_Recovery_v1')
try{$ownsMutex=$mutex.WaitOne(0)}catch [System.Threading.AbandonedMutexException]{$ownsMutex=$true}
if(!$ownsMutex){$mutex.Dispose();exit 0}
try{
New-Item -ItemType Directory -Path (Join-Path $base 'recovery_events') -Force | Out-Null
$config=Join-Path $base 'xm_readonly_restart.ini'
$expected="[Experts]`r`nEnabled=0`r`nAllowLiveTrading=0`r`nAllowDllImport=0`r`n[Charts]`r`nProfileLast=Default`r`n"
if(Test-Path -LiteralPath $config){
    $existing=[IO.File]::ReadAllText($config)
    if($existing -ceq $expected.Replace('Enabled=0','Enabled=1')){
        $replacement=$config+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
        [IO.File]::WriteAllText($replacement,$expected)
        [IO.File]::Replace($replacement,$config,[NullString]::Value)
    }elseif($existing -cne $expected){throw 'RECOVERY_CONFIG_CHANGED'}
}else{[IO.File]::WriteAllText($config,$expected)}
$nts=$null;$receipt=$null;$lastCF=[datetime]::MinValue;$lastSnapshotWatch=[datetime]::MinValue;$lastDashboard=[datetime]::MinValue;$lastPipeline=[datetime]::MinValue;$lastReceipt=[datetime]::MinValue;$lastNts=[datetime]::MinValue;$lastLaunch=[datetime]::MinValue;$prior=''
 do {
    try {
    $processes=@(Get-CimInstance Win32_Process)
    $xm=@($processes | Where-Object {$_.ExecutablePath -eq $terminal})
    $watch=@($processes | Where-Object {$_.Name -eq 'powershell.exe' -and $_.CommandLine -like ('*"'+(Join-Path $repo 'tools\new_capture_watchdog.ps1')+'"*')})
    $actions=@()
    # Scientific ingress closure is forward-only. The native XM observer remains
    # diagnostic; old reservation writers and their watchdogs must not restart.
    $legacyIngressClosed=Test-Path -LiteralPath (Join-Path $repo 'outputs\us30cash_m5_native_observations\legacy_ingress_closed.json')
    $cfBase=Join-Path $repo 'outputs\us30cash_m5_native_observations'
    $cfEnable=Join-Path $cfBase 'enabled.json'
    if((Test-Path -LiteralPath $cfEnable) -and (Get-Content -LiteralPath $cfEnable -Raw|ConvertFrom-Json).enabled){
        $cfScript=Join-Path $repo 'tools\cf_study_station.py'
        $cf=@($processes|Where-Object {$_.Name -eq 'pythonw.exe' -and $_.CommandLine -like ('*"'+$cfScript+'" --serve*')})
        $cfStatus=Join-Path $cfBase 'status.json'
        if($cf.Count -gt 0 -and (Test-Path -LiteralPath $cfStatus) -and ([datetime]::UtcNow-(Get-Item -LiteralPath $cfStatus).LastWriteTimeUtc).TotalSeconds -ge 300){
            $parents=@($cf|ForEach-Object {$_.ParentProcessId})
            $leaves=@($cf|Where-Object {$_.ProcessId -notin $parents -and ([datetime]::UtcNow-$_.CreationDate.ToUniversalTime()).TotalSeconds -ge 300})
            if($leaves.Count -gt 0){$actions+='RECOVER_STALLED_CF_CLIENT_NEW_EPOCH';if(!$DryRun){foreach($leaf in $leaves){Stop-Process -Id $leaf.ProcessId -Force -ErrorAction SilentlyContinue}}}
        }
        if($cf.Count -eq 0 -and $xm.Count -eq 1 -and ([datetime]::UtcNow-$lastCF).TotalSeconds -ge 60){
            $actions+='START_AUTHORIZED_CF_QUARANTINE_PRODUCER'
            if(!$DryRun){Start-Process (Join-Path $repo '.venv\Scripts\pythonw.exe') -ArgumentList ('"'+$cfScript+'" --serve') -WorkingDirectory $repo -WindowStyle Hidden -RedirectStandardOutput (Join-Path $cfBase 'producer.stdout') -RedirectStandardError (Join-Path $cfBase 'producer.stderr')|Out-Null}
            $lastCF=[datetime]::UtcNow
        }
    }
    if($xm.Count -eq 1 -and !$legacyIngressClosed){
        $capturePointer=Join-Path $repo 'outputs\new_native_studies\us30cash_m5_native_20261030_01\current_capture.json'
        if(Test-Path -LiteralPath $capturePointer){
            $captureId=(Get-Content -LiteralPath $capturePointer -Raw|ConvertFrom-Json).capture_id
            if($captureId -match '^us30cap_[a-f0-9]{32}$'){
                $captureStatus=Join-Path (Split-Path $capturePointer -Parent) ($captureId+'\collector_status.json')
                if(Test-Path -LiteralPath $captureStatus){
                    $cs=Get-Content -LiteralPath $captureStatus -Raw|ConvertFrom-Json
                    $xp=Get-Process -Id $xm[0].ProcessId -ErrorAction SilentlyContinue
                    $profileSafe=$false;$foreignExpert=$false
                    foreach($chart in (Get-ChildItem -LiteralPath (Join-Path $data 'MQL5\Profiles\Charts\Default') -Filter '*.chr')){
                        $chartText=Get-Content -LiteralPath $chart.FullName -Raw
                        foreach($expert in [regex]::Matches($chartText,'(?s)<expert>(.*?)</expert>')){
                            if($expert.Value -match 'path=Experts\\ResearchDiagnostics\\ProspectiveUtcObserver.ex5'){$profileSafe=$true}else{$foreignExpert=$true}
                        }
                    }
                    if($xp -and $profileSafe -and !$foreignExpert -and (Test-HeadlessCaptureStall $xp.MainWindowHandle ([datetime]::UtcNow-$xp.StartTime.ToUniversalTime()).TotalSeconds $cs.last_callback_age_ms ([datetime]::UtcNow-(Get-Item -LiteralPath $captureStatus).LastWriteTimeUtc).TotalSeconds)){
                        $actions+='RESTART_EXACT_HEADLESS_XM_NO_CALLBACKS_5MIN_FRESH_COLLECTOR'
                        if(!$DryRun){Stop-Process -Id $xp.Id -Force;$xm=@()}
                    }
                }
            }
        }
    }
    # The authorized separate snapshot trial has its own mutex watchdog. Logon
    # registration alone cannot recover a watchdog lost during the same login.
    $snapshotEnable=Join-Path $repo 'outputs\native_database_snapshots_v1\enabled.json'
    $snapshotWatch=Join-Path $repo 'scripts\Watch-NativeDatabaseSnapshots.ps1'
    if(!$legacyIngressClosed -and (Test-Path -LiteralPath $snapshotEnable) -and (Get-Content -LiteralPath $snapshotEnable -Raw|ConvertFrom-Json).enabled){
        $snapshotWatches=@($processes|Where-Object {$_.Name -eq 'powershell.exe' -and $_.CommandLine -like ('*"'+$snapshotWatch+'"*')})
        if($snapshotWatches.Count -eq 0 -and ([datetime]::UtcNow-$lastSnapshotWatch).TotalSeconds -ge 60){
            $actions+='START_AUTHORIZED_SEPARATE_SNAPSHOT_WATCHDOG'
            if(!$DryRun){Start-Process powershell.exe -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$snapshotWatch+'"') -WorkingDirectory $repo -WindowStyle Hidden | Out-Null}
            $lastSnapshotWatch=[datetime]::UtcNow
        }
    }
    $dashboardScript=Join-Path $repo 'tools\research_dashboard.py'
    $dashboard=@($processes|Where-Object {$_.Name -eq 'pythonw.exe' -and $_.CommandLine -like ('*"'+$dashboardScript+'" --serve*')})
    if($dashboard.Count -eq 0 -and ([datetime]::UtcNow-$lastDashboard).TotalSeconds -ge 60){
        $actions+='START_READ_ONLY_ADMISSION_DASHBOARD'
        if(!$DryRun){Start-Process (Join-Path $repo '.venv\Scripts\pythonw.exe') -ArgumentList ('"'+$dashboardScript+'" --serve') -WorkingDirectory $repo -WindowStyle Hidden -RedirectStandardOutput (Join-Path $repo 'outputs\research_readiness\reporter.stdout') -RedirectStandardError (Join-Path $repo 'outputs\research_readiness\reporter.stderr')}
        $lastDashboard=[datetime]::UtcNow
    }
    $pipelineEnable=Join-Path $repo 'outputs\prospective_derivatives_v1\enabled.json'
    if(!$legacyIngressClosed -and (Test-Path -LiteralPath $pipelineEnable)){
        $pipelineEnabled=(Get-Content -LiteralPath $pipelineEnable -Raw | ConvertFrom-Json).enabled
        $pipelineScript=Join-Path $repo 'tools\prospective_pipeline.py'
        $pipeline=@($processes | Where-Object {$_.Name -eq 'pythonw.exe' -and $_.CommandLine -like ('*"'+$pipelineScript+'" --serve*')})
        if($pipelineEnabled -and $pipeline.Count -gt 0){
            $pointer=Join-Path $repo 'outputs\new_native_studies\us30cash_m5_native_20261030_01\current_capture.json'
            $id=(Get-Content -LiteralPath $pointer -Raw|ConvertFrom-Json).capture_id
            if($id -match '^us30cap_[a-f0-9]{32}$'){
                $maturity=Join-Path (Split-Path $pipelineEnable -Parent) ($id+'\maturity.json')
                if((Test-Path -LiteralPath $maturity) -and ([datetime]::UtcNow-(Get-Item -LiteralPath $maturity).LastWriteTimeUtc).TotalSeconds -ge 300){
                    $parentIds=@($pipeline|ForEach-Object {$_.ParentProcessId})
                    $leaves=@($pipeline|Where-Object {$_.ProcessId -notin $parentIds -and ([datetime]::UtcNow-$_.CreationDate.ToUniversalTime()).TotalSeconds -ge 300})
                    if($leaves.Count -gt 0){
                        $actions+='RESTART_STALLED_DERIVATIVE_IPC_CLIENT_DURABLE_CURSOR_ONLY'
                        if(!$DryRun){foreach($leaf in $leaves){Stop-Process -Id $leaf.ProcessId -Force -ErrorAction SilentlyContinue}}
                    }
                }
            }
        }
        if($pipelineEnabled -and $pipeline.Count -eq 0 -and ([datetime]::UtcNow-$lastPipeline).TotalSeconds -ge 60){
            $actions+='START_QUARANTINED_DERIVATIVE_WORKER'
            if(!$DryRun){Start-Process (Join-Path $repo '.venv\Scripts\pythonw.exe') -ArgumentList ('"'+$pipelineScript+'" --serve') -WorkingDirectory $repo -WindowStyle Hidden -RedirectStandardOutput (Join-Path $repo 'outputs\prospective_derivatives_v1\worker.stdout') -RedirectStandardError (Join-Path $repo 'outputs\prospective_derivatives_v1\worker.stderr') | Out-Null}
            $lastPipeline=[datetime]::UtcNow
        }
    }
    if($xm.Count -eq 0 -and ([datetime]::UtcNow-$lastLaunch).TotalSeconds -ge 120){
        # Only the already identified XM installation. No credentials, login change,
        # tester, orders or script injection. Preserve its persisted profile.
        $observer=Join-Path $data 'MQL5\Experts\ResearchDiagnostics\ProspectiveUtcObserver.ex5'
        $charts=Get-ChildItem -LiteralPath (Join-Path $data 'MQL5\Profiles\Charts\Default') -Filter '*.chr'
        $valid=$false;$unsafe=$false
        foreach($chart in $charts){$text=Get-Content -LiteralPath $chart.FullName -Raw;if($text -match 'path=Experts\\ResearchDiagnostics\\ProspectiveUtcObserver.ex5'){$valid=$true};foreach($match in [regex]::Matches($text,'(?s)<expert>(.*?)</expert>')){if($match.Value -notmatch 'path=Experts\\ResearchDiagnostics\\ProspectiveUtcObserver.ex5'){$unsafe=$true}}}
        $binaryValid=(Test-Path -LiteralPath $observer) -and (([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([IO.File]::ReadAllBytes($observer))).Replace('-','')) -eq '5cf9fb463f0be82d46680a3b5e6af83f501033ad83b5cf1bc2795692262f1fc0')
        $checkpointSafe=$true
        if($valid -and !$unsafe -and $binaryValid -and $legacyIngressClosed -and !$DryRun){
            & (Join-Path $repo '.venv\Scripts\python.exe') (Join-Path $repo 'tools\research_restart_receipt.py') > (Join-Path $base 'xm_preflight.stdout')
            $checkpointSafe=$LASTEXITCODE -eq 0
        }
        if($valid -and !$unsafe -and $binaryValid -and $checkpointSafe){
            $actions+='START_EXACT_XM_READONLY'
            if(!$DryRun){Start-Process -FilePath $terminal -ArgumentList ('/config:"'+$config+'"') -WindowStyle Hidden | Out-Null}
        }elseif(!$checkpointSafe){$actions+='BLOCKED_CF_CHECKPOINT_PREFLIGHT'}else{$actions+='BLOCKED_PROFILE_REQUIRES_REVIEW'}
        $lastLaunch=[datetime]::UtcNow
    }
    if(!$legacyIngressClosed -and $watch.Count -eq 0){$actions+='START_OWN_CAPTURE_WATCHDOG';if(!$DryRun){Start-Process powershell.exe -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+(Join-Path $repo 'tools\new_capture_watchdog.ps1')+'"') -WindowStyle Hidden | Out-Null}}
    if(($null -eq $nts -or $nts.HasExited) -and ([datetime]::UtcNow-$lastNts).TotalSeconds -ge 60){
        $actions+='CHECK_NTS_DUE_EXISTING_LOCKED_STATION'
        if(!$DryRun){$id=[guid]::NewGuid().ToString('N');$nts=Start-Process (Join-Path $repo '.venv\Scripts\pythonw.exe') -ArgumentList ('"'+(Join-Path $repo 'tools\authenticated_utc_station.py')+'"') -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $base ($id+'.nts.stdout')) -RedirectStandardError (Join-Path $base ($id+'.nts.stderr'))}
        $lastNts=[datetime]::UtcNow
    }
    if(($null -eq $receipt -or $receipt.HasExited) -and ([datetime]::UtcNow-$lastReceipt).TotalSeconds -ge 60){
            $actions+='SAVE_OR_VERIFY_RESTART_RECEIPT'
            if(!$DryRun){$receipt=Start-Process (Join-Path $repo '.venv\Scripts\pythonw.exe') -ArgumentList ('"'+(Join-Path $repo 'tools\research_restart_receipt.py')+'"') -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $base 'restart_receipt.stdout') -RedirectStandardError (Join-Path $base 'restart_receipt.stderr')}
            $lastReceipt=[datetime]::UtcNow
    }
    $value=@{recovery_pid=$PID;host_utc=[datetime]::UtcNow.ToString('o');xm_process_count=$xm.Count;capture_watchdog_count=$watch.Count;actions=$actions;dry_run=[bool]$DryRun;live_trading=$false;no_backfill=$true;scope='EXACT_XM_AND_OWN_WATCHDOG_NTS';requires_user_logon=$true}
    $target=Join-Path $base 'recovery_status.json'
    $temporary=$target+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
    [IO.File]::WriteAllText($temporary,($value | ConvertTo-Json -Depth 5))
    if([IO.File]::Exists($target)){[IO.File]::Replace($temporary,$target,[NullString]::Value)}else{[IO.File]::Move($temporary,$target)}
    $signature=(@($xm.Count,$watch.Count)+$actions) -join '|'
    if($signature -ne $prior){$event=Join-Path $base ('recovery_events\'+[guid]::NewGuid().ToString('N')+'.json');$value | ConvertTo-Json -Depth 5 | Out-File -LiteralPath $event -Encoding utf8 -NoClobber;$prior=$signature}
    } catch {
        if($Once){throw}
        Write-Warning ('RECOVERY_ITERATION_RETRY: '+$_.Exception.Message)
    }
    if(!$Once){Start-Sleep -Seconds 30}
 }while(!$Once)
}finally{$mutex.ReleaseMutex();$mutex.Dispose()}
