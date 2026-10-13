import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import pandas as pd
from fixtures import dataset, audit
from parquet_io import parquet_engine

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(importlib.util.find_spec('pyarrow') or importlib.util.find_spec('fastparquet'), 'No Parquet engine installed')
class ParquetTests(unittest.TestCase):
    def test_engine_respects_host_simd_capabilities(self):
        import numpy as np
        engine=parquet_engine()
        self.assertIn(engine,{'pyarrow','fastparquet'})
        features=np.core._multiarray_umath.__cpu_features__
        if not features.get('SSE42',False) and importlib.util.find_spec('fastparquet'):
            self.assertEqual(engine,'fastparquet')

    def test_roundtrip_and_walk_forward_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);csv=root/'synthetic.csv';parquet=root/'synthetic.parquet'
            d=dataset(120);d.loc[3,'follow_exit_reason']='END_OF_DATA';d.loc[3,['follow_PnL','directional_advantage']]=float('nan')
            d.to_csv(csv,index=False);Path(str(csv)+'.audit.json').write_text(json.dumps(audit(len(d))))
            subprocess.run([sys.executable,str(ROOT/'python/validate_dataset.py'),str(csv),'--parquet',str(parquet)],check=True,capture_output=True,text=True)
            from research import read_dataset
            pd.testing.assert_frame_equal(pd.read_csv(csv),read_dataset(parquet))
            subprocess.run([sys.executable,str(ROOT/'python/validate_dataset.py'),str(parquet)],check=True,capture_output=True,text=True)
            subprocess.run([sys.executable,str(ROOT/'python/analyze_dataset.py'),str(parquet),'--output',str(root/'wf'),'--walk-forward','--wf-initial','50','--wf-step','20'],check=True,capture_output=True,text=True)
            self.assertTrue(list((root/'wf').glob('walk_forward_*/metrics.csv')))
            self.assertFalse(list((root/'wf').glob('**/FINAL_TEST')))

if __name__=='__main__':unittest.main()
