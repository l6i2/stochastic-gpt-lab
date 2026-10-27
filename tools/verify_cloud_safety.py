"""Static no-order checks and retained MAIN_K evidence integrity; no market I/O."""
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def verify():
    count = 0
    forbidden = {'order_send', 'OrderSend', 'OrderSendAsync', 'PositionOpen'}
    for directory in ('python', 'controller', 'scripts', 'tools'):
        for path in (ROOT / directory).rglob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
                    if name in forbidden:
                        raise ValueError('ORDER_API_CALL:' + str(path.relative_to(ROOT)))
            count += 1
    probe = ROOT / 'tests/mql5/FullClockAndTimeSemanticsProbe.mq5'
    if re.search(r'\b(OrderSend|OrderSendAsync|CTrade|PositionOpen)\b', probe.read_text(), re.I):
        raise ValueError('ORDER_API_IN_PROBE')
    folder = ROOT / 'configs/main_k_native_evidence_20261023'
    report = json.loads((folder / 'validated_audit.json').read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    if sha(folder / 'validated_audit.json') != (folder / 'validated_audit.sha256').read_text().split()[0]:
        raise ValueError('MAIN_K_AUDIT_SEAL_CHANGED')
    for name, expected in report['artifacts_sha256'].items():
        if sha(folder / name) != expected:
            raise ValueError('MAIN_K_EVIDENCE_CHANGED')
    if report['status'] != 'PASS' or sha(ROOT / 'mt5/StochasticBarDecisionResearchEA.mq5') != report['production_source_sha256']:
        raise ValueError('MAIN_K_PRODUCTION_OR_STATUS_CHANGED')
    result = {'static_no_order_calls': 'PASS', 'python_sources_checked': count,
              'main_k_parity': 'PASS', 'main_k_scope': 'RETAINED_NATIVE_EVIDENCE_HASHES_VERIFIED_NOT_RERUN',
              'master_native_compile_run': 'LOCAL_REQUIRED', 'live_trading': False}
    print(json.dumps(result, sort_keys=True))
    return result


if __name__ == '__main__':
    verify()
