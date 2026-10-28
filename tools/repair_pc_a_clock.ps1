# Run only through the normal UAC elevation flow. No research process is started.
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$folder = Join-Path $repo ('outputs\pc_a\clock_repair_' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $folder | Out-Null
& w32tm /query /configuration 2>&1 | Out-File (Join-Path $folder 'configuration_before.txt')
& w32tm /query /status /verbose 2>&1 | Out-File (Join-Path $folder 'status_before.txt')
Get-CimInstance Win32_Service -Filter "Name='W32Time'" | Select-Object Name,StartMode,State | ConvertTo-Json | Set-Content (Join-Path $folder 'service_before.json')
Set-Service W32Time -StartupType Automatic
Start-Service W32Time
if ((Get-Service W32Time).Status -ne 'Running') { throw 'Windows Time did not start' }
& w32tm /resync /rediscover 2>&1 | Out-File (Join-Path $folder 'resync.txt')
$resyncExit = $LASTEXITCODE
& w32tm /query /status /verbose 2>&1 | Out-File (Join-Path $folder 'status_after.txt')
& w32tm /query /source 2>&1 | Out-File (Join-Path $folder 'source_after.txt')
Get-Service W32Time | Select-Object Name,Status,StartType | ConvertTo-Json | Set-Content (Join-Path $folder 'service_after.json')
@{resync_exit=$resyncExit; attestation='PENDING'; mapping='PENDING'} | ConvertTo-Json | Set-Content (Join-Path $folder 'result.json')
exit $resyncExit
