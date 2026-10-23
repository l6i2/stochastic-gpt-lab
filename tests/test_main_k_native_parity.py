from pathlib import Path
import sys,tempfile,unittest,csv,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from main_k_native_parity import fixtures,build_harness,validate_native_result,CASES
from causal_metadata_audit import main_values


class MainKNativeHarnessTests(unittest.TestCase):
    def test_fixture_families_are_valid_reproducible_and_include_threshold_plateaus(self):
        data=fixtures();self.assertEqual(set(data),set(CASES));self.assertEqual(data,fixtures())
        for name,rows in data.items():
            for i,row in enumerate(rows):
                self.assertLessEqual(row['low'],row['open']);self.assertLessEqual(row['open'],row['high'])
                self.assertLessEqual(row['low'],row['close']);self.assertLessEqual(row['close'],row['high'])
                self.assertEqual(row['bar_time'],rows[0]['bar_time']+i*300)
        self.assertTrue(any(r['close']==102 for r in data['equality']))
        self.assertTrue(any(r['close']==108 for r in data['equality']))

    def test_build_extracts_actual_production_shift_and_parameters_and_refuses_fake_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);manifest=build_harness(folder,'pk_12345678')
            source=(folder/'MQL5/Scripts/ResearchDiagnostics/pk_12345678/MainKNativeParity.mq5').read_text(encoding='utf-8-sig')
            self.assertIn('CopyBuffer(handle,buffer,1,n,a)',source)
            self.assertIn('iStochastic(sym,PERIOD_M5,K_PERIOD,D_PERIOD,SLOWING,MODE_SMA,STO_LOWHIGH)',source)
            self.assertIn('IndicatorCreate(symbol,PERIOD_M5,IND_STOCHASTIC,5,p)',source)
            for forbidden in ('OrderSend(', 'CTrade', 'PositionOpen('):self.assertNotIn(forbidden,source)
            self.assertFalse(manifest['production_modified'])
            with self.assertRaisesRegex(ValueError,'NOT_EVIDENCED'):validate_native_result(folder,'pk_12345678')
            with self.assertRaises(FileExistsError):build_harness(folder,'pk_12345678')

    def test_validator_rejects_matching_but_wrong_shared_formula(self):
        # All exports in this test are fabricated test fixtures, never evidence of native execution.
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);run='pk_87654321';build_harness(folder,run)
            root=folder/'MQL5/Files'
            (root/(run+'_result.json')).write_text(json.dumps({'run_id':run,'native_execution':True,'passed':True,'terminal_build':0}))
            output=root/(run+'_native.csv')
            fields=['fixture','bar_index','bar_time','production_main','native_main','production_d','native_d','production_signal','native_signal','readiness']
            rows=[]
            for name,bars in fixtures().items():
                k=main_values(bars,native_reference=True)
                for i,bar in enumerate(bars[:-1]):
                    value=k[i] if k[i] is not None else 0
                    rows.append(dict(zip(fields,[name,i,bar['bar_time'],value,value,0,0,0,0,'WARMUP' if i<6 else 'READY'])))
            def write():
                with output.open('w',newline='') as stream:
                    w=csv.DictWriter(stream,fieldnames=fields);w.writeheader();w.writerows(rows)
            write();self.assertEqual(validate_native_result(folder,run)['status'],'PASS')
            row=next(r for r in rows if r['readiness']=='READY')
            row['production_main']+=1;row['native_main']+=1
            write()
            with self.assertRaisesRegex(ValueError,'REFERENCE_MISMATCH'):validate_native_result(folder,run)
