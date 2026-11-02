import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from controller.isolated_observation import Observation,eof_anchor,GENESIS
from test_isolated_observation import line,clock


class SegmentCutOrder(unittest.TestCase):
    def setup_sources(self,root):
        old=root/'old.jsonl';old.write_bytes(line(GENESIS,0,90)[0])
        prior=Observation.create(root/'segments',old,eof_anchor(old),clock(100),synthetic=True);prior.close()
        new=root/'new.jsonl';new.write_bytes(line(GENESIS,0,200)[0]);return prior,new

    def test_fresh_clock_sampled_after_new_eof_no_prefix_adoption(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t);prior,new=self.setup_sources(r);saved=(prior.folder/'manifest.json').read_bytes();order=[]
            def anchor(p):order.append('eof');return eof_anchor(p)
            def cut():order.append('clock');return clock(201)
            with patch('controller.isolated_observation.eof_anchor',side_effect=anchor):
                obj=Observation.new_segment(prior.folder,r/'segments',new,cut,synthetic=True)
            try:
                self.assertEqual(order,['eof','clock']);self.assertEqual(obj.state['source_records'],0)
                self.assertEqual(obj.manifest['actual_start_clock']['uptime_ms'],201)
                self.assertEqual((prior.folder/'manifest.json').read_bytes(),saved)
            finally:obj.close()

    def test_old_or_regressing_cut_still_rejected_without_tolerance(self):
        for supplied in (clock(100),lambda:clock(199)):
            with tempfile.TemporaryDirectory() as t:
                r=Path(t);prior,new=self.setup_sources(r)
                with self.assertRaisesRegex(ValueError,'CLOCK_EPOCH_UNCOMPARABLE'):
                    Observation.new_segment(prior.folder,r/'segments',new,supplied,synthetic=True)


if __name__=='__main__':unittest.main()
