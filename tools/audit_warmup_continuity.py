"""One-shot counter and checkpoint verification, never changes a producer."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.warmup_diagnostics import inspect
from controller.isolated_observation import atomic

def main():
    pointer=json.loads((ROOT/'outputs/new_native_studies/us30cash_m5_native_20261030_01/current_capture.json').read_text())
    capture=pointer['capture_id']
    if Path(capture).name!=capture:raise ValueError('UNSAFE_CAPTURE_ID')
    result=inspect(ROOT/'outputs/prospective_derivatives_v1'/capture/'quarantine.sqlite3')
    atomic(ROOT/'outputs/status/WARMUP_CONTINUITY.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
