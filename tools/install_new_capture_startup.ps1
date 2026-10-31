$ErrorActionPreference = 'Stop'
$captureRepo = Split-Path -Parent $PSScriptRoot
$captureBase = Join-Path $captureRepo 'outputs\new_native_studies\us30cash_m5_native_20261030_01'
$captureWatchdog = Join-Path $captureRepo 'tools\new_capture_watchdog.ps1'
$captureName = 'StochasticGPTLab_PC_A_NewNativeCapture_v1'
$capturePowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$captureArguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $captureWatchdog + '"'
$captureCommand = '"' + $capturePowerShell + '" ' + $captureArguments
$captureKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$capturePrior = $null
try { $capturePrior = Get-ItemPropertyValue -Path $captureKey -Name $captureName -ErrorAction Stop } catch [System.Management.Automation.PSArgumentException] { $capturePrior = $null }
if ($capturePrior -and $capturePrior -ne $captureCommand) { throw 'STARTUP_VALUE_CONFLICT_NO_OTHER_PROJECT_MODIFIED' }
New-Item -Path $captureKey -Force | Out-Null
New-ItemProperty -Path $captureKey -Name $captureName -Value $captureCommand -PropertyType String -Force | Out-Null
$captureProcess = Start-Process -FilePath $capturePowerShell -ArgumentList $captureArguments -WorkingDirectory $captureRepo -WindowStyle Hidden -PassThru
@{mode='PER_USER_STARTUP_AND_LOCAL_WATCHDOG';startup_value_name=$captureName;watchdog_pid=$captureProcess.Id;registry_value_verified=((Get-ItemPropertyValue -Path $captureKey -Name $captureName) -eq $captureCommand);admin_privilege_required=$false;credentials_requested=$false;old_tasks_modified=$false;requires_user_logon_and_awake_pc=$true} | ConvertTo-Json -Compress
