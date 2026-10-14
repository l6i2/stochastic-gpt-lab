import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from python.validate_bar_path import QUOTE_DTYPE, baseline, open_quotes, validate


class BarPathTests(unittest.TestCase):
    def test_binary_records_and_frozen_barrier_time_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'quotes.bin'
            quotes=np.array([(i+1,1000.,1002.,i) for i in range(101)],dtype=QUOTE_DTYPE)
            quotes.tofile(path)
            tape=open_quotes(path,10000)
            self.assertEqual(baseline(tape,0,100,1)['reason'],'TIME_EXIT')
            del tape
            quotes[-1]['bid']=700;quotes[-1]['ask']=702;quotes.tofile(path)
            tape=open_quotes(path,10000)
            outcome=baseline(tape,0,100,1)
            self.assertEqual((outcome['reason'],outcome['pnl']),('SL',-302))
            del tape
            with self.assertRaisesRegex(ValueError,'protected'):
                open_quotes(path,100)

    def test_full_event_and_arrival_parity_with_gap_tp_and_sl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path=root/'quotes.bin'
            np.array([(1,1000.,1002.,0),(300001,1400.,1402.,1)],dtype=QUOTE_DTYPE).tofile(path)
            event=dict(signal_id='sig',signal_time_msc=0,entry_time_msc=1,
                       follow_side='BUY',invert_side='SELL',follow_entry_price=1002,invert_entry_price=1000,
                       follow_exit_price=1242,invert_exit_price=1402,follow_exit_time=300001,invert_exit_time=300001,
                       follow_exit_reason='TP',invert_exit_reason='SL',follow_PnL=240,invert_PnL=-402,
                       follow_MFE=240,invert_MFE=0,follow_MAE=2,invert_MAE=402,
                       follow_bars_in_trade=1,invert_bars_in_trade=1)
            def table(name, rows):
                with (root/name).open('w',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            table('events.csv',[event])
            trades=[];arrivals=[]
            for mode, side, entry, price, reason in (('FOLLOW','BUY',1002,1242,'TP'),('INVERT','SELL',1000,1402,'SL')):
                trades.append(dict(signal_id='sig',virtual_mode=mode,virtual_side=side,
                    entry_quote_index=0,exit_quote_index=1,entry_time_msc=1,exit_time_msc=300001,
                    entry_price=entry,exit_price=price,exit_reason=reason,bars_in_trade=1))
                arrivals.append(dict(snapshot_id='sig_'+mode+'_1',signal_id='sig',virtual_mode=mode,
                    snapshot_bar=1,decision_cutoff_msc=300000,execution_time_msc=300001,
                    execution_bid=1400,execution_ask=1402,decision_quote_index=1))
            table('trades.csv',trades);table('arrivals.csv',arrivals)
            result=validate(path,root/'trades.csv',root/'events.csv',root/'arrivals.csv',1000000)
            self.assertEqual(result['BASELINE_REPLAY'],'PASS')
            self.assertEqual(result['indexed_trades'],2)
            arrivals[0]['decision_quote_index']=0;table('arrivals.csv',arrivals)
            with self.assertRaisesRegex(ValueError,'arrival quote'):
                validate(path,root/'trades.csv',root/'events.csv',root/'arrivals.csv',1000000)

    def test_partial_record_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'partial.bin';path.write_bytes(b'incomplete')
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                open_quotes(path,1000)
