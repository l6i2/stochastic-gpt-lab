"""Fresh NTS evidence for activation only; no old station state or clock changes."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]


def sample(origin='time.cloudflare.com'):
    if origin not in ('time.cloudflare.com','ntppool2.time.nl'):
        raise ValueError('UNAPPROVED_NTS_ORIGIN')
    manifest=json.loads((ROOT/'configs/nts_runtime_dependencies_20261029.json').read_text())
    dependencies=ROOT/'outputs/pc_a_prospective_utc/nts_dependencies'
    runtime=dependencies/'runtime'
    for name,expected in manifest['runtime_files'].items():
        path=(runtime/name).resolve()
        if not path.is_relative_to(runtime.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('NTS_RUNTIME_HASH_MISMATCH')
    ca=dependencies/'mozilla_cacert.pem'
    if hashlib.sha256(ca.read_bytes()).hexdigest()!=manifest['ca_sha256']:
        raise ValueError('NTS_CA_HASH_MISMATCH')
    sys.path.insert(0,str(runtime));sys.path.insert(0,str(ROOT/'python'))
    from nts_external import measure
    return measure(origin,ca)


if __name__=='__main__':
    print(json.dumps(sample(sys.argv[1] if len(sys.argv)>1 else 'time.cloudflare.com'),sort_keys=True))
