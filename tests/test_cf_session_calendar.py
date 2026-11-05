import calendar
import copy
from datetime import datetime
import unittest
from controller.cf_session_calendar import IDENTITY,parse_probe,transition_review
from controller.pretrain_contracts import seal


def fixture():
    start=calendar.timegm(datetime(2026,11,6).timetuple())*1000;end=start+3600000
    records=['XM_SESSION_PROBE|START|symbol=US30Cash|symbol_selected=YES|server=XMGlobalSC-MT5 5']
    for day in ('MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY'):
        records += [f'XM_SESSION_PROBE|QUOTE|day={day}|index=0|from=01:00|to=00:00',
                    f'XM_SESSION_PROBE|TRADE|day={day}|index=0|from=01:05|to=23:55']
    records+=['XM_SESSION_PROBE|END']
    exception=dict(**IDENTITY,from_native_msc=start,to_native_msc=end,
        schedule_effect='NORMAL_QUOTE_CLOSURE_CONFIRMED',source_kind='BROKER_DATED_NOTICE',
        source_url_or_artifact='synthetic_fixture_not_real_attestation',source_sha256='synthetic')
    window=dict(source_pin_sha256='synthetic_source',identity=IDENTITY,first_n=0,
                previous_hash='synthetic_prior_checkpoint',sleep_record_id=42,records=[])
    head=window['previous_hash']
    for n in range(362):
        payload=dict(kind='LIVE_LATEST_STATE_POLL',connected=True,sleep_record_id=42,
            read_end=dict(boot_id='synthetic',monotonic_ns=n*10000000000,uptime_ms=n*10000),
            native_quote=dict(time_msc=start-1 if n<361 else end))
        digest=seal(dict(previous=head,payload=payload))
        window['records'].append(dict(n=n,previous=head,digest=digest,payload=payload));head=digest
    window.update(expected_head=head,last_n=361)
    return dict(from_native_msc=start,to_native_msc=end,last_native_msc=start-1,current_native_msc=end,
        boundary_reason='NATIVE_MINUTE_GAP_SESSION_CAUSE_UNKNOWN',next_m5_open_msc=start,
        calendars=[dict(records=records,records_sha256=seal(records),observed_native_msc=stamp) for stamp in (start-1,end)],
        exception_receipt=exception,expected_exception_receipt_sha256=seal(exception),
        ledger_window=window,expected_source_pin_sha256='synthetic_source')


def reseal_window(request):
    window=request['ledger_window'];head=window['previous_hash']
    for row in window['records']:
        row['previous']=head;row['digest']=seal(dict(previous=head,payload=row['payload']));head=row['digest']
    window['expected_head']=head


class SessionCalendarTests(unittest.TestCase):
    def test_native_quote_and_trade_sessions_remain_separate(self):
        parsed=parse_probe(fixture()['calendars'][0]['records'])
        self.assertEqual(parsed['sessions']['QUOTE']['FRIDAY'],[[60,1440]])
        self.assertEqual(parsed['sessions']['TRADE']['FRIDAY'],[[65,1435]])
        self.assertEqual(parsed['sessions']['QUOTE']['SUNDAY'],[])

    def test_incomplete_or_duplicate_probe_rejected(self):
        rows=fixture()['calendars'][0]['records']
        for bad in (rows[:-1],rows[:2]+[rows[1]]+rows[2:]):
            with self.assertRaises(ValueError):parse_probe(bad)

    def test_complete_synthetic_transition_without_admission(self):
        result=transition_review(fixture())
        self.assertTrue(result['bridge_allowed'],result['reasons'])
        self.assertFalse(result['dataset_admitted'])
        self.assertFalse(result['generation_utc_certified'])

    def test_future_receipt_never_advances_current_cursor(self):
        request=fixture();request['current_native_msc']=request['to_native_msc']-1
        result=transition_review(request)
        self.assertFalse(result['bridge_allowed'])
        self.assertIn('GAP_NOT_CURRENT_OR_REOPEN_NOT_OBSERVED',result['reasons'])

    def test_missing_applicable_exception_blocks_even_exact_weekly_schedule(self):
        request=fixture();request['exception_receipt']={}
        result=transition_review(request)
        self.assertFalse(result['bridge_allowed'])
        self.assertIn('EXACT_APPLICABLE_EXCEPTION_ATTESTATION_MISSING',result['reasons'])

    def test_changed_calendar_hash_rejected(self):
        request=fixture();request['calendars'][0]['records_sha256']='changed'
        self.assertIn('CALENDAR_HASH_MISMATCH',transition_review(request)['reasons'])

    def test_quote_open_cannot_be_bridged_as_trade_closure(self):
        request=fixture();request['to_native_msc']+=300000
        result=transition_review(request)
        self.assertIn('QUOTE_SESSION_OPEN_INSIDE_CLAIMED_CLOSURE',result['reasons'])

    def test_missing_ledger_record_breaks_chain(self):
        request=fixture();del request['ledger_window']['records'][20]
        self.assertIn('MONITOR_CHAIN_GAP_OR_CHANGED',transition_review(request)['reasons'])

    def test_disconnection_sleep_and_boot_changes_not_accepted(self):
        for key,value,reason in [('connected',False,'DISCONNECTED_OR_UNVERIFIED_POLL'),('sleep_record_id',43,'SLEEP_EVIDENCE_MISSING_OR_CHANGED')]:
            request=fixture();request['ledger_window']['records'][20]['payload'][key]=value;reseal_window(request)
            self.assertIn(reason,transition_review(request)['reasons'])
        request=fixture();request['ledger_window']['records'][20]['payload']['read_end']['boot_id']='other';reseal_window(request)
        self.assertIn('MONITOR_BOOT_GAP_OR_CLOCK_DISCONTINUITY',transition_review(request)['reasons'])

    def test_interruption_or_epoch_inside_closed_interval_rejected(self):
        for kind in ('OBSERVATION_INTERRUPTION','NEW_OBSERVATION_EPOCH'):
            request=fixture();request['ledger_window']['records'][20]['payload']['kind']=kind;reseal_window(request)
            self.assertIn('EPOCH_OR_INTERRUPTION_INSIDE_TRANSITION',transition_review(request)['reasons'])

    def test_wrong_boundary_and_cursor_fail_closed(self):
        request=fixture();request.update(boundary_reason='WINDOWS_BOOT_CHANGED',next_m5_open_msc=request['to_native_msc'])
        result=transition_review(request)
        self.assertIn('NOT_A_SESSION_GAP_BOUNDARY',result['reasons'])
        self.assertIn('CURSOR_NOT_AT_THIS_CLOSED_INTERVAL',result['reasons'])

    def test_old_weekly_metadata_is_not_current_before_session(self):
        request=fixture();request['calendars'][0]['observed_native_msc']-=7*86400000
        self.assertIn('CALENDAR_VINTAGE_NOT_IN_ADJACENT_QUOTE_SESSIONS',transition_review(request)['reasons'])

    def test_malformed_monitor_record_is_quarantined(self):
        request=fixture();del request['ledger_window']['records'][20]['payload']['read_end'];reseal_window(request)
        self.assertEqual(transition_review(request)['status'],'QUARANTINED')


if __name__=='__main__':unittest.main()
