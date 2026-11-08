import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock,patch
from controller.bc_study import initial,native_floor,check_request,assessment,advance,evaluation_guard
from controller.prospective_processor import Ledger
from tools import bc_study_station as station


def rows(start):
    ticks=[dict(time=(start+i*60000)//1000,time_msc=start+i*60000,bid=10.,ask=11.,flags=2) for i in range(5)]
    m1=[dict(time=t['time'],open=10.,high=10.,low=10.,close=10.,tick_volume=1) for t in ticks]
    return dict(ticks=ticks,m1=m1,m5=[dict(time=start//1000,open=10.,high=10.,low=10.,close=10.,tick_volume=5)])


class BCStudyTests(unittest.TestCase):
    def test_stale_quote_cannot_create_native_cut(self):
        for new in (300000,299999):self.assertIsNone(native_floor(dict(time_msc=300000),dict(time_msc=new)))
        self.assertEqual(native_floor(dict(time_msc=300000),dict(time_msc=600000)),900000)

    def test_pre_cut_partial_and_forming_ranges_reject(self):
        for start,end,floor,latest in [(0,300000,300000,600000),(300001,600001,300000,900000),(300000,600000,300000,599999),(300000,700000,300000,900000)]:
            with self.assertRaises(PermissionError):check_request(start,end,floor,latest)
        check_request(300000,600000,300000,600000)

    def test_native_parity_never_implies_live_receipt_or_admission(self):
        r=assessment(rows(300000),300000,600000)
        self.assertTrue(r['native_archive_parity']);self.assertFalse(r['live_receipt_proven']);self.assertFalse(r['scientific_admission'])
        missing=rows(300000);missing['ticks'].pop()
        self.assertFalse(assessment(missing,300000,600000)['native_archive_parity'])

    def test_bid_ask_and_volume_discrepancies_quarantine(self):
        for field in ('ask','flags'):
            data=rows(300000);data['ticks'][0][field]=0
            self.assertFalse(assessment(data,300000,600000)['native_archive_parity'])

    def test_350_context_bars_and_future_mutation(self):
        state=initial();prefix=[]
        for i in range(351):
            bar=dict(time=i*300,open=10.,high=12.+i%3,low=9.,close=11.,tick_volume=5)
            state,artifact=advance(state,bar,str(i));prefix.append(artifact)
        self.assertTrue(all(a['role']=='TRAIN_CONTEXT' for a in prefix[:350]))
        self.assertEqual(prefix[350]['role'],'TRAIN_DEV')
        self.assertEqual(prefix[275]['values']['ha_direction'],1)
        before=copy.deepcopy(prefix)
        advance(state,dict(time=351*300,open=10.,high=1e8,low=9.,close=11.,tick_volume=5),'future')
        self.assertEqual(prefix,before)
        self.assertTrue(all(x['feature_max_native_msc']<x['earliest_decision_native_msc'] for x in prefix))

    def test_gap_segments_without_losing_accumulated_total(self):
        state=initial()
        for stamp in (0,300,900):state,artifact=advance(state,dict(time=stamp,open=10.,high=12.,low=9.,close=11.,tick_volume=5),str(stamp))
        self.assertEqual(state['total_m5'],3);self.assertEqual(state['run_bars'],1)
        self.assertTrue(artifact['calendar_boundary_unverified'])
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):advance(state,artifact['native_bar'],'repeat')

    def test_eval_requires_later_specific_authority_and_same_clock_domain(self):
        with self.assertRaises(PermissionError):evaluation_guard(None,1,2,dict(boot_id='1',monotonic_ns=4))
        freeze=dict(model_hashes={'BUY':'x','SELL':'y'},authorized_evaluation_receipt='test-only',boot_id='1',monotonic_ns=3)
        with self.assertRaises(PermissionError):evaluation_guard(freeze,1,2,dict(boot_id='2',monotonic_ns=4))
        self.assertIn('NOT_ADMISSION',evaluation_guard(freeze,1,2,dict(boot_id='1',monotonic_ns=4)))

    def test_worker_synthetic_restart_idempotence_and_no_stale_download(self):
        with TemporaryDirectory() as directory:
            base=Path(directory)/'outputs';base.mkdir();package=Path(directory)/'package';package.mkdir();(package/'activation.json').write_text('{}')
            manifest=dict(cut_anchor=dict(quote=dict(time_msc=300000)),dataset_id='SYNTHETIC_ONLY',producer_id='SYNTHETIC_ONLY',epoch='SYNTHETIC_ONLY')
            quote=dict(time_msc=300000);identity=lambda _:dict(quote=dict(quote))
            def fetch(_,kind,start,end):return rows(start)[kind],dict(origin='SYNTHETIC_FIXTURE')
            with patch.object(station,'BASE',base),patch.object(station,'PACKAGE',package),patch.object(station,'load_manifest',return_value=manifest),patch.object(station,'NativeReference',return_value=Mock()),patch.object(station,'identity',side_effect=identity),patch.object(station,'fetch',side_effect=fetch) as reader:
                first=station.run();reader.assert_not_called();self.assertIsNone(first['native_floor'])
                quote['time_msc']=600001;cut=station.run();self.assertEqual(cut['native_floor'],900000)
                quote['time_msc']=1500000;one=station.run(budget=1);self.assertEqual(one['M5_verified'],1)
                first_path=next((base/'raw').rglob('manifest.json'));first_raw=first_path.read_bytes()
                two=station.run(budget=1);self.assertEqual(two['M5_verified'],2);self.assertEqual(two['M5_current_consecutive'],2)
                repeated=station.run();self.assertEqual(repeated['M5_verified'],2);self.assertEqual(repeated['processed_this_run'],0)
                self.assertEqual(reader.call_count,6);self.assertEqual(first_path.read_bytes(),first_raw)
            ledger=Ledger(base/'ledger.sqlite3')
            try:self.assertEqual(ledger.state['bc']['cursor'],1500000)
            finally:ledger.close()

    def test_historical_recovery_revises_without_overwriting_or_double_counting(self):
        with TemporaryDirectory() as directory:
            base=Path(directory)/'outputs';base.mkdir();package=Path(directory)/'package';package.mkdir();(package/'activation.json').write_text('{}')
            manifest=dict(cut_anchor=dict(quote=dict(time_msc=300000)),dataset_id='SYNTHETIC_ONLY',producer_id='SYNTHETIC_ONLY',epoch='SYNTHETIC_ONLY')
            quote=dict(time_msc=600001);phase=[False];elapsed=[1000]
            def clock():return dict(boot_id='SYNTHETIC_BOOT',monotonic_ns=elapsed[0]*1000000,uptime_ms=elapsed[0],host_utc_label='2026-11-08T00:00:00+00:00',utc_certified=False)
            def fetch(_,kind,start,end):
                data=rows(start)
                if not phase[0] and kind=='ticks':return [],dict(origin='SYNTHETIC_TEMPORARILY_UNAVAILABLE')
                return data[kind],dict(origin='SYNTHETIC_FIXTURE')
            with patch.object(station,'BASE',base),patch.object(station,'PACKAGE',package),patch.object(station,'load_manifest',return_value=manifest),patch.object(station,'NativeReference',return_value=Mock()),patch.object(station,'identity',side_effect=lambda _:dict(quote=dict(quote))),patch.object(station,'fetch',side_effect=fetch),patch.object(station,'host_clock',side_effect=clock):
                station.run();quote['time_msc']=1200000
                rejected=station.run();self.assertEqual(rejected['M5_rejected'],1)
                original=next((base/'raw').rglob('manifest.json'));content=original.read_bytes()
                phase[0]=True;elapsed[0]+=900001
                recovered=station.run();self.assertEqual(recovered['M5_verified'],1)
                self.assertEqual(original.read_bytes(),content)
                self.assertEqual(len(list((base/'raw').rglob('manifest.json'))),2)
                repeated=station.run();self.assertEqual(repeated['M5_verified'],1)
