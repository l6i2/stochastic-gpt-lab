from pathlib import Path
import sys
import unittest
import json
import hashlib
import tempfile
import importlib.util
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from nts_external import stamp,unstamp,extension,verify_response,offset_bounds


class OffsetTests(unittest.TestCase):
    def test_asymmetric_delay_bounds_without_midpoint_assumption(self):
        self.assertEqual(offset_bounds(0,102,110,20,2),[88,104])
        with self.assertRaises(ValueError):offset_bounds(0,102,110,1,0)
        with self.assertRaises(ValueError):offset_bounds(0,102,100,20,0)

    def test_history_tampering_is_rejected(self):
        spec=importlib.util.spec_from_file_location('nts_station',Path(__file__).resolve().parents[1]/'tools/authenticated_utc_station.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);payload={'previous':'0'*64,'test':1}
            digest=hashlib.sha256(module.raw.canonical(payload)).hexdigest();path=folder/('a'*32+'.json')
            path.write_text(json.dumps({'payload':payload,'sha256':digest}))
            self.assertEqual(module.verify_history(folder,{'chain_head':digest}),1)
            payload['test']=2;path.write_text(json.dumps({'payload':payload,'sha256':digest}))
            with self.assertRaises(ValueError):module.verify_history(folder,{'chain_head':digest})


class NtsAuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime=Path(__file__).resolve().parents[1]/'outputs/pc_a_prospective_utc/nts_dependencies/runtime'
        if not runtime.exists():raise unittest.SkipTest('Isolated pinned NTS dependencies not provisioned on this host')
        sys.path.insert(0,str(runtime))
        from cryptography.hazmat.primitives.ciphers.aead import AESSIV
        cls.AESSIV=AESSIV

    def packet(self):
        import struct
        key=bytes(range(32));uid=b'u'*32;origin=b'o'*8
        header=b'\x24\x01'+bytes(22)+origin+stamp(100000000000)+stamp(101000000000)
        aad=header+extension(0x104,uid);nonce=b'n'*16
        ciphertext=self.AESSIV(key).encrypt(b'',[aad,nonce])
        return aad+extension(0x404,struct.pack('!HH',16,len(ciphertext))+nonce+ciphertext),key,uid,origin

    def test_valid_reply_and_tampered_ciphertext(self):
        packet,key,uid,origin=self.packet()
        self.assertEqual(verify_response(packet,key,uid,origin),(100000000000,101000000000))
        bad=packet[:-1]+bytes([packet[-1]^1])
        with self.assertRaises(Exception):verify_response(bad,key,uid,origin)

    def test_uid_origin_unsynchronized_and_truncation_rejected(self):
        packet,key,uid,origin=self.packet()
        for p,u,o in ((packet,b'x'*32,origin),(packet,uid,b'x'*8),(b'\xe4'+packet[1:],uid,origin),(packet[:-3],uid,origin)):
            with self.assertRaises(ValueError):verify_response(p,key,u,o)

    def test_authenticated_header_cannot_be_changed(self):
        packet,key,uid,origin=self.packet();bad=bytearray(packet);bad[40]^=1
        with self.assertRaises(Exception):verify_response(bytes(bad),key,uid,origin)

    def test_rfc5297_deterministic_vector(self):
        key=bytes.fromhex('fffefdfcfbfaf9f8f7f6f5f4f3f2f1f0f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff')
        ad=bytes.fromhex('101112131415161718191a1b1c1d1e1f2021222324252627')
        result=self.AESSIV(key).encrypt(bytes.fromhex('112233445566778899aabbccddee'),[ad])
        self.assertEqual(result.hex(),'85632d07c6e8f37f950acd320a2ecc9340c02b9690c4dc04daef7f6afe5c')
