param([ValidateSet('STATUS','RESUME')][string]$Action='STATUS')
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$name='StochasticGPTLab_PC_A_RecoveryGuardian_v1'
if($Action -eq 'RESUME'){
    # Validate the existing task's exact scope before requesting its idempotent guardian.
    & (Join-Path $PSScriptRoot 'ensure_research_guardian.ps1') | Out-Null
    $task=Get-ScheduledTask -TaskName $name
    if($task.State -ne 'Running'){Start-ScheduledTask -TaskName $name}
}
$dashboard=Join-Path $repo 'outputs\research_readiness\status.json'
$recovery=Join-Path $repo 'outputs\pc_a_stability\recovery_status.json'
$value=[ordered]@{action=$Action;observed_local=(Get-Date).ToString('o');training_started=$false;orders_sent=0}
foreach($item in @(@('estado_cientifico',$dashboard),@('supervision',$recovery))){
    if(Test-Path -LiteralPath $item[1]){
        $value[$item[0]]=@{report_age_seconds=[math]::Round(((Get-Date)-(Get-Item -LiteralPath $item[1]).LastWriteTime).TotalSeconds,1);report=(Get-Content -LiteralPath $item[1] -Raw | ConvertFrom-Json)}
    }else{$value[$item[0]]=@{status='MISSING_FAIL_CLOSED'}}
}
$value | ConvertTo-Json -Depth 16
