"""Automated PRE_TRAIN preparation; metadata/synthetic tests only, no activation."""
import io
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'python'))


def main():
    from local_finalize import verify_source_manifest
    from controller.pretrain_package import build,verify_package,PACKAGE,digest
    from controller.pretrain_contracts import seal
    verify_source_manifest(ROOT/'configs/pc_a_source_hashes_20261030_v24.json')
    gates=build()
    patterns=['test_pretrain_contracts.py','test_pretrain_package.py','test_native_independence.py',
              'test_native_study_design.py','test_native_methodology_proposal.py']
    suite=unittest.TestSuite()
    for pattern in patterns:
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
    transcript=io.StringIO()
    result=unittest.TextTestRunner(stream=transcript,verbosity=2).run(suite)
    report=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                skipped=len(result.skipped),patterns=patterns,transcript=transcript.getvalue(),
                real_dataset_training_or_scoring=False,native_MT5_probes_rerun=False)
    (PACKAGE/'validation.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    if not result.wasSuccessful():raise SystemExit(1)
    hashes={p.name:digest(p) for p in sorted(PACKAGE.iterdir()) if p.is_file() and p.name!='package_hashes.json'}
    (PACKAGE/'package_hashes.json').write_text(json.dumps(dict(files=hashes,root_sha256=seal(hashes)),indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    checked=verify_package()
    print(json.dumps(dict(status=gates['NEW_STUDY_PACKAGE'],tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),integrity=checked['integrity'],
        independent_data=gates['INDEPENDENT_DATA_AVAILABLE'],training_authorized=False)))


if __name__=='__main__':main()
