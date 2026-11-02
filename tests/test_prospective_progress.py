import unittest
from controller.pretrain_contracts import seal
from controller.prospective_progress import classify_tail


class ProgressAuditTests(unittest.TestCase):
    def chain(self,bodies):
        head='a'*64;rows=[]
        for n,b in enumerate(bodies,10):
            digest=seal(dict(previous=head,payload=b));rows.append((n,head,digest,b));head=digest
        return rows

    def comparison(self):
        return dict(kind='BAR_COMPARISON',evidence_hash='reference',bucket=dict(timeframe_seconds=300,issues=[]),
                    parity_exact=True,bid_sequence_coverage={'status':'PASS_EXACT_NATIVE_BID_SEQUENCE_REFERENCE'})

    def test_valid_reference_parity_does_not_mean_scientific_certification(self):
        bar=dict(time=300,segment='s',evidence_hash='reference')
        rows=self.chain([self.comparison(),dict(kind='CLOSED_AGGREGATE_BAR',bar=bar,bar_hash=seal(bar))])
        r=classify_tail(rows,10,'a'*64)
        self.assertEqual(r['classification_counts']['300'],{'VALID_REFERENCE_PARITY_QUARANTINED':1})
        self.assertEqual(r['admitted_intervals'],0)

    def test_partial_and_rejected_are_exclusive_m5_categories(self):
        bodies=[]
        for issues in (['FIRST_PARTIAL_BUCKET'],[]):
            bodies += [self.comparison(),dict(kind='INCOMPLETE_BUCKET',evidence_hash='reference',
                observed_bucket=dict(timeframe_seconds=300,open_msc=300000,segment='s',issues=issues),reasons=['MISMATCH'])]
        r=classify_tail(self.chain(bodies),10,'a'*64)
        self.assertEqual(r['classification_counts']['300'],{'PARTIAL_REJECTED':1,'REJECTED':1})

    def test_tampered_tail_or_missing_comparison_is_rejected(self):
        rows=self.chain([self.comparison()]);bad=list(rows);n,p,d,b=bad[0];bad[0]=(n,p,d,b|{'parity_exact':False})
        with self.assertRaises(ValueError):classify_tail(bad,10,'a'*64)
        bar=dict(time=300,segment='s',evidence_hash='absent')
        with self.assertRaises(ValueError):classify_tail(self.chain([dict(kind='CLOSED_AGGREGATE_BAR',bar=bar,bar_hash=seal(bar))]),10,'a'*64)

    def test_reference_failure_cannot_be_counted_as_valid(self):
        bar=dict(time=300,segment='s',evidence_hash='reference');c=self.comparison();c['parity_exact']=False
        with self.assertRaises(ValueError):classify_tail(self.chain([c,dict(kind='CLOSED_AGGREGATE_BAR',bar=bar,bar_hash=seal(bar))]),10,'a'*64)

    def test_future_features_and_unreviewed_admission_fail(self):
        bad=dict(kind='CAUSAL_PREFIX_FEATURES',feature_cutoff_native_msc=300,decision_input_ref={'native_time_msc':300},ready_stage=1,decision_stage=2)
        with self.assertRaises(ValueError):classify_tail(self.chain([bad]),10,'a'*64)
        with self.assertRaises(ValueError):classify_tail(self.chain([{'kind':'CHECKPOINT','admitted':True}]),10,'a'*64)
