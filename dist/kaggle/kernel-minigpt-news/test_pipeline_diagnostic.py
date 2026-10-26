import json
import tempfile
import unittest
from pathlib import Path

from diagnose_minigpt_pipeline import array_rows, repeated_trigram_fraction


class PipelineDiagnosticTests(unittest.TestCase):
    def read(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'rows.json'
            path.write_text(text, encoding='utf-8')
            return list(array_rows(path))

    def test_streams_unicode_and_records_larger_than_buffer(self):
        rows = [{'id': 'đúng', 'body': 'lời, "chuẩn"\n'*10000}, {'id': '2'}]
        self.assertEqual(self.read(json.dumps(rows, ensure_ascii=False, indent=2)), rows)
        self.assertEqual(self.read('[]'), [])

    def test_rejects_incomplete_or_malformed_records(self):
        for text in ('[{"id": 1}', '[{"id":', '[{},]', '[{} {}]'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.read(text)

    def test_repetition_is_zero_for_short_or_unique_sequences(self):
        for text in ('', 'một hai', 'một hai ba bốn năm'):
            self.assertEqual(repeated_trigram_fraction(text), 0)
        self.assertAlmostEqual(repeated_trigram_fraction('An ninh an ninh an ninh'), .5)


if __name__ == '__main__':
    unittest.main()
