from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from simultaneous_clock_capture import bracket, native_frames
from simultaneous_clock_audit import audit_overlap
from finalize_clock_capture import finalize
import csv
import json
import hashlib
import tempfile


def native(frame=0):
    return [dict(frame=str(frame), symbol=s, mono_start_ms=str(frame*1000+10), mono_end_ms=str(frame*1000+20),
                 tester='0', connected='1', tick_ok='1', tick_time='1', tick_time_msc='1000',
                 time_trade_server='7200', time_gmt='0') for s in ('US30Cash','EURUSD','USDCHF')]


def windows(start, end):
    return dict(start_tick_ms=start,end_tick_ms=end,qpc_start_ns=start*1000000,
                qpc_end_ns=end*1000000,precise_utc_ns=1000000000)


class SimultaneousCaptureTests(unittest.TestCase):
    def test_requires_windows_observations_before_and_after_native(self):
        before,after=windows(0,9),windows(21,30)
        self.assertIsNone(bracket(native(),[after]))
        self.assertIsNone(bracket(native(),[before]))
        pair=bracket(native(),[before,after])
        self.assertEqual(pair['bracket_width_ms'],30)
        self.assertEqual(pair['windows_before'],before)

    def test_coarse_tick_equality_cannot_prove_bracketing(self):
        group=native()
        for row in group:
            row['mono_start_ms']='10';row['mono_end_ms']='10'
        same=windows(10,10)
        self.assertIsNone(bracket(group,[same]))
        pair=bracket(group,[windows(0,9),same,windows(11,12)])
        self.assertNotEqual(pair['windows_before'],pair['windows_after'])
        self.assertEqual(pair['windows_before']['end_tick_ms'],9)
        self.assertEqual(pair['windows_after']['start_tick_ms'],11)

    def test_uses_monotonic_bounds_not_wall_clock_order(self):
        a,b=windows(0,9),windows(21,30)
        a['precise_utc_ns']=9999999999999999999
        self.assertIsNotNone(bracket(native(),[a,b]))

    def test_csv_parser_ignores_partial_and_duplicate_frame(self):
        header='frame,symbol\n'
        body=header+'0,US30Cash\n0,EURUSD\n0,USDCHF\n'
        self.assertEqual(len(native_frames(body)),1)
        self.assertEqual(native_frames(body+'0,USDCHF\n'),[])
        self.assertEqual(native_frames(body[:-1]),[])

    def capture(self):
        pairs=[bracket(native(i),[windows(i*1000,i*1000+9),windows(i*1000+21,i*1000+30)]) for i in range(50)]
        status={name:{'returncode':1} for name in ('source','status','offset')}
        return dict(paired_frames=pairs,references=[],w32_before=status,w32_after=status)

    def test_complete_overlap_does_not_certify_bad_clock_or_mapping(self):
        result=audit_overlap(self.capture(),end_marker_present=True)
        self.assertEqual(result['simultaneous_overlap'],'PASS')
        self.assertEqual(result['windows_clock_sync'],'FAIL')
        self.assertEqual(result['native_to_utc_mapping'],'FAIL')
        self.assertEqual(result['future_tolerance_ms'],0)

    def test_missing_marker_malformed_pair_and_future_units_fail_closed(self):
        base=self.capture()
        self.assertEqual(audit_overlap(base,end_marker_present=False)['simultaneous_overlap'],'FAIL')
        bad=deepcopy(base);bad['paired_frames'][0]['windows_before']['end_tick_ms']=11
        self.assertIn('WINDOWS_NATIVE_BRACKET_INVALID',audit_overlap(bad,end_marker_present=True)['errors'])
        bad=deepcopy(base);bad['paired_frames'][0]['native'][0]['tick_time_msc']='2000'
        self.assertIn('SECONDS_MILLISECONDS_MISMATCH',audit_overlap(bad,end_marker_present=True)['errors'])

    def test_auditor_rejects_equal_coarse_boundaries_independently(self):
        for side,field,value in [('windows_before','end_tick_ms',10),
                                  ('windows_after','start_tick_ms',20)]:
            capture=self.capture()
            capture['paired_frames'][0][side][field]=value
            self.assertIn('WINDOWS_NATIVE_BRACKET_INVALID',
                          audit_overlap(capture,end_marker_present=True)['errors'])

    def test_finalizer_preserves_raw_hash_and_does_not_unlock_failed_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);capture=self.capture()
            (folder/'capture.json').write_text(json.dumps(capture))
            script=folder/'probe.mq5';script.write_bytes(b'synthetic source')
            script.with_suffix('.ex5').write_bytes(b'synthetic executable')
            build={'source_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),
                   'ex5_sha256':hashlib.sha256(script.with_suffix('.ex5').read_bytes()).hexdigest()}
            raw=folder/'raw.csv'
            rows=[r for p in capture['paired_frames'] for r in p['native']]
            with raw.open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            markers=folder/'original_markers.txt';markers.write_text('CLOCK_ATTESTATION_BEGIN\nCLOCK_ATTESTATION_END\n')
            digest=hashlib.sha256(raw.read_bytes()).hexdigest()
            result=finalize(folder,raw,markers,script,build)
            self.assertEqual(hashlib.sha256((folder/'native.csv').read_bytes()).hexdigest(),digest)
            self.assertEqual(result['simultaneous_overlap'],'PASS')
            self.assertEqual(result['causal_audit'],'FAIL')
            self.assertEqual(result['demo'],'DISABLED')
            with self.assertRaises(FileExistsError):finalize(folder,raw,markers,script,build)

    def test_finalizer_rejects_changed_executable_before_accepting_data(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);script=folder/'probe.mq5';script.write_bytes(b'changed')
            script.with_suffix('.ex5').write_bytes(b'changed executable')
            with self.assertRaisesRegex(ValueError,'EXECUTABLE_CHANGED'):
                finalize(folder,folder/'missing.csv',folder/'missing.txt',script,
                         {'source_sha256':'a'*64,'ex5_sha256':'b'*64})


if __name__=='__main__':unittest.main()
