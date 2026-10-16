import unittest

from python.censored_membership_contract import candidates


class CensoredMembershipTests(unittest.TestCase):
    def fixture(self):
        common=dict(follow_exit_reason='END_OF_DATA',invert_exit_reason='END_OF_DATA',
                    follow_exit_time=11000,invert_exit_time=11000,
                    follow_bars_in_trade=4,invert_bars_in_trade=4)
        return [dict(common,signal_id='known',signal_time_msc=100,entry_time_msc=101),
                dict(common,signal_id='unassigned',signal_time_msc=10001,entry_time_msc=10002)]

    def test_only_end_censored_nonmembers_can_be_quarantined(self):
        rows=self.fixture()
        ids,coverage=candidates(rows,{'known':100},0,10000,100000000,7)
        self.assertEqual(coverage,1)
        self.assertEqual([r['signal_id'] for r in ids],['unassigned'])
        self.assertIn('UNRESOLVED',ids[0]['reason'])
        rows[1]['follow_exit_reason']='SL'
        with self.assertRaisesRegex(ValueError,'wholly censored'):
            candidates(rows,{'known':100},0,10000,100000000,7)

    def test_quarantine_cannot_hide_missing_frozen_observations(self):
        with self.assertRaisesRegex(ValueError,'observations are missing'):
            candidates(self.fixture(),{'known':100,'missing':200},0,10000,100000000,7)
        with self.assertRaisesRegex(ValueError,'exceeds'):
            candidates(self.fixture(),{'known':100},0,10000,100000000,0)
