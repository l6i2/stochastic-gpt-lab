import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from tools.autonomous_research_status import review_state,main,code_head

class AutonomousStatusTests(unittest.TestCase):
    def test_head_without_git_on_scheduler_path(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);g=root/'.git';g.mkdir();(g/'HEAD').write_text('a'*40)
            self.assertEqual(code_head(root),'a'*40)
            (g/'HEAD').write_text('ref: refs/heads/research/full-pipeline')
            (g/'packed-refs').write_text('b'*40+' refs/heads/research/full-pipeline\n')
            self.assertEqual(code_head(root),'b'*40)
    def test_four_states_preserve_fail_closed_authority(self):
        self.assertEqual(review_state({},[]),'WAITING_FOR_DATA')
        self.assertEqual(review_state({'authorization_request_ready':True},[]),'WAITING_FOR_DATA')
        self.assertEqual(review_state({'authorization_request_ready':True,'package_complete':True},[]),'WAITING_FOR_AUTHORIZATION')
        self.assertEqual(review_state({'execution_permitted':True},[]),'WAITING_FOR_DATA')
        self.assertEqual(review_state({'execution_permitted':True,'package_complete':True},[]),'PASS')
        self.assertEqual(review_state({'execution_permitted':True,'package_complete':True},['STALE']),'FAIL')
        self.assertEqual(review_state({'reasons':['REAL_OR_UNKNOWN_ACCOUNT_HARD_FAIL']},[]),'FAIL')

    def test_corrupt_evidence_overwrites_stale_pass_without_dispatch(self):
        with patch('tools.autonomous_research_status.build',side_effect=ValueError('CHAIN_CHANGED')),patch('tools.autonomous_research_status.atomic') as output,patch('builtins.print'):
            self.assertEqual(main(),1)
            value=output.call_args.args[1]
            self.assertEqual(value['TRAINING_ADMISSION_GATE'],'FAIL')
            self.assertFalse(value['TRAINING_EXECUTED'])
            self.assertFalse(value['LIVE_TRADING'])

if __name__=='__main__':unittest.main()
