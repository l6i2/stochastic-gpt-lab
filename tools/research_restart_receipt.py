"""Refresh a pre-reboot receipt and preserve the first post-boot comparison."""
import json,sys,hashlib,subprocess
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.authorized_capture import CaptureManager,manager_lock
from controller.cf_recovery import recover
from controller.isolated_observation import atomic,host_clock
from controller.restart_readiness import receipt,verify_previous,transition


def windows_events(start, end):
    # Both arguments come from verified clock labels and are normalized before quoting.
    start, end = (datetime.fromisoformat(value).isoformat() for value in (start, end))
    script = """
$events = @(Get-WinEvent -FilterHashtable @{LogName='System';StartTime=([datetimeoffset]'START').LocalDateTime;EndTime=([datetimeoffset]'END').LocalDateTime;Id=12,13,41,1074} -ErrorAction SilentlyContinue | Sort-Object RecordId | ForEach-Object {
    $intent=''
    if($_.ProviderName -eq 'User32' -and $_.Id -eq 1074){$xml=[xml]$_.ToXml();$intent=[string]($xml.Event.EventData.Data | Where-Object Name -eq 'param5').'#text'}
    @{id=$_.Id;provider=$_.ProviderName;record=$_.RecordId;time=$_.TimeCreated.ToUniversalTime().ToString('o');intent=$intent}
})
ConvertTo-Json -InputObject $events -Compress
""".replace('START',start).replace('END',end)
    try:
        result = subprocess.run(['powershell.exe','-NoProfile','-Command',script], capture_output=True,
                                text=True, check=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
        return json.loads(result.stdout)
    except (subprocess.SubprocessError, ValueError, OSError):
        return []


def run():
    cf = ROOT/'outputs/us30cash_m5_native_observations'
    if (cf/'legacy_ingress_closed.json').exists():
        with manager_lock(cf/'recovery'):
            return recover(ROOT,host_clock(),windows_events)
    import msvcrt
    base=ROOT/'outputs/pc_a_stability/restart';base.mkdir(parents=True,exist_ok=True)
    with (base/'monitor.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        manager=CaptureManager();manager.load();clock=host_clock()
        latest=base/'latest_pre_restart.json'
        old=json.loads(latest.read_text()) if latest.exists() else None
        current=receipt(manager.root,clock)
        if old:
            verify_previous(manager.root,old)
            outcome=transition(old,current)
            if outcome['boot_transition_observed']:
                # Preserve both sides, including a non-resumed first observation.
                body=dict(previous=old,current=current,outcome=outcome)
                digest=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
                pending=outcome['restart_recovery']=='WAITING_FOR_FRESH_NEW_BOOT_SEGMENT'
                name=('pending_boot_'+hashlib.sha256((old['clock']['boot_id']+'_'+clock['boot_id']).encode()).hexdigest()) if pending else ('transition_'+digest)
                target=base/(name+'.json')
                if not target.exists():
                    with target.open('x',encoding='utf8') as stream:json.dump(body,stream,sort_keys=True)
                if outcome['restart_recovery']=='WAITING_FOR_FRESH_NEW_BOOT_SEGMENT':
                    atomic(base/'status.json',outcome);return outcome
                atomic(base/'last_verified_boot_transition.json',dict(file=target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
        else:outcome=dict(restart_recovery='BASELINE_SAVED_WAITING_FOR_NATURAL_RESTART',physical_power_cycle_proven=False)
        proof=base/'last_verified_boot_transition.json'
        if proof.exists():outcome['last_verified_boot_transition']=json.loads(proof.read_text())
        atomic(latest,current);atomic(base/'status.json',outcome)
        return outcome


if __name__=='__main__':
    try:print(json.dumps(run()))
    except Exception as exc:
        print(json.dumps(dict(status='RETRY_REQUIRED_FAIL_CLOSED',error=type(exc).__name__,reason=str(exc))));sys.exit(1)
