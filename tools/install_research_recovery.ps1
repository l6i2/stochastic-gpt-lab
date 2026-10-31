param([switch]$Remove)
$ErrorActionPreference='Stop'
$key='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$name='StochasticGPTLab_PC_A_Recovery_v1'
$script=Join-Path $PSScriptRoot 'research_recovery.ps1'
$command='"'+(Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe')+'" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$script+'"'
if($Remove){Remove-ItemProperty -LiteralPath $key -Name $name -ErrorAction SilentlyContinue;return}
$old=$null
try{$old=Get-ItemPropertyValue -LiteralPath $key -Name $name -ErrorAction Stop}catch [System.Management.Automation.PSArgumentException]{}
if($old -and $old -ne $command){throw 'RECOVERY_STARTUP_CONFLICT'}
New-ItemProperty -LiteralPath $key -Name $name -Value $command -PropertyType String -Force | Out-Null
Start-Process powershell.exe -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+$script+'"') -WindowStyle Hidden | Out-Null
