import copy
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hymns_pipeline.layers import ingest, silver, gold, load_gold, load_bronze
from hymns_pipeline.seed import render_seed
from hymns_pipeline.storage import DATA, read_json
from hymns_pipeline.validation import validate_release


class LayerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)
        self.source = DATA / 'bronze/sv-001/source.odt'
        ingest(self.source, 'test-001', self.data)

    def build(self):
        dataset = silver('test-001', self.data)
        gold(dataset, 3, '2026-11-04T02:33:25.207726+00:00', self.data)
        return dataset, load_gold(3, self.data)[0]

    def test_repeatable_layers_and_legacy_seed(self):
        dataset, release = self.build()
        before = {str(p): p.read_bytes() for p in self.data.rglob('*') if p.is_file()}
        self.assertEqual(silver('test-001', self.data), dataset)
        ingest(self.source, 'test-001', self.data)
        gold(dataset, 3, release['updatedAt'], self.data)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.data.rglob('*') if p.is_file()})
        from hymns_pipeline.layers import load_gold
        self.assertEqual(render_seed(release), render_seed(load_gold(3)[0]))
        report = read_json(self.data / 'silver' / dataset / 'report.json')
        self.assertEqual(report['acceptedHymns'], 236)
        self.assertEqual(sum(e['reason'] == 'approved_legacy_duplicate' for e in report['exclusions']), 2)
        self.assertTrue(any(e['reason'] == 'excluded_range' for e in report['exclusions']))

    def test_bronze_tampering_and_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            ingest(self.source, '../escape', self.data)
        (self.data / 'bronze/test-001/source.odt').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            load_bronze('test-001', self.data)

    def test_gold_is_immutable(self):
        dataset, release = self.build()
        with self.assertRaisesRegex(ValueError, 'Immutable'):
            gold(dataset, 3, '2026-11-05T00:00:00Z', self.data)
        self.assertEqual(load_gold(3, self.data)[0], release)

    def test_tampered_silver_and_gold_rejected(self):
        dataset, _ = self.build()
        path = self.data / 'gold/3/hymns.json'
        original = path.read_bytes()
        path.write_text(path.read_text().replace('Antífona', 'Changed'))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            load_gold(3, self.data)
        path.write_bytes(original)
        path = self.data / 'silver' / dataset / 'hymns.json'
        path.write_text(path.read_text().replace('Antífona', 'Changed'))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            load_gold(3, self.data)

    def test_new_duplicate_conflict_requires_review(self):
        with patch('hymns_pipeline.layers.read_json', wraps=read_json) as reader:
            def without_approvals(path):
                return [] if str(path).endswith('duplicates-v1.json') else read_json(path)
            reader.side_effect = without_approvals
            with self.assertRaisesRegex(ValueError, 'requires review'):
                silver('test-001', self.data)

    def test_contract_and_domain_failures(self):
        _, release = self.build()
        for mutation in ('empty', 'duplicate', 'version', 'title', 'sections', 'verse', 'timestamp', 'field'):
            bad = copy.deepcopy(release)
            if mutation == 'empty': bad['hymns'] = []
            elif mutation == 'duplicate': bad['hymns'].append(bad['hymns'][0])
            elif mutation == 'version': bad['hymns'][0]['version'] += 1
            elif mutation == 'title': bad['hymns'][0]['title'] = ' '
            elif mutation == 'sections': bad['hymns'][0]['sections'] = []
            elif mutation == 'verse': bad['hymns'][0]['sections'][0]['number'] = 5
            elif mutation == 'timestamp': bad['hymns'][0]['updatedAt'] = 'bad'
            else: bad['hymns'][0]['unexpected'] = True
            with self.subTest(mutation=mutation), self.assertRaises(Exception):
                validate_release(bad)

    def test_updated_document_preserves_old_source_and_release(self):
        _, original_release = self.build()
        original_bytes = (self.data / 'bronze/test-001/source.odt').read_bytes()
        updated = self.data / 'updated.odt'
        with zipfile.ZipFile(self.source) as old, zipfile.ZipFile(updated, 'w') as new:
            for member in old.infolist():
                content = old.read(member.filename)
                if member.filename == 'content.xml':
                    needle = 'A Ti, ó Deus, fiel e bom Senhor.'.encode()
                    self.assertIn(needle, content)
                    content = content.replace(needle, 'A Ti, ó Deus, fiel Senhor.'.encode(), 1)
                new.writestr(member, content)
        ingest(updated, 'test-002', self.data)
        dataset = silver('test-002', self.data)
        gold(dataset, 4, '2026-11-08T00:00:00Z', self.data)
        updated_release, _ = load_gold(4, self.data)
        self.assertNotEqual(original_release['hymns'][0]['sections'], updated_release['hymns'][0]['sections'])
        self.assertEqual(load_gold(3, self.data)[0], original_release)
        self.assertEqual((self.data / 'bronze/test-001/source.odt').read_bytes(), original_bytes)
