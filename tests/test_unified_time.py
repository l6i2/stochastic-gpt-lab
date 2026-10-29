from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from time_semantics import (instant_display, event_display, chart_points,
    new_york_wall_to_utc, new_york_reference_session, new_york_dst_changes)
from native_time_mapping import NativeTimestamp, ClockMapping, MappingSegment, native_to_utc
from temporal_causality import utc_milliseconds


class UnifiedTimeTests(unittest.TestCase):
    def test_ecuador_and_ny_winter_summer(self):
        for month, expected in ((1, '07:00'), (7, '08:00')):
            view = instant_display(datetime(2026, month, 2, 12, tzinfo=timezone.utc), basis='HOST_RECEIPT_UNATTESTED')
            self.assertIn('07:00', view['Ecuador'])
            self.assertIn(expected, view['Nueva York'])
            self.assertIsNone(view['XM'])
            self.assertFalse(view['scientific_authorization'])

    def test_nominal_session_reference_not_broker_permission(self):
        for month, opening in ((1, '09:30'), (7, '08:30')):
            session = new_york_reference_session(date(2026, month, 5))
            self.assertIn(opening, session['start']['Ecuador'])
            self.assertFalse(session['execution_allowed'])
            self.assertEqual(session['holiday_and_early_close_status'], 'NOT_EVALUATED')

    def test_dst_exact_transitions_and_historical_rules(self):
        changes = new_york_dst_changes(2026)
        self.assertEqual([r['transition']['UTC'] for r in changes],
            ['2026-03-08T07:00:00.000+00:00', '2026-11-01T06:00:00.000+00:00'])
        self.assertTrue(new_york_dst_changes(2006)[0]['transition']['UTC'].startswith('2006-04-02'))

    def test_gap_fold_and_naive_input_rejected(self):
        with self.assertRaises(ValueError): new_york_wall_to_utc(datetime(2026, 3, 8, 2, 30))
        wall = datetime(2026, 11, 1, 1, 30)
        with self.assertRaises(ValueError): new_york_wall_to_utc(wall)
        self.assertEqual((new_york_wall_to_utc(wall, fold=1)-new_york_wall_to_utc(wall, fold=0)).total_seconds(),3600)
        with self.assertRaises(ValueError): instant_display(wall, basis='HOST_RECEIPT_UNATTESTED')

    def test_four_views_period_identity_raw_and_causal_hash_preserved(self):
        stamp=utc_milliseconds(datetime(2026, 1, 5, 12, tzinfo=timezone.utc))
        mapping=ClockMapping('SYNTHETIC_ONLY','TEST',('TEST',),
            (MappingSegment(stamp,stamp+10000,7200,10800),),True)
        raw=NativeTimestamp((stamp+7200000)//1000,stamp+7200000,'TEST','TEST','a'*64)
        original=native_to_utc(raw,mapping)
        view=event_display(raw,mapping)
        self.assertEqual(view['utc_msc'],stamp)
        self.assertIn('15:00',view['XM'])
        self.assertEqual(view['xm_server_offset_seconds'],10800)
        self.assertEqual(view['original_xm']['time_msc'],raw.time_msc)
        self.assertEqual(original.views['utc_event_sha256'],native_to_utc(raw,mapping).views['utc_event_sha256'])
        self.assertEqual(event_display(raw,replace(mapping,verified=False))['status'],'QUARANTINED')
        outside=instant_display(datetime(2026,1,6,tzinfo=timezone.utc),basis='REFERENCE_SESSION',mapping=mapping,server='TEST',symbol='TEST')
        self.assertIsNone(outside['XM'])
        wrong=instant_display(datetime(2026,1,5,12,tzinfo=timezone.utc),basis='REFERENCE_SESSION',mapping=mapping,server='OTHER',symbol='TEST')
        self.assertIsNone(wrong['XM'])
        self.assertEqual([v['original_xm']['time_msc'] for v in chart_points([raw,raw],mapping)],[raw.time_msc]*2)

    def test_unknown_native_event_has_no_converted_event_clock(self):
        raw=NativeTimestamp(100,100000,'US30Cash','XM','a'*64)
        view=event_display(raw)
        self.assertEqual(view['status'],'QUARANTINED')
        self.assertTrue(all(view[k] is None for k in ('Ecuador','Nueva York','UTC')))
        self.assertIn('sin mapping', view['XM'])
        self.assertEqual(view['original_xm']['time_msc'],100000)
