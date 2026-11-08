"""Replay synthetic native exports only. No terminal, protected data or fit."""
import csv
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from tools.cf_own_indicator_oracle import build_source, native_seed_diagnostic


def replay():
    receipt = json.loads((HERE/'synthetic_receipt.json').read_bytes())
    export = HERE/'cfweek_382ad54e_oracle.csv'
    assert hashlib.sha256(export.read_bytes()).hexdigest() == receipt['export_sha256']
    with export.open(encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    bars = [dict(time=946857600+i*300,open=1000.+i%13,high=1030.+i%17,
                 low=980.-i%11,close=1005.+i%19,tick_volume=5) for i in range(300)]
    minutes = [dict(bar,time=bar['time']+j*60,tick_volume=1) for bar in bars for j in range(5)]
    source = ('// SYNTHETIC WEEKEND DIAGNOSTIC. NOT PROSPECTIVE DATA.\n'
              + build_source(dict(native_m5=bars,native_m1=minutes),receipt['recipe']['run']))
    # Path.write_text used the Windows newline convention for the compiled file.
    assert hashlib.sha256(source.replace('\n','\r\n').encode()).hexdigest() == receipt['source_sha256']
    assert len(rows) == len(bars) == 300
    previous = None
    ready = 0
    for i,(bar,row) in enumerate(zip(bars,rows)):
        assert int(row['time']) == bar['time']
        assert all(float(row[key]) == bar[key] for key in ('open','high','low','close'))
        close = (bar['open']+bar['high']+bar['low']+bar['close'])/4
        opening = (bar['open']+bar['close'])/2 if previous is None else sum(previous)/2
        expected = dict(ha_open=opening,ha_close=close,
                        ha_high=max(bar['high'],opening,close),ha_low=min(bar['low'],opening,close))
        assert all(float(row[key]) == value for key,value in expected.items())
        assert bool(int(row['ha_ready'])) == (i+1 >= 276)
        if i+1 >= 276:
            assert int(row['ha_direction']) == (1 if close>opening else -1 if close<opening else 0)
            ready += 1
        previous = (opening,close)
    candidate = native_seed_diagnostic(bars,rows)
    assert candidate == receipt['candidate_atr']
    assert candidate['compared'] == 287 and not candidate['mismatches']
    return dict(synthetic=True,ha_ohlc_exact=300,ha_ready_directions_exact=ready,
                atr_candidate_exact=287,scientific_fits=0,dataset_admitted=False)


if __name__ == '__main__':
    print(json.dumps(replay(),sort_keys=True))
