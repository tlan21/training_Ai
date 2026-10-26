"""Isolated synthetic fixtures only: never write ratings into the actual evaluation packet."""

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from prepare_youtube_evaluation import IDS, save, sha


class PacketChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.packet = Path(self.temporary.name)
        self.ids = [f'fixture_{i:02}' for i in range(30)]
        save(self.packet / 'samples.json', [{'sample_id': i} for i in self.ids])
        self.manifest = self.packet / 'manifest.json'
        self.result = self.packet / 'result.json'
        save(self.manifest, {'packet': str(self.packet), 'evaluation_kind': 'real_video',
                             'samples_sha256': sha(self.packet / 'samples.json'), 'results_file': str(self.result)})
        for rater in range(1, 4):
            self.write_sheet(rater, '')

    def write_sheet(self, rater, score, ids=None):
        with (self.packet / f'ratings_rater_{rater}.csv').open('w', encoding='utf-8-sig', newline='') as target:
            writer = csv.writer(target)
            writer.writerow(['sample_id', 'overall_score_1_to_5', 'notes'])
            writer.writerows((i, score, 'SYNTHETIC TEST ONLY') for i in (ids or self.ids))

    def run_scorer(self):
        return subprocess.run([sys.executable, str(Path(__file__).with_name('score_human_pilot.py')),
                               '--manifest', str(self.manifest)], capture_output=True, encoding='utf-8')

    def test_blank_is_pending(self):
        self.assertEqual(self.run_scorer().returncode, 0)
        result = json.loads(self.result.read_text(encoding='utf-8'))
        self.assertEqual(result['completed'], 0)
        self.assertIsNone(result['mean'])
        self.assertIsNone(result['threshold_pass'])

    def test_all_scores_required_for_pass(self):
        for rater in range(1, 4):
            self.write_sheet(rater, '3')
        self.assertEqual(self.run_scorer().returncode, 0)
        result = json.loads(self.result.read_text(encoding='utf-8'))
        self.assertEqual(result['mean'], 3)
        self.assertEqual(result['video_human_DoD'], 'PASS')
        self.assertEqual(len(result['samples']), 30)

    def test_partial_has_no_overall_mean(self):
        self.write_sheet(1, '5')
        self.assertEqual(self.run_scorer().returncode, 0)
        result = json.loads(self.result.read_text(encoding='utf-8'))
        self.assertEqual(result['completed'], 30)
        self.assertIsNone(result['mean'])

    def test_pilot_never_certifies_video(self):
        manifest = json.loads(self.manifest.read_text(encoding='utf-8'))
        manifest.pop('evaluation_kind')
        save(self.manifest, manifest)
        for rater in range(1, 4):
            self.write_sheet(rater, '5')
        self.assertEqual(self.run_scorer().returncode, 0)
        result = json.loads(self.result.read_text(encoding='utf-8'))
        self.assertTrue(result['pilot_threshold_pass'])
        self.assertTrue(result['video_human_DoD'].startswith('NOT EVALUATED'))

    def test_reject_invalid_scores(self):
        for score in ['0', '6', '3.5', 'abc']:
            with self.subTest(score=score):
                self.write_sheet(1, score)
                self.assertNotEqual(self.run_scorer().returncode, 0)

    def test_reject_duplicate_ids(self):
        self.write_sheet(1, '', [self.ids[0]] * 30)
        self.assertNotEqual(self.run_scorer().returncode, 0)

    def test_reject_changed_samples(self):
        (self.packet / 'samples.json').write_text('[]', encoding='utf-8')
        self.assertNotEqual(self.run_scorer().returncode, 0)

    def test_source_and_hash_checks(self):
        self.assertEqual(len(IDS), 10)
        self.assertEqual(len(set(IDS)), 10)
        self.assertEqual(sha(self.packet / 'samples.json'), hashlib.sha256((self.packet / 'samples.json').read_bytes()).hexdigest())
        self.assertFalse(list(self.packet.glob('*.tmp')))


if __name__ == '__main__':
    unittest.main()
