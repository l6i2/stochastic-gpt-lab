$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$path=Join-Path $root 'tools\research_recovery.ps1'
$source=Get-Content -LiteralPath $path -Raw
$errors=$null;$tokens=$null
[Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors) | Out-Null
if($errors.Count){throw 'POWERSHELL_PARSE_FAILED'}
# Exercise the actual guardian decisions with fake process inventory and dry-run.
# Use an isolated script directory/output root and real read-only XM profile checks.
$temp=Join-Path (Join-Path $root 'outputs') ('stochastic_stability_test_'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $temp 'tools') -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $temp 'tools\research_recovery.ps1'),$source.Replace('Local\StochasticGPTLab_PC_A_Recovery_v1',('Local\StochasticGPTLab_Test_'+[guid]::NewGuid().ToString('N'))))
$global:stabilityTestCases=@()
function Get-CimInstance {param($ClassName) return $global:stabilityTestCases}
function Start-Process {throw 'SYNTHETIC_TEST_ATTEMPTED_REAL_PROCESS_LAUNCH'}
$guardian=Join-Path $temp 'tools\research_recovery.ps1'
$global:stabilityTestCases=@([pscustomobject]@{ExecutablePath='C:\Program Files\XM Global SC MT5 Terminal\terminal64.exe';Name='terminal64.exe';CommandLine='XM'},[pscustomobject]@{ExecutablePath='powershell.exe';Name='powershell.exe';CommandLine=('powershell -File "'+(Join-Path $temp 'tools\new_capture_watchdog.ps1')+'"')})
& $guardian -Once -DryRun
$a=Get-Content (Join-Path $temp 'outputs\pc_a_stability\recovery_status.json') -Raw | ConvertFrom-Json
if($a.actions -contains 'START_EXACT_XM_READONLY' -or $a.actions -contains 'START_OWN_CAPTURE_WATCHDOG'){throw 'HEALTHY_PROCESS_RESTART_ATTEMPT'}
$global:stabilityTestCases=@()
& $guardian -Once -DryRun
$b=Get-Content (Join-Path $temp 'outputs\pc_a_stability\recovery_status.json') -Raw | ConvertFrom-Json
if($b.actions -notcontains 'START_OWN_CAPTURE_WATCHDOG'){throw 'MISSING_CAPTURE_RECOVERY'}
if($b.actions -notcontains 'START_EXACT_XM_READONLY' -and $b.actions -notcontains 'BLOCKED_PROFILE_REQUIRES_REVIEW'){throw 'MISSING_MT5_FAIL_CLOSED_DECISION'}
if($b.actions -notcontains 'CHECK_NTS_DUE_EXISTING_LOCKED_STATION'){throw 'MISSING_NTS_RECOVERY'}
@{status='PASS';checks=@('SYNTAX','HEALTHY_NO_RESTART','MISSING_COLLECTOR_RECOVERY','MISSING_XM_GUARDED_RECOVERY','NTS_DUE_CHECK','NO_REAL_PROCESS_LAUNCH');real_processes_closed=0;test_artifacts=$temp} | ConvertTo-Json
