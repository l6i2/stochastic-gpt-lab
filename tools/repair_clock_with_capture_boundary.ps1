# Explicit clock-maintenance boundary. Invoke only through normal Windows UAC.
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$folder = Join-Path $repo ('outputs\pc_a\clock_boundary_' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $folder | Out-Null
$python = Join-Path $repo '.venv\Scripts\python.exe'
$station = Join-Path $PSScriptRoot 'research_station.py'
@{utc=[DateTime]::UtcNow.ToString('o'); stopwatch_ticks=[Diagnostics.Stopwatch]::GetTimestamp(); stopwatch_frequency=[Diagnostics.Stopwatch]::Frequency; kind='BEFORE_WINDOWS_TIME_MAINTENANCE'; scientific_acceptance=$false} | ConvertTo-Json | Set-Content (Join-Path $folder 'before.json')
try {
    & $python $station stop | Out-File (Join-Path $folder 'collector_pause.json')
    if ($LASTEXITCODE -ne 0) { throw 'Collector pause failed' }
    # Allow the already-started bounded collector invocation to finish; no kill.
    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    while ((Get-ScheduledTask -TaskName 'StochasticGPTLab_PC_A_RawQuarantine_v1').State -eq 'Running') {
        if ([DateTime]::UtcNow -gt $deadline) { throw 'Active collector did not finish; no clock adjustment attempted' }
        Start-Sleep -Seconds 1
    }
    & (Join-Path $PSScriptRoot 'repair_pc_a_clock.ps1')
    $repairExit = $LASTEXITCODE
} finally {
    @{utc=[DateTime]::UtcNow.ToString('o'); stopwatch_ticks=[Diagnostics.Stopwatch]::GetTimestamp(); stopwatch_frequency=[Diagnostics.Stopwatch]::Frequency; kind='AFTER_WINDOWS_TIME_MAINTENANCE'; scientific_acceptance=$false} | ConvertTo-Json | Set-Content (Join-Path $folder 'after.json')
    & $python $station resume | Out-File (Join-Path $folder 'collector_resume.json')
}
@{repair_exit=$repairExit; normalized_timestamps_rewritten=$false; event_mapping_authorized=$false} | ConvertTo-Json | Set-Content (Join-Path $folder 'result.json')
exit $repairExit
