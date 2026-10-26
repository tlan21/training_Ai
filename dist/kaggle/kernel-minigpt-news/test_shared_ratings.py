"""Synthetic fixtures are isolated from the real human submission."""

import unittest

from evaluate_shared_ratings import summarize


class SharedRatingChecks(unittest.TestCase):
    def setUp(self):
        self.rows = [{'sample_id': f'fixture_{i:02}', 'overall_score_1_to_5': '', 'notes': '1'} for i in range(30)]
        self.expected = {r['sample_id'] for r in self.rows}

    def test_notes_import_is_30_observed_not_90(self):
        for row in self.rows[:4]:
            row['notes'] = ' 5'
        self.rows[4]['notes'] = '3'
        result = summarize(self.rows, self.expected)
        self.assertEqual(result['observed_score_records'], 30)
        self.assertEqual(result['mean'], 1.6)
        self.assertFalse(result['threshold_pass'])
        self.assertEqual(result['score_counts'], {'1': 25, '2': 0, '3': 1, '4': 0, '5': 4})

    def test_explicit_score_column(self):
        for row in self.rows:
            row.update(overall_score_1_to_5='3', notes='free text')
        self.assertEqual(summarize(self.rows, self.expected)['mean'], 3)

    def test_invalid_or_missing_scores_rejected(self):
        for value in ['', '0', '6', '3.5', 'good']:
            with self.subTest(value=value):
                self.rows[0]['notes'] = value
                with self.assertRaises(AssertionError):
                    summarize(self.rows, self.expected)

    def test_duplicate_id_rejected(self):
        self.rows[0]['sample_id'] = self.rows[1]['sample_id']
        with self.assertRaises(AssertionError):
            summarize(self.rows, self.expected)

    def test_partial_misplaced_scores_rejected(self):
        self.rows[0]['overall_score_1_to_5'] = '1'
        with self.assertRaises(AssertionError):
            summarize(self.rows, self.expected)


if __name__ == '__main__':
    unittest.main()
