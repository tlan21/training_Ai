"""Small deterministic metric checks with synthetic, isolated text fixtures."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'ai-core'))
from diagnose_asr_reference import reference_metrics


class MetricChecks(unittest.TestCase):
    def test_identical(self):
        result = reference_metrics([{'reference': 'AB CD', 'asr': {'full_transcript': 'AB CD'}}])
        self.assertEqual(result['corpus_wer'], 0)
        self.assertEqual(result['corpus_cer'], 0)

    def test_corpus_weighting_and_macro_differ(self):
        rows = [{'reference': 'A', 'asr': {'full_transcript': ''}},
                {'reference': 'B C D', 'asr': {'full_transcript': 'B C D'}}]
        result = reference_metrics(rows)
        self.assertEqual(result['macro_wer'], .5)
        self.assertEqual(result['corpus_wer'], .25)
        self.assertEqual(result['word_errors'], 1)
        self.assertEqual(result['reference_words'], 4)
        self.assertEqual(result['corpus_cer'], 1 / 6)

    def test_no_reference_is_not_measured(self):
        for rows in [[], [{'reference': '', 'asr': {'full_transcript': 'A'}}]]:
            with self.assertRaises(AssertionError):
                reference_metrics(rows)


if __name__ == '__main__':
    unittest.main()
