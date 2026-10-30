import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from controller.pretrain_contracts import seal,chain
from controller.pretrain_package import inventory,raw_metadata,verify_package,digest


class PretrainPackageTests(unittest.TestCase):
    def fixture(self, root):
        folder=root/'historical_fixture';folder.mkdir()
        asset=dict(file='private.csv.gz',rows=2,sha256='a'*64)
        entry=dict(start_native_msc=100,end_native_msc=200,previous=None,ticks=asset,bars=asset)
        entry['entry_sha256']=seal(entry)
        d=dict(archive_id=folder.name,kind='historical',server='XMGlobalSC-MT5 5',symbol='US30Cash',
               collector_sha256='b'*64,native_start_msc=100,native_end_exclusive_msc=200,
               next_native_msc=200,chain_head=entry['entry_sha256'],segments=[entry],
               scientific_acceptance=False,train_access_allowed=False,evaluation_authorized=False,
               maturity_eligible=False,live_trading=False)
        path=folder/'manifest.json';path.write_text(json.dumps(d))
        return path,d

    def test_inventory_never_opens_or_hashes_protected_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p=root/'outputs/splits/FINAL_TEST.parquet';p.parent.mkdir(parents=True);p.write_bytes(b'NEVER_OPEN')
            with patch.object(Path,'open',side_effect=AssertionError('PROTECTED_IO_FORBIDDEN')):
                report=inventory(root)
            self.assertEqual(report['groups']['outputs/splits/FINAL_TEST.parquet']['rows_opened'],0)
            self.assertEqual(report['protected_dataset_rows_opened'],0)
            self.assertFalse(report['independent_data_proven'])

    def test_raw_chain_validation_never_opens_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,_=self.fixture(Path(tmp))
            # No raw file even exists: metadata validation must not claim it does.
            report=raw_metadata(path,'b'*64)
            self.assertEqual(report['declared_ticks'],2)
            self.assertTrue(report['raw_payload_integrity'].startswith('NOT_RECHECKED'))
            self.assertTrue(report['completeness'].startswith('UNPROVEN'))

    def test_wrong_feed_source_gates_or_cursor_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,d=self.fixture(Path(tmp))
            for change in ({'server':'ANOTHER_SERVER'},{'symbol':'ANOTHER_SYMBOL'},
                           {'collector_sha256':'c'*64},{'scientific_acceptance':True},
                           {'next_native_msc':201},{'chain_head':'c'*64}):
                path.write_text(json.dumps(d|change))
                with self.assertRaises(ValueError):raw_metadata(path,'b'*64)

    def test_changing_interval_or_count_is_not_valid_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,d=self.fixture(Path(tmp))
            d['segments'][0]['end_native_msc']=201
            path.write_text(json.dumps(d))
            with self.assertRaises(ValueError):raw_metadata(path)

    def package_fixture(self, root, authorize=False):
        entries=chain([{'instrument':'SYNTHETIC'}])
        (root/'exposure_ledger.json').write_text(json.dumps(dict(entries=entries,chain_head=entries[-1]['entry_sha256'])))
        (root/'scientific_authorization_package.json').write_text(json.dumps(dict(
            authorization_requested=False,authorization_ready=False,
            actual_training_authorized=authorize,actual_scoring_authorized=False)))
        hashes={p.name:digest(p) for p in root.iterdir() if p.name!='package_hashes.json'}
        (root/'package_hashes.json').write_text(json.dumps(dict(files=hashes,root_sha256=seal(hashes))))

    def test_package_integrity_does_not_authorize_and_detects_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.package_fixture(root)
            self.assertFalse(verify_package(root)['training_authorized'])
            (root/'exposure_ledger.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'FILE_CHANGED'):verify_package(root)

    def test_rehashing_cannot_convert_pre_train_package_to_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.package_fixture(root,authorize=True)
            with self.assertRaisesRegex(ValueError,'AUTHORITY_EXCEEDED'):verify_package(root)


if __name__=='__main__':unittest.main()
