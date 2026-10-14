import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from python.membership_contract import derive, digest, quarantine_windows


class MembershipContractTests(unittest.TestCase):
    def test_endpoint_exclusion_is_pinned_and_never_extends_splits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'outputs/master').mkdir(parents=True)
            (root/'outputs/splits').mkdir()
            split = root/'outputs/splits/split_manifest.json'
            split.write_text(json.dumps({'boundaries': {'final_test_start_signal_time_msc':
                int(datetime(2026, 3, 20, tzinfo=timezone.utc).timestamp()*1000)}}))
            pins = []
            for year in (2024, 2025):
                folder = root/'outputs/history/raw'/str(year)
                folder.mkdir(parents=True)
                source = folder/'stochastic_events.csv'
                stamp = int(datetime(year, 12, 30, tzinfo=timezone.utc).timestamp()*1000)
                source.write_text(f'signal_id,signal_time_msc\ns{year},{stamp}\n')
                metadata = dict(period=f'{year}-01-01..{year}-12-31', csv_sha256=digest(source), signals=1)
                (folder/'manifest.json').write_text(json.dumps(metadata))
                pins.append(hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest())
            (root/'outputs/master/master_manifest.json').write_text(json.dumps({'source_block_manifest_hashes': pins}))
            record = derive(root)
            self.assertFalse(record['selection_uses_outcomes'])
            contract = root/'contract.json'
            contract.write_text(json.dumps(record))
            self.assertEqual(len(quarantine_windows(contract, split, root)), 2)
            source.write_text(source.read_text()+'unrecognized,1\n')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                quarantine_windows(contract, split, root)
