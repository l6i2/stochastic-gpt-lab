"""Provision only the pinned isolated NTS dependencies, never the training venv."""
import hashlib
import json
from pathlib import Path
import ssl
import urllib.request
import zipfile
ROOT=Path(__file__).resolve().parents[1]


def main():
    manifest=json.loads((ROOT/'configs/nts_runtime_dependencies_20261029.json').read_text())
    base=ROOT/'outputs/pc_a_prospective_utc/nts_dependencies';base.mkdir(parents=True,exist_ok=True)
    runtime=base/'runtime';runtime.mkdir(exist_ok=True)
    for item in manifest['wheels']:
        target=base/item['filename']
        if not target.exists():
            # pip's bundled CA supports bootstrap without changing system trust.
            import pip._vendor.certifi
            context=ssl.create_default_context(cafile=pip._vendor.certifi.where())
            with urllib.request.urlopen(item['url'],context=context,timeout=20) as response:body=response.read(10000000)
            if hashlib.sha256(body).hexdigest()!=item['sha256']:raise ValueError('WHEEL_HASH_MISMATCH')
            target.write_bytes(body)
        if hashlib.sha256(target.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('WHEEL_HASH_MISMATCH')
        with zipfile.ZipFile(target) as archive:
            for name in archive.namelist():
                if not (runtime/name).resolve().is_relative_to(runtime.resolve()):raise ValueError('ARCHIVE_PATH_ESCAPE')
            archive.extractall(runtime)
    ca=runtime/'certifi/cacert.pem'
    if hashlib.sha256(ca.read_bytes()).hexdigest()!=manifest['ca_sha256']:raise ValueError('CA_HASH_MISMATCH')
    (base/'mozilla_cacert.pem').write_bytes(ca.read_bytes())
    print('PINNED_ISOLATED_NTS_RUNTIME_READY_NO_GLOBAL_CHANGES')


if __name__=='__main__':main()
