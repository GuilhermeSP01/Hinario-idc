import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hymns_pipeline.validation import validate_content, validate_hymns


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.hymn = dict(id='145', number=464, title='Rocha Eterna', sections=[dict(type='verse', number=1, lines=['Verso'])])

    def test_number_can_change_without_changing_identity(self):
        validate_hymns([self.hymn])
        hymn = dict(self.hymn, id='51cfde53-5391-49fe-91ee-ecb8ee1e4bfa')
        validate_hymns([hymn])

    def test_invalid_identity_number_and_content_are_rejected(self):
        for change in [dict(id='1'), dict(id='../escape'), dict(number=65536), dict(number=True), dict(title=' '), dict(sections=[])]:
            with self.subTest(change=change), self.assertRaises(Exception):
                validate_hymns([dict(self.hymn, **change)])
        for content in [dict(version=4), dict(title='x', token='secret'), {}]:
            with self.assertRaises(Exception): validate_content(content, partial=True)

    def test_partial_update_and_complete_content(self):
        validate_content({'title':'Corrected'}, partial=True)
        with self.assertRaises(Exception): validate_content({'title':'Corrected'})
        validate_content({k:v for k,v in self.hymn.items() if k!='id'})
