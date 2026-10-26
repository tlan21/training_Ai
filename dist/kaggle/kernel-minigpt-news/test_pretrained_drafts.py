import unittest

from transcribe_pretrained_drafts import IDS, STATUS, srt, timestamp


class DraftExportChecks(unittest.TestCase):
    def test_timestamps_carry_milliseconds(self):
        self.assertEqual(timestamp(59.9996), '00:01:00,000')
        self.assertEqual(timestamp(3661.234), '01:01:01,234')
        self.assertEqual(timestamp(0), '00:00:00,000')

    def test_invalid_timestamps(self):
        for value in [-1, float('nan'), float('inf')]:
            with self.assertRaises(AssertionError):
                timestamp(value)

    def test_srt_export(self):
        self.assertEqual(srt([{'start': 0, 'end': 1.25, 'text': ' Xin chào '}]),
                         '1\n00:00:00,000 --> 00:00:01,250\nXin chào\n')
        with self.assertRaises(AssertionError):
            srt([{'start': 2, 'end': 1, 'text': 'bad'}])

    def test_scope_is_three_unverified_drafts(self):
        self.assertEqual(IDS, ['sample_01', 'sample_10', 'sample_28'])
        self.assertEqual(STATUS, 'PRETRAINED_DRAFT_UNVERIFIED')

    def test_srt_end_is_bounded_by_audio(self):
        result = srt([{'start': 52.2, 'end': 60.52, 'text': 'Đoạn cuối'}], 60)
        self.assertIn('00:00:52,200 --> 00:01:00,000', result)


if __name__ == '__main__':
    unittest.main()
