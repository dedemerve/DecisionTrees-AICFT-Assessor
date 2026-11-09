"""WS7 must follow the three printed rules, including equality boundaries."""
import unittest
from pipeline_integration import score_ws7_deterministic

class PrintedRulesTest(unittest.TestCase):
    def score(self, answers):
        return score_ws7_deterministic(dict(zip((f'WS7_{i}' for i in range(1,8)), answers)), 'Sample_Student')

    def test_printed_key(self):
        self.assertEqual(self.score(['<180','≥180','<7,7 g','>=7.7','B','A','C'])['total_score'],7)

    def test_equalities_are_not_interchangeable(self):
        self.assertEqual(self.score(['≤180','>180','≤7.7','>7.7','B','A','C'])['total_score'],3)

    def test_old_food_card_key_is_not_accepted(self):
        self.assertEqual(self.score(['<200','>200','<11','≥11','B','A','C'])['total_score'],3)

    def test_wrong_numeric_values_and_missing_operators(self):
        self.assertEqual(self.score(['180','≥181','<7.0','≥11','B','A','C'])['total_score'],3)

if __name__ == '__main__':
    unittest.main()
