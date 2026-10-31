import copy
import json
from pathlib import Path
import tempfile
import unittest
from controller.restart_readiness import prefix,receipt,verify_previous,transition


class RestartTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name);self.seg=self.folder/'segments'/'a';self.seg.mkdir(parents=True)
        self.source=self.folder/'native';self.source.write_bytes(b'original\n')
        self.write(self.folder/'collection_manifest.json',{'id':'independent'})
        self.write(self.folder/'runtime_state.json',{'segments':['a'],'active_segment':'a'})
        self.write(self.folder/'collector_status.json',{'capture_id':'id','last_callback_age_ms':100})
        self.write(self.seg/'manifest.json',{'source_path':str(self.source)})
        self.write(self.seg/'checkpoint.json',{'rows':1,'chain_head':'hash','source_offset':9,'source_sequence':10})
        (self.seg/'journal.jsonl').write_bytes(b'{"sha256":"hash"}\n')
        self.old=receipt(self.folder,{'boot_id':'1'})

    def write(self,path,data):path.write_text(json.dumps(data),encoding='utf8')

    def test_saved_prefix_survives_append_and_checkpoint_progress(self):
        with self.source.open('ab') as s:s.write(b'new\n')
        with (self.seg/'journal.jsonl').open('ab') as s:s.write(b'{"sha256":"new"}\n')
        self.assertTrue(verify_previous(self.folder,self.old))

    def test_truncated_or_modified_native_fails(self):
        self.source.write_bytes(b'x')
        with self.assertRaisesRegex(ValueError,'TRUNCATED'):verify_previous(self.folder,self.old)
        self.source.write_bytes(b'changed!\n')
        with self.assertRaisesRegex(ValueError,'NATIVE_PREFIX_CHANGED'):verify_previous(self.folder,self.old)

    def test_changed_journal_fails(self):
        (self.seg/'journal.jsonl').write_bytes(b'{"sha256":"fake"}\n')
        with self.assertRaisesRegex(ValueError,'JOURNAL_PREFIX_CHANGED'):verify_previous(self.folder,self.old)

    def test_same_boot_is_never_restart_proof(self):
        self.assertEqual(transition(self.old,self.old)['restart_recovery'],'WAITING_FOR_NATURAL_WINDOWS_RESTART')

    def test_boot_change_requires_fresh_distinct_segment(self):
        now=copy.deepcopy(self.old);now['clock']['boot_id']='2'
        self.assertIn('WAITING',transition(self.old,now)['restart_recovery'])
        now['active_segment']='b';now['recent_callback_age_ms']=20000
        self.assertIn('WAITING',transition(self.old,now)['restart_recovery'])
        now['recent_callback_age_ms']=1
        result=transition(self.old,now)
        self.assertEqual(result['restart_recovery'],'BOOT_CHANGE_AND_FRESH_NEW_SEGMENT_OBSERVED')
        self.assertFalse(result['physical_power_cycle_proven']);self.assertFalse(result['scientific_admission'])

    def test_identity_and_manifest_change_fail(self):
        now=copy.deepcopy(self.old);now['capture_id']='other'
        with self.assertRaisesRegex(ValueError,'CAPTURE_ID_CHANGED'):transition(self.old,now)
        self.write(self.folder/'collection_manifest.json',{'different':1})
        with self.assertRaisesRegex(ValueError,'CAPTURE_MANIFEST_CHANGED'):verify_previous(self.folder,self.old)

    def test_incomplete_checkpoint_prefix_rejected(self):
        (self.seg/'journal.jsonl').write_bytes(b'{"sha256":"hash"}')
        with self.assertRaisesRegex(ValueError,'INCOMPLETE'):receipt(self.folder,{'boot_id':'1'})


if __name__=='__main__':unittest.main()
