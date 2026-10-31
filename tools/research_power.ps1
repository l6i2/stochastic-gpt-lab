param([ValidateSet('Apply','Restore','Audit')][string]$Action='Audit')
$ErrorActionPreference='Stop'
$base=Join-Path (Split-Path -Parent $PSScriptRoot) 'outputs\pc_a_stability'
New-Item -ItemType Directory -Path $base -Force | Out-Null
$snapshot=Join-Path $base 'power_original.json'
function RunPower([string[]]$Arguments) {
    $value=& powercfg @Arguments 2>&1
    if($LASTEXITCODE -ne 0){throw ($value -join "`n")}
    return ($value -join "`n")
}
$scheme=[regex]::Match((RunPower @('/getactivescheme')),'[a-fA-F0-9-]{36}').Value
$items=@(@{sub='SUB_SLEEP';setting='STANDBYIDLE'},@{sub='SUB_SLEEP';setting='HIBERNATEIDLE'},@{sub='SUB_BUTTONS';setting='LIDACTION'})
function ReadValues($id) {
    $values=@()
    foreach($item in $items){
        $query=RunPower @('/qh',$id,$item.sub,$item.setting)
        $hex=[regex]::Matches($query,'0x[0-9a-fA-F]+')
        if($hex.Count -lt 2){throw 'POWER_VALUE_PARSE_FAILED'}
        $values+=@{sub=$item.sub;setting=$item.setting;ac=[Convert]::ToUInt32($hex[$hex.Count-2].Value.Substring(2),16);dc=[Convert]::ToUInt32($hex[$hex.Count-1].Value.Substring(2),16)}
    }
    return $values
}
if($Action -eq 'Apply'){
    if(!(Test-Path -LiteralPath $snapshot)){
        @{scheme=$scheme;values=@(ReadValues $scheme);created_host_utc=[DateTime]::UtcNow.ToString('o');scope='AC_ONLY_MACHINE_POWER_POLICY'} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $snapshot -Encoding UTF8
    }
    $old=Get-Content -LiteralPath $snapshot -Raw | ConvertFrom-Json
    if($scheme -ne $old.scheme){throw 'ACTIVE_SCHEME_CHANGED_NO_AUTOMATIC_OVERRIDE'}
    foreach($item in $items){$null=RunPower @('/setacvalueindex',$scheme,$item.sub,$item.setting,'0')}
    $null=RunPower @('/setactive',$scheme)
}
if($Action -eq 'Restore'){
    $old=Get-Content -LiteralPath $snapshot -Raw | ConvertFrom-Json
    foreach($item in $old.values){$null=RunPower @('/setacvalueindex',$old.scheme,$item.sub,$item.setting,[string]$item.ac)}
    if($scheme -eq $old.scheme){$null=RunPower @('/setactive',$scheme)}
    # Never delete the original snapshot; rollback remains repeatable.
}
$now=@(ReadValues $scheme)
if(Test-Path -LiteralPath $snapshot){
    $old=Get-Content -LiteralPath $snapshot -Raw | ConvertFrom-Json
    foreach($item in $now){$prior=$old.values | Where-Object {$_.setting -eq $item.setting};if($item.dc -ne $prior.dc){throw 'BATTERY_CONFIGURATION_CHANGED'}}
}
@{action=$Action;scheme=$scheme;values=$now;battery_modified=$false;snapshot=$snapshot;host_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Depth 6
