import copy
import hashlib
import json
from pathlib import Path
import unittest
from scripts.score_ws12 import complementary, parse_threshold, score_group, build_revision, REVISION, REPO

class WS12RevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obs=json.loads((REVISION/'observations.json').read_text())
    def group(self,index=2):return copy.deepcopy(self.obs['groups'][index])
    def rows(self,g):return {int(r['printed_item_id']):r for r in score_group(g)['items']}
    def test_complementary_numeric_cutpoints(self):
        self.assertTrue(complementary('≤229','>229'))
        self.assertFalse(complementary('≤229','>250'))
        self.assertFalse(complementary('<229','>229'))
    def test_orientation_commas_and_units(self):
        self.assertTrue(complementary('<2,5g','2,5≤'))
        self.assertTrue(complementary('≤240kcal','240<'))
    def test_placeholders_unverified(self):
        for v in [None,'','(not_extracted)','N/A','0','≤bad']:
            self.assertIsNone(parse_threshold(v))
    def test_ambiguous_pair_not_credited(self):
        g=self.group();g['items']['2']['ambiguous']=True
        r=self.rows(g)
        self.assertEqual([r[i]['status'] for i in [2,3]],['unknown','unknown'])
    def test_blank_active_threshold_not_inferred(self):
        g=self.group();g['items']['8']={'value':None,'state':'blank'}
        r=self.rows(g);self.assertEqual(r[8]['status'],'blank');self.assertEqual(r[9]['status'],'unknown')
    def test_pure_stop_descendants_excluded(self):
        r=self.rows(self.group())
        for i in [6,7,10,11]:
            self.assertEqual(r[i]['status'],'structural_na');self.assertIsNone(r[i]['score']);self.assertIsNone(r[i]['max_score'])
    def test_no_purity_evidence_no_automatic_na(self):
        g=self.group();g['counts'].pop('left')
        r=self.rows(g)
        for i in [6,7,10,11]:self.assertEqual(r[i]['status'],'unknown')
    def test_checkbox_accepted_as_decision(self):
        self.assertEqual(self.rows(self.group())[4]['status'],'correct')
    def test_counts_not_decisions(self):
        g=self.group();g['decisions'].pop('rl');g['items']['12']={'value':None,'state':'blank'}
        self.assertEqual(self.rows(g)[12]['status'],'unknown')
    def test_wrong_actual_prediction_uses_opposite_class(self):
        g=self.group();g['decisions']['rl']='not_recommended';g['items']['14']['value']=0
        r=self.rows(g);self.assertEqual(r[12]['status'],'incorrect');self.assertEqual(r[14]['status'],'incorrect')
        g['items']['14']['value']=1;self.assertEqual(self.rows(g)[14]['status'],'correct')
    def test_missing_counts_do_not_gain_plausibility_credit(self):
        g=self.group();g['counts'].pop('rl')
        self.assertEqual(self.rows(g)[14]['status'],'unknown')
    def test_zero_is_response_not_blank(self):
        r=self.rows(self.group());self.assertEqual(r[14]['value'],0);self.assertEqual(r[14]['status'],'correct')
        self.assertEqual(r[15]['status'],'unknown')
    def test_test_reference_missing(self):
        for v in [0,1,12,999]:
            g=self.group();g['items']['15']['value']=v
            self.assertEqual(self.rows(g)[15]['status'],'unknown')
    def test_independent_conservation_only(self):
        g=self.group();g['counts'].pop('right')
        self.assertEqual(score_group(g)['count_diagnostics'][0]['status'],'unknown')
        g=self.group();g['counts']['right']=[2,6]
        self.assertEqual(score_group(g)['count_diagnostics'][0]['status'],'inconsistent')
    def test_mirrored_tree(self):
        g=self.group()
        g['items']['4'],g['items']['5']=g['items']['5'],g['items']['4']
        for a,b in [(6,8),(7,9),(10,12),(11,13)]:g['items'][str(a)],g['items'][str(b)]=g['items'][str(b)],g['items'][str(a)]
        g['counts']={'right':[5,0],'left':[1,7],'ll':[1,0],'lr':[0,7]}
        g['decisions']={'right':'recommended','ll':'recommended','lr':'not_recommended'}
        r=self.rows(g);self.assertEqual(r[14]['status'],'correct')
        for i in [8,9,12,13]:self.assertEqual(r[i]['status'],'structural_na')
    def test_coverage_unique_no_human_inputs(self):
        data=build_revision();self.assertEqual(len(data['groups']),7)
        keys=[(s,r['item']) for g in data['groups'] for s in g['students'] for r in g['items']]
        self.assertEqual(len(keys),195);self.assertEqual(len(keys),len(set(keys)))
        self.assertTrue(all(g['total_score'] is None for g in data['groups']))
        self.assertNotIn('human',json.dumps(self.obs['groups']))
    def test_protected_sources_unchanged(self):
        hashes=json.loads((REVISION/'source_hashes.json').read_text())
        for p,h in hashes.items():self.assertEqual(hashlib.sha256((REPO/p).read_bytes()).hexdigest(),h,p)
    def test_missing_feature_is_not_wrong_or_blank(self):
        for value in [None,'','(not_extracted)','unknown']:
            g=self.group();g['items']['1']={'value':value,'state':'missing'}
            r=self.rows(g)[1];self.assertEqual(r['status'],'unknown');self.assertIsNone(r['score'])
    def test_schema_numbering(self):
        sch=json.loads((REPO/'worksheets/WS12/extraction_schema.json').read_text())
        self.assertEqual(sch['form_slot_map']['14'],'WS12_train_errors')
        self.assertEqual(sch['form_slot_map']['15'],'WS12_test_errors')
        self.assertEqual(len({f['field_id'] for f in sch['fields']}),len(sch['fields']))

if __name__=='__main__':unittest.main()
