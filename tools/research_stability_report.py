"""Read-only, sanitized station inspection; no restart or market queries."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.authorized_capture import CaptureManager,STATION,sha
from controller.isolated_observation import host_clock


def powershell(code):
    return json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',code],text=True,encoding='utf8',creationflags=subprocess.CREATE_NO_WINDOW,timeout=30))


def inspect():
    manager=CaptureManager();manager.load()
    scope=str(ROOT).replace("'","''")
    processes=powershell("$r='"+scope+"';$v=@(Get-CimInstance Win32_Process | Where-Object {$_.ExecutablePath -eq 'C:\\Program Files\\XM Global SC MT5 Terminal\\terminal64.exe' -or ($_.CommandLine -like ('*'+$r+'*') -and $_.CommandLine -notmatch '-Command' -and $_.Name -in @('pythonw.exe','powershell.exe'))} | ForEach-Object {$p=$_;$g=Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue;if($g){$role=if($p.Name -eq 'terminal64.exe'){'XM'}elseif($p.CommandLine -like '*research_recovery.ps1*'){'RECOVERY'}elseif($p.CommandLine -like '*new_capture_watchdog.ps1*'){'WATCHDOG'}elseif($p.CommandLine -like '*new_capture_station.py*'){'CAPTURE_LAUNCHER_OR_CHILD'}elseif($p.CommandLine -like '*authenticated_utc_station.py*'){'NTS_TRANSIENT'}elseif($p.CommandLine -like '*research_restart_receipt.py*'){'RECEIPT_TRANSIENT'}else{'OTHER_EXISTING_REPOSITORY_TASK'};@{pid=$p.ProcessId;parent_pid=$p.ParentProcessId;role=$role;working_mb=[math]::Round($g.WorkingSet64/1MB,2);private_mb=[math]::Round($g.PrivateMemorySize64/1MB,2);cpu_seconds=$g.CPU}}});@{processes=$v}|ConvertTo-Json -Depth 5 -Compress")
    tasks=powershell("@{tasks=@(Get-ScheduledTask | Where-Object {$_.TaskName -like 'StochasticGPTLab*'} | ForEach-Object {$t=$_;$i=Get-ScheduledTaskInfo -TaskName $t.TaskName;@{name=$t.TaskName;state=[string]$t.State;last_result=$i.LastTaskResult;enabled=[bool]$t.Settings.Enabled}})}|ConvertTo-Json -Depth 5 -Compress")
    osinfo=powershell("Get-CimInstance Win32_OperatingSystem | ForEach-Object {@{last_boot_host_label=$_.LastBootUpTime.ToUniversalTime().ToString('o');total_memory_mb=[math]::Round($_.TotalVisibleMemorySize/1024,1);available_memory_mb=[math]::Round($_.FreePhysicalMemory/1024,1)}} | ConvertTo-Json -Compress")
    startup=powershell("$v=Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run';@{capture_present=[bool]$v.StochasticGPTLab_PC_A_NewNativeCapture_v1;recovery_present=[bool]$v.StochasticGPTLab_PC_A_Recovery_v1}|ConvertTo-Json -Compress")
    power=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-File',str(ROOT/'tools/research_power.ps1'),'-Action','Audit'],text=True,creationflags=subprocess.CREATE_NO_WINDOW));power.pop('snapshot',None)
    nts=ROOT/'outputs/pc_a_prospective_utc/authenticated_utc';state=json.loads((nts/'state.json').read_text());last=json.loads((nts/state['last_record']).read_text())
    collector=json.loads((manager.root/'collector_status.json').read_text())
    recovery=json.loads((ROOT/'outputs/pc_a_stability/recovery_status.json').read_text(encoding='utf-8-sig'))
    restart=ROOT/'outputs/pc_a_stability/restart'
    return dict(clock=host_clock(),power=power,**processes,**tasks,os=osinfo,startup=startup,
        collector=collector,recovery=recovery,restart=json.loads((restart/'status.json').read_text()),
        saved_restart_receipt_sha256=sha(restart/'latest_pre_restart.json'),
        nts=dict(state=state,record_sha256=sha(nts/state['last_record']),results=[dict(origin=r.get('origin',r.get('measurement',{}).get('origin')),status=r['status']) for r in last['payload']['results']]),
        other_project_actions='NONE_TARGETED_NO_EXTERNAL_BASELINE_TO_CERTIFY_ALL_EXTERNAL_CHANGES',
        power_scope='SHARED_WINDOWS_AC_POLICY',backfill=False,training=False,scoring=False,live_trading=False)


if __name__=='__main__':print(json.dumps(inspect(),indent=2,sort_keys=True))
