"""Read-only migration preflight. Never starts collection, evaluation, or orders."""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from controller.mt5_env import status
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
    blockers = []
    if git('branch', '--show-current') != 'research/full-pipeline':
        blockers.append('WRONG_BRANCH')
    if git('remote', 'get-url', 'origin') != 'https://github.com/l6i2/stochastic-gpt-lab.git':
        blockers.append('WRONG_ORIGIN')
    clock = subprocess.run(['w32tm', '/query', '/status', '/verbose'], capture_output=True)
    # A migration handoff is evidence of readiness only after a separately reviewed attestation.
    handoff_path = ROOT / 'outputs/status/PC_A_HANDOFF.json'
    handoff = json.loads(handoff_path.read_text(encoding='utf-8-sig')) if handoff_path.exists() else {}
    if clock.returncode or handoff.get('clock_status') != 'PASS':
        blockers.append('CLOCK_ATTESTATION_REQUIRED')
    environment = status()
    # Do not persist account identifiers or broker credentials in the station status.
    if environment.get('ACCOUNT_MODE') != 'DEMO' or not environment.get('CONNECTED'):
        blockers.append('CONNECTED_XM_DEMO_REQUIRED')
    if environment.get('US30Cash_AVAILABLE') is not True:
        blockers.append('US30Cash_UNVERIFIED')
    if handoff.get('collector_status') != 'CONTINUITY_VERIFIED':
        blockers.append('COHORT_CONTINUITY_UNPROVEN')
    # Startup wiring is deliberately gated until actual local operational acceptance.
    blockers.append('READ_ONLY_PREFLIGHT_ONLY_COMPONENT_START_NOT_ACCEPTED')
    report = dict(status='BLOCKED', blockers=blockers, observed_utc=datetime.now(timezone.utc).isoformat(),
                  clock_timestamp_trusted=False, low_memory_mode=True, orders_sent=0,
                  collector_started=False, final_test='LOCKED', demo='DISABLED', live_trading=False)
    folder = ROOT / 'outputs/pc_a'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'station_status.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, target)
    print(json.dumps(report, indent=2))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
