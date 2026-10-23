param(
    [Parameter(Mandatory=$true)][string]$NativeFile,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [string]$TemporaryTaskName = ''
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ClockAttestationNativeRead {
 [DllImport("kernel32.dll")] public static extern void GetSystemTimePreciseAsFileTime(out long value);
 [DllImport("kernel32.dll")] public static extern ulong GetTickCount64();
}
'@
function Read-ObservedClock {
    $clockStart = [ClockAttestationNativeRead]::GetTickCount64()
    $counterStart = [System.Diagnostics.Stopwatch]::GetTimestamp()
    [long]$clockFiletime = 0
    [ClockAttestationNativeRead]::GetSystemTimePreciseAsFileTime([ref]$clockFiletime)
    $clockUtc = [DateTime]::FromFileTimeUtc($clockFiletime)
    $clockLocal = [DateTimeOffset]::Now
    $clockZone = Get-TimeZone
    [ordered]@{
        tick_start_ms = $clockStart
        qpc_start = $counterStart
        qpc_frequency = [System.Diagnostics.Stopwatch]::Frequency
        precise_utc_filetime = $clockFiletime
        precise_utc = $clockUtc.ToString('o')
        local_time = $clockLocal.ToString('o')
        windows_timezone = $clockZone.Id
        qpc_end = [System.Diagnostics.Stopwatch]::GetTimestamp()
        tick_end_ms = [ClockAttestationNativeRead]::GetTickCount64()
    }
}
$clockSource = (& w32tm.exe /query /source 2>&1 | Out-String)
$clockStatus = (& w32tm.exe /query /status 2>&1 | Out-String)
$readyFile = Join-Path $OutputDirectory 'ready.json'
@{ state='ARMED_NO_EXPIRY'; first=(Read-ObservedClock); w32_source=$clockSource; w32_status=$clockStatus; orders_sent=0 } |
    ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $readyFile -Encoding UTF8
$markerFile = Join-Path (Split-Path -Parent $NativeFile) 'attest_20261023_a2_markers.txt'
$stream = New-Object System.IO.StreamWriter((Join-Path $OutputDirectory 'windows_observations.jsonl'), $false, [System.Text.Encoding]::UTF8)
try {
    $clockPrior = Read-ObservedClock
    while ($true) {
        $clockNow = Read-ObservedClock
        if (Test-Path -LiteralPath $NativeFile) {
            @{ before=$clockPrior; after=$clockNow; native_bytes=(Get-Item -LiteralPath $NativeFile).Length } |
                ConvertTo-Json -Depth 8 -Compress | ForEach-Object { $stream.WriteLine($_) }
            $stream.Flush()
            if ((Test-Path -LiteralPath $markerFile) -and
                ([System.IO.File]::ReadAllText($markerFile).Contains('CLOCK_ATTESTATION_END'))) { break }
        }
        $clockPrior = $clockNow
        Start-Sleep -Milliseconds 100
    }
    @{ state='CAPTURE_COMPLETE'; last=(Read-ObservedClock); orders_sent=0 } |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $readyFile -Encoding UTF8
} finally {
    $stream.Dispose()
    if ($TemporaryTaskName) {
        Unregister-ScheduledTask -TaskName $TemporaryTaskName -Confirm:$false -ErrorAction SilentlyContinue
    }
}
