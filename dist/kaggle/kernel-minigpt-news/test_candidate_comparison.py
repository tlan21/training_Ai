import unittest

from compare_asr_candidate import IDS, human_metrics, review


def records():
    return [{'sample_id': sid, 'video_id': 'source', 'start_seconds': 60, 'duration_seconds': 60,
             'audio': 'audio.wav', 'video': 'video.mp4', 'title': '</textarea><script>bad()</script>',
             'channel': 'test', 'unverified_draft': 'DRAFT MUST NOT BECOME REFERENCE',
             'baseline': {'asr': {'full_transcript': 'A'}, 'summary': '<img src=x onerror=bad()>'},
             'candidate': {'asr': {'full_transcript': 'A B'}, 'summary': 'A B'}} for sid in IDS]


class CandidateComparisonTests(unittest.TestCase):
    def test_no_or_partial_human_references_are_not_scored(self):
        refs = [{'sample_id': sid, 'reference': 'A B', 'transcriber': 'test'} for sid in IDS]
        for source in ([], refs[:2], [dict(r, transcriber='') for r in refs]):
            result = human_metrics(records(), source)
            self.assertEqual(result['status'], 'PENDING_HUMAN_REFERENCES')
            self.assertIsNone(result['baseline'])
            self.assertIsNone(result['candidate'])

    def test_complete_references_compare_same_three_ids(self):
        refs = [{'sample_id': sid, 'reference': ' a  b ', 'transcriber': 'test'} for sid in IDS]
        result = human_metrics(records(), list(reversed(refs)))
        self.assertEqual(result['verified_count'], 3)
        self.assertEqual(result['baseline']['macro_wer'], .5)
        self.assertEqual(result['candidate']['macro_wer'], 0)
        self.assertEqual(result['candidate']['macro_cer'], 0)
        with self.assertRaises(AssertionError):
            human_metrics(records(), refs + refs[:1])

    def test_review_escapes_outputs_and_never_prefills_drafts(self):
        page = review(records(), [])
        self.assertEqual(page.count('<article data-id='), 3)
        self.assertEqual(page.count('<video controls'), 3)
        self.assertEqual(page.count('class="reference" rows="6"></textarea>'), 3)
        self.assertNotIn('<script>bad()', page)
        self.assertNotIn('<img src=x', page)
        self.assertNotIn('checked>', page)
        self.assertIn('DRAFT MUST NOT BECOME REFERENCE', page)
        self.assertIn('human_references_3.csv', page)


if __name__ == '__main__':
    unittest.main()
