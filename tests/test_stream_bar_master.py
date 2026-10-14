import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from python.membership_contract import digest
from python.parquet_io import read_parquet, write_parquet
from python.stream_bar_master import build
from python.validate_intratrade_dataset import REQUIRED_FEATURE_COLUMNS


class StreamingMasterTests(unittest.TestCase):
    def test_chunked_build_preserves_membership_timestamps_and_execution_separation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            block = root/'block'
            block.mkdir()
            train = root/'train.parquet'
            validation = root/'validation.parquet'
            write_parquet(pd.DataFrame({'signal_id':['train']}), train)
            write_parquet(pd.DataFrame({'signal_id':['validation']}), validation)
            epoch = lambda year: int(datetime(year,6,1,tzinfo=timezone.utc).timestamp()*1000)+299999
            boundary = int(datetime(2025,1,1,tzinfo=timezone.utc).timestamp()*1000)
            final = int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp()*1000)
            split = root/'split.json'
            split.write_text(json.dumps({'boundaries':{'validation_start_signal_time_msc':boundary,
                                                       'final_test_start_signal_time_msc':final},
                                         'train_parquet_sha256':digest(train),
                                         'validation_parquet_sha256':digest(validation)}))
            rows = []
            events = []
            fills = []
            for signal, stamp in (('train',epoch(2024)),('validation',epoch(2025))):
                events.append(dict(signal_id=signal,signal_time_msc=stamp,tp_distance=240,sl_distance=180,
                                   time_exit_bars=100,follow_side='BUY',invert_side='SELL',
                                   follow_exit_reason='END_OF_DATA',invert_exit_reason='END_OF_DATA',
                                   follow_exit_time=stamp+800000,invert_exit_time=stamp+800000,
                                   follow_bars_in_trade=2,invert_bars_in_trade=2))
                for mode, side in (('FOLLOW','BUY'),('INVERT','SELL')):
                    row = {name:1 for name in REQUIRED_FEATURE_COLUMNS}
                    row.update(snapshot_id=f'{signal}_{mode}_1', signal_id=signal,symbol='US30Cash',
                               signal_time_msc=stamp,original_signal='BUY',virtual_mode=mode,virtual_side=side,
                               entry_time_msc=stamp+1,snapshot_bar=1,snapshot_time_msc=stamp+300000,
                               feature_max_time_msc=stamp+300000,mark_time_msc=stamp+299999,
                               current_ask=2,distance_to_tp=239,distance_to_sl=181)
                    rows.append(row)
                    fills.append(dict(snapshot_id=row['snapshot_id'],signal_id=signal,virtual_mode=mode,
                                      snapshot_bar=1,decision_cutoff_msc=stamp+300000,
                                      execution_time_msc=stamp+300001,execution_bid=1,execution_ask=2))
            def table(name, data):
                with (block/name).open('w',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=list(data[0]))
                    writer.writeheader();writer.writerows(data)
            table('intratrade_snapshots.csv',rows)
            table('stochastic_events.csv',events)
            table('bar_execution_quotes.csv',fills)
            (block/'intratrade_snapshot_targets.csv').write_text('')
            (block/'stochastic_events.csv.audit.json').write_text('{}')
            (block/'intratrade_snapshots.csv.audit.json').write_text(json.dumps(dict(
                schema_version='3.0',LIVE_TRADING=False,optimization='OFF',aborted=False,
                snapshot_schedule=','.join(map(str,range(1,101))),signals=2,snapshot_rows=4,target_rows=0)))
            names=[p.name for p in block.iterdir()]
            metadata=dict(producer_schema='3.0',max_signal_time_msc=epoch(2025),run_id='run',
                          period=['2024-01-01','2025-12-31'],LIVE_TRADING=False,optimization='OFF',
                          symbol='US30Cash',timeframe='M5',
                          source_artifact_hashes={'run_'+name:digest(block/name) for name in names})
            (block/'manifest.json').write_text(json.dumps(metadata))
            with patch('python.stream_bar_master.ROOT',root):
                result=build([block],root/'out',train,validation,split,chunksize=1)
            self.assertEqual(result['rows']['master'],4)
            self.assertEqual(result['execution_quotes'],4)
            cohort=read_parquet(root/'out/train.parquet')
            self.assertEqual(set(cohort.signal_id),{'train'})
            self.assertNotIn('execution_bid',cohort.columns)
            self.assertEqual(int(cohort.signal_time_msc.iloc[0]),epoch(2024))
            self.assertFalse(result['final_test_accessed'])
            with self.assertRaisesRegex(ValueError,'overwrite'):
                build([block],root/'out',train,validation,split,chunksize=1)
