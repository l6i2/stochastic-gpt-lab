import unittest
from controller.pretrain_contracts import seal,chain
from controller.scientific_blockers import iso_ns,adjudicate,power_pairs,known_membership,receipt_sampling,enrich_network


class ScientificBlockerTests(unittest.TestCase):
    def test_network_reason_is_context_not_verified_xm_route(self):
        incident=self.incident('DISCONNECTION_OBSERVED_START')
        event=self.event(8003,'1970-01-01T00:01:50Z',provider='Microsoft-Windows-WLAN-AutoConfig')
        event['fields']={'ReasonCode':'5'}
        r=enrich_network(adjudicate(incident,[]),incident,[event])
        self.assertEqual(r['classification'],'PROBABLE_CAUSE')
        self.assertFalse(r['admitted'])
        event['host_utc_label']='1970-01-01T00:02:10Z'
        self.assertEqual(enrich_network(adjudicate(incident,[]),incident,[event])['classification'],'UNKNOWN_CAUSE')

    def test_receipt_is_a_counter_bracket_not_callback_instant_or_event_utc(self):
        row=dict(sequence=1,callback_uptime_ms=10,read_uptime_ms=12,receipt_host_gmt_seconds=1)
        r=receipt_sampling(row,dict(boot_id='111',uptime_ms=245465),'111')
        self.assertEqual(r['host_label_read_counter_bracket_ms'],[12,245465])
        self.assertFalse(r['broker_generation_inferred'])
        self.assertFalse(r['host_label_utc_certified'])
        with self.assertRaises(ValueError):receipt_sampling(row,dict(boot_id='112',uptime_ms=13),'111')
        with self.assertRaises(ValueError):receipt_sampling(row,dict(boot_id='111',uptime_ms=11),'111')

    def incident(self,kind='CALLBACK_TIMER_GAP'):
        b=dict(session_id='s',sequence=1,callback_uptime_ms=1000,receipt_host_gmt_seconds=100,connected=True)
        a=dict(session_id='s',sequence=2,callback_uptime_ms=21000,receipt_host_gmt_seconds=120,connected=False)
        f=dict(kind=kind,before=b,after=a,elapsed_ms=20000,source_record_hash='x')
        return dict(fact=f,incident_id=seal(f),first_detected_host_clock={'boot_id':'111'})

    def event(self,number,timestamp,boot='111',provider='Microsoft-Windows-Kernel-Power',record=None):
        return dict(id=number,record_id=record or number,provider=provider,
            host_utc_label=timestamp,fields={'BootId':boot})

    def pair(self):
        return [self.event(506,'1970-01-01T00:01:45Z'),self.event(507,'1970-01-01T00:01:55Z')]

    def test_full_pair_same_boot_is_only_contributor_not_complete_coverage(self):
        r=adjudicate(self.incident(),self.pair())
        self.assertEqual(r['classification'],'VERIFIED_CAUSE')
        self.assertIsNone(r['missing_broker_event_count'])
        self.assertEqual(r['coverage'],'UNKNOWN_NO_BACKFILL')
        self.assertFalse(r['admitted'])

    def test_clock_step_demotes_alignment_to_probable(self):
        events=self.pair()+[self.event(1,'1970-01-01T00:01:50Z',provider='Microsoft-Windows-Kernel-General',record=509)]
        self.assertEqual(adjudicate(self.incident(),events)['classification'],'PROBABLE_CAUSE')

    def test_partial_pair_boot_mismatch_or_missing_cannot_verify(self):
        events=self.pair();events[0]['host_utc_label']='1970-01-01T00:01:39Z'
        self.assertEqual(adjudicate(self.incident(),events)['classification'],'PROBABLE_CAUSE')
        for boot in ('112',None):
            events=self.pair()
            for e in events:e['fields']['BootId']=boot
            self.assertEqual(adjudicate(self.incident(),events)['classification'],'PROBABLE_CAUSE')
        self.assertEqual(adjudicate(self.incident(),self.pair()[:1])['classification'],'UNKNOWN_CAUSE')

    def test_connection_state_and_no_ticks_do_not_establish_root_cause(self):
        for kind in ('DISCONNECTION_OBSERVED_START','RECONNECTION_OBSERVED'):
            self.assertEqual(adjudicate(self.incident(kind),self.pair())['classification'],'UNKNOWN_CAUSE')
        self.assertEqual(adjudicate(self.incident(),[])['classification'],'UNKNOWN_CAUSE')

    def test_counter_hash_and_sequence_guard(self):
        r=self.incident();r['fact']['elapsed_ms']=3
        with self.assertRaises(ValueError):adjudicate(r,[])
        r['incident_id']=seal(r['fact'])
        with self.assertRaises(ValueError):adjudicate(r,[])
        r=self.incident();r['fact']['after']['sequence']=4;r['incident_id']=seal(r['fact'])
        self.assertEqual(adjudicate(r,self.pair())['classification'],'UNKNOWN_CAUSE')

    def test_exact_100ns_clock_step_and_record_order(self):
        self.assertEqual(iso_ns('1970-01-01T00:00:01.0000001Z'),1000000100)
        for bad in ('1970-01-01T00:00:01','1970-01-01T00:00:01-05:00'):
            with self.assertRaises(ValueError):iso_ns(bad)
        events=list(reversed(self.pair()))
        self.assertEqual(len(power_pairs(events)),1)

    def test_membership_unknown_never_invented_from_date_range(self):
        entries=chain([dict(dataset_id='legacy',declared_native_date_range=['2024','2026'],
                            start_native_msc=None,end_native_exclusive_msc=None),
                       dict(dataset_id='diagnostic',start_native_msc=10,end_native_exclusive_msc=20)])
        r=known_membership(dict(entries=entries,chain_head=entries[-1]['entry_sha256']),[{'signal_id':'a'}],['b'])
        self.assertEqual(len(r['unknown_intervals']),1)
        self.assertEqual(len(r['verified_interval_metadata']),1)
        self.assertFalse(r['independent_dataset_certified'])
        self.assertEqual(r['protected_intersection'],'UNKNOWN_WITHOUT_ORIGINAL_COMPARABLE_MEMBERSHIP')
