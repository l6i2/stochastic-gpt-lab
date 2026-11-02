param([switch]$Once,[switch]$DryRun)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$base=Join-Path $repo 'outputs\pc_a_stability'
$terminal='C:\Program Files\XM Global SC MT5 Terminal\terminal64.exe'
$data=Join-Path $env:APPDATA 'MetaQuotes\Terminal\20C285FE08971A9A2E814AAC44AFC9D2'
$mutex=New-Object System.Threading.Mutex($false,'Local\StochasticGPTLab_PC_A_Recovery_v1')
if(!$mutex.WaitOne(0)){$mutex.Dispose();exit 0}
New-Item -ItemType Directory -Path (Join-Path $base 'recovery_events') -Force | Out-Null
$config=Join-Path $base 'xm_readonly_restart.ini'
$expected="[Experts]`r`nEnabled=1`r`nAllowLiveTrading=0`r`nAllowDllImport=0`r`n[Charts]`r`nProfileLast=Default`r`n"
if(Test-Path -LiteralPath $config){if([IO.File]::ReadAllText($config) -ne $expected){throw 'RECOVERY_CONFIG_CHANGED'}}else{[IO.File]::WriteAllText($config,$expected)}
$nts=$null;$receipt=$null;$lastDashboard=[datetime]::MinValue;$lastPipeline=[datetime]::MinValue;$lastReceipt=[datetime]::MinValue;$lastNts=[datetime]::MinValue;$lastLaunch=[datetime]::MinValue;$prior=''
try{
 do {
    $processes=@(Get-CimInstance Win32_Process)
    $xm=@($processes | Where-Object {$_.ExecutablePath -eq $terminal})
    $watch=@($processes | Where-Object {$_.Name -eq 'powershell.exe' -and $_.CommandLine -like ('*"'+(Join-Path $repo 'tools\new_capture_watchdog.ps1')+'"*')})
    $actions=@()
    $dashboardScript=Join-Path $repo 'tools\research_dashboard.py'
    $dashboard=@($processes|Where-Object {$_.Name -eq 'pythonw.exe' -and $_.CommandLine -like ('*"'+$dashboardScript+'" --serve*')})
    if($dashboard.Count -eq 0 -and ([datetime]::UtcNow-$lastDashboard).TotalSeconds -ge 60){
        $actions+='START_READ_ONLY_ADMISSION_DASHBOARD'
        if(!$DryRun){Start-Process (Join-Path $repo '.venv\Scripts\pythonw.exe') -ArgumentList ('"'+$dashboardScript+'" --serve') -WorkingDirectory $repo -WindowStyle Hidden -RedirectStandardOutput (Join-Path $repo 'outputs\research_readiness\reporter.stdout') -RedirectStandardError (Join-Path $repo 'outputs\research_readiness\reporter.stderr')}
        $lastDashboard=[datetime]::UtcNow
    }
    $pipelineEnable=Join-Path $repo 'outputs\prospective_derivatives_v1\enabled.json'
    if(Test-Path -LiteralPath $pipelineEnable){
        $pipelineEnabled=(Get-Content -LiteralPath $pipelineEnable -Raw | ConvertFrom-Json).enabled
        $pipelineScript=Join-Path $repo 'tools\prospective_pipeline.py'
        $pipeline=@($processes | Where-Object {$_.Name -eq 'pythonw.exe' -and $_.CommandLine -like ('*"'+$pipelineScript+'" --serve*')})
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
        if($valid -and !$unsafe -and $binaryValid){
            $actions+='START_EXACT_XM_READONLY'
            if(!$DryRun){Start-Process -FilePath $terminal -ArgumentList ('/config:"'+$config+'"') -WindowStyle Hidden | Out-Null}
        }else{$actions+='BLOCKED_PROFILE_REQUIRES_REVIEW'}
        $lastLaunch=[datetime]::UtcNow
    }
    if($watch.Count -eq 0){$actions+='START_OWN_CAPTURE_WATCHDOG';if(!$DryRun){Start-Process powershell.exe -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+(Join-Path $repo 'tools\new_capture_watchdog.ps1')+'"') -WindowStyle Hidden | Out-Null}}
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
    $value | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $base 'recovery_status.json') -Encoding UTF8
    $signature=(@($xm.Count,$watch.Count)+$actions) -join '|'
    if($signature -ne $prior){$event=Join-Path $base ('recovery_events\'+[guid]::NewGuid().ToString('N')+'.json');$value | ConvertTo-Json -Depth 5 | Out-File -LiteralPath $event -Encoding utf8 -NoClobber;$prior=$signature}
    if(!$Once){Start-Sleep -Seconds 30}
 }while(!$Once)
}finally{$mutex.ReleaseMutex();$mutex.Dispose()}
