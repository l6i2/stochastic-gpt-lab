import unittest
import json
import shutil
import tempfile
from pathlib import Path
from controller.six_routes import aggregate_m1
from controller.pretrain_contracts import seal
from controller.authorized_capture import sha
from tools.prepare_six_routes_study import verify, ROOT


class AggregationTests(unittest.TestCase):
    def rows(self):
        return [dict(time=i*60,open=100+i,high=102+i,low=99+i,close=101+i,tick_volume=i+1) for i in range(5)]

    def test_complete_bucket_uses_native_order_and_volume(self):
        result=aggregate_m1(self.rows())[0]
        self.assertTrue(result['complete_five_minutes'])
        self.assertEqual([result[k] for k in ('open','high','low','close','tick_volume')],[100,106,99,105,15])

    def test_missing_minute_stays_incomplete_without_fill(self):
        rows=self.rows();rows.pop(2)
        result=aggregate_m1(rows)[0]
        self.assertFalse(result['complete_five_minutes'])
        self.assertEqual(result['observed_minutes'],[0,60,180,240])
        self.assertEqual(result['tick_volume'],12)

    def test_duplicate_and_reordered_minutes_fail(self):
        for rows in ([self.rows()[0]]*2,list(reversed(self.rows()))):
            with self.assertRaisesRegex(ValueError,'ORDER_OR_DUPLICATE'):
                aggregate_m1(rows)

    def test_resealed_proposal_cannot_reduce_threshold_or_change_strategy(self):
        for key in ('minimums','strategy'):
            with tempfile.TemporaryDirectory() as directory:
                target=Path(directory)/'proposal'
                shutil.copytree(ROOT/'research/studies/six_alternatives_resolution/proposed_study',target)
                path=target/'study.json';study=json.loads(path.read_text())
                study[key]['own_m5' if key=='minimums' else 'TP']=1
                path.write_text(json.dumps(study))
                index=json.loads((target/'hashes.json').read_text());index['files']['study.json']=sha(path)
                index['root_sha256']=seal(index['files']);(target/'hashes.json').write_text(json.dumps(index))
                with self.assertRaises(ValueError):verify(target)


if __name__=='__main__':unittest.main()
