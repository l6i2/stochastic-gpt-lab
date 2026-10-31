$ErrorActionPreference = 'Stop'
$captureRepo = Split-Path -Parent $PSScriptRoot
$captureBase = Join-Path $captureRepo 'outputs\new_native_studies\us30cash_m5_native_20261030_01'
$capturePython = Join-Path $captureRepo '.venv\Scripts\pythonw.exe'
$captureScript = Join-Path $captureRepo 'tools\new_capture_station.py'
$captureMutex = New-Object System.Threading.Mutex($false, 'Local\StochasticGPTLab_PC_A_NewCaptureWatchdog_v1')
if (-not $captureMutex.WaitOne(0)) { $captureMutex.Dispose(); exit 0 }
$captureChild = $null
$captureLaunches = 0
try {
    while ($true) {
        if ($null -eq $captureChild -or $captureChild.HasExited) {
            $captureLogDir = Join-Path $captureBase 'watchdog_logs'
            New-Item -ItemType Directory -Path $captureLogDir -Force | Out-Null
            $captureLogId = [guid]::NewGuid().ToString('N')
            $captureChild = Start-Process -FilePath $capturePython -ArgumentList @(('"' + $captureScript + '"'), '--serve') -WorkingDirectory $captureRepo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $captureLogDir ($captureLogId + '.stdout.log')) -RedirectStandardError (Join-Path $captureLogDir ($captureLogId + '.stderr.log'))
            $captureLaunches++
        }
        $captureValue = @{status='WATCHDOG_RUNNING';watchdog_pid=$PID;child_pid=$captureChild.Id;child_has_exited=$captureChild.HasExited;launches=$captureLaunches;check_interval_seconds=5;training_authorized=$false;scoring_authorized=$false;live_trading=$false}
        $captureTemp = Join-Path $captureBase ('watchdog_status.' + [guid]::NewGuid().ToString('N') + '.tmp')
        [System.IO.File]::WriteAllText($captureTemp, ($captureValue | ConvertTo-Json -Compress), (New-Object System.Text.UTF8Encoding($false)))
        Move-Item -LiteralPath $captureTemp -Destination (Join-Path $captureBase 'watchdog_status.json') -Force
        Start-Sleep -Seconds 5
    }
} finally {
    $captureMutex.ReleaseMutex()
    $captureMutex.Dispose()
}
