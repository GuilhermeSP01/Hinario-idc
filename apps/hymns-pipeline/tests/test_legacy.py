"""Reference checks captured before migrating the extractor (no output writes)."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('legacy', ROOT / 'tools/extract_hymns.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


class LegacyExtractionTests(unittest.TestCase):
    def test_document_matches_published_dataset(self):
        hymns = legacy.extract_hymns()
        expected = json.loads((ROOT / 'tools/output/hymns.json').read_text())['hymns']
        self.assertEqual(hymns, expected)
        self.assertEqual(len(hymns), 236)
        canonical = json.dumps(hymns, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        self.assertEqual(hashlib.sha256(canonical.encode()).hexdigest(),
                         'ce2d50ac7b2a8579ff57021b129bb44b8f61664fb1c36ca8e3eaa3e697f8673b')

    def test_editorial_normalization(self):
        self.assertEqual(legacy.normalize_text('  EXUTALÇÃO\u00a0  ÓRei '), 'EXALTAÇÃO Ó Rei')
        self.assertEqual(legacy.format_title_pt('GRANDE É O SENHOR.'), 'Grande É o Senhor')
        self.assertEqual(legacy.clean_lyric_line('Ponte: Aleluia (Coro)'), 'Aleluia')

    def test_chorus_and_verse_boundaries(self):
        line = legacy.LineSegment
        sections = legacy.build_sections_from_lines([
            line('Verso', False, False), line('', False, False),
            line('Coro:', False, False), line('Aleluia', True, False),
            line('', False, False), line('(Coro)', False, False),
            line('Ponte: Final', False, False),
        ])
        self.assertEqual(sections, [
            {'type': 'verse', 'number': 1, 'lines': ['Verso']},
            {'type': 'chorus', 'lines': ['Aleluia']},
            {'type': 'verse', 'number': 2, 'lines': ['Final']},
        ])
