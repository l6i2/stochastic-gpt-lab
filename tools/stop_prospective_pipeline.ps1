$ErrorActionPreference='Stop'
$base=Join-Path (Split-Path -Parent $PSScriptRoot) 'outputs\prospective_derivatives_v1'
$file=Join-Path $base 'enabled.json'
@{enabled=$false;reason='USER_REQUESTED_DERIVED_WORKER_STOP_RAW_CAPTURE_UNCHANGED';host_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $file -Encoding UTF8
# Worker observes the flag between atomic transactions and exits itself.
# No data deletion, raw-capture stop or process termination.
