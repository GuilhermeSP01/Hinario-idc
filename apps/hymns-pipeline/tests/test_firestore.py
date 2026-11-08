import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hymns_pipeline.firestore import (Firestore, document_fields, from_value, plan, publish,
                                     to_value)
from hymns_pipeline.storage import digest

BASE = 'projects/hinario-idc/databases/(default)/documents'
STAMP = '2026-11-04T00:00:00+00:00'


def hymn(number=1, title='Antífona', version=4):
    return dict(id=f'{number:03d}', number=number, title=title,
                sections=[dict(type='verse', number=1, lines=['Aleluia'])],
                version=version, deleted=False, updatedAt=STAMP)


def doc(key, value):
    return dict(name=f'{BASE}/{key}', fields={k: to_value(v) for k, v in value.items()},
                updateTime='2026-11-03T00:00:00.123456Z')


class FirestoreTests(unittest.TestCase):
    def setUp(self):
        self.release = dict(schemaVersion=1, version=4, updatedAt=STAMP, totalHymns=1, hymns=[hymn()])
        self.manifest = dict(releaseHash=digest(self.release))
        self.metadata = doc('metadata/version', dict(currentVersion=3))

    def test_one_atomic_commit_including_tombstones_and_metadata(self):
        existing = {'001': doc('hymns/001', hymn(title='Old', version=3)),
                    '002': doc('hymns/002', hymn(2, version=3)),
                    '7': doc('hymns/7', hymn(7, version=3))}
        writes, summary = plan(self.release, self.manifest, BASE, self.metadata, existing, 3)
        self.assertEqual(summary['removals'], 2)
        self.assertEqual(summary['changedIds'], ['001'])
        self.assertEqual(summary['removedIds'], ['002', '7'])
        self.assertEqual(len(writes), 4)
        self.assertTrue(all('updateTime' in w['currentDocument'] for w in writes))
        values = [document_fields(w['update']) for w in writes]
        self.assertEqual(values[0]['title'], 'Antífona')
        self.assertTrue(values[1]['deleted'])
        self.assertTrue(values[2]['deleted'])
        self.assertEqual(values[-1]['currentVersion'], 4)
        self.assertFalse(any('delete' in w for w in writes))

    def test_insertions_require_document_to_be_absent(self):
        writes, _ = plan(self.release, self.manifest, BASE, None, {}, 0)
        self.assertTrue(all(w['currentDocument'] == {'exists': False} for w in writes))

    def test_repeat_is_noop_and_same_version_cannot_change_content(self):
        metadata = doc('metadata/version', dict(currentVersion=4, updatedAt=STAMP, totalHymns=1,
                                               releaseHash=self.manifest['releaseHash']))
        existing = {'001': doc('hymns/001', hymn())}
        writes, summary = plan(self.release, self.manifest, BASE, metadata, existing, 4)
        self.assertEqual(writes, [])
        self.assertTrue(summary['unchanged'])
        existing['001'] = doc('hymns/001', hymn(title='Drift'))
        with self.assertRaisesRegex(ValueError, 'already used'):
            plan(self.release, self.manifest, BASE, metadata, existing, 4)

    def test_version_conflicts_and_downgrade_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Remote version changed'):
            plan(self.release, self.manifest, BASE, self.metadata, {}, 2)
        metadata = doc('metadata/version', dict(currentVersion=5))
        with self.assertRaisesRegex(ValueError, 'higher'):
            plan(self.release, self.manifest, BASE, metadata, {}, 5)

    def test_publication_limits_fail_before_any_write(self):
        release = copy.deepcopy(self.release)
        release['hymns'] = [hymn(n) for n in range(1, 401)]
        release['totalHymns'] = 400
        with self.assertRaisesRegex(ValueError, 'limits'):
            plan(release, {'releaseHash': digest(release)}, BASE, self.metadata, {}, 3)
        release = copy.deepcopy(self.release)
        release['hymns'][0]['sections'][0]['lines'] = ['x' * (901 * 1024)]
        with self.assertRaisesRegex(ValueError, 'size limit'):
            plan(release, {'releaseHash': digest(release)}, BASE, self.metadata, {}, 3)

    def test_dry_run_never_sends_commit(self):
        client = Mock(base=BASE, url='https://firestore.googleapis.com/v1/' + BASE)
        client.snapshot.return_value = self.metadata, {}
        from hymns_pipeline.remote import snapshot
        baseline=dict(projectId='hinario-idc',snapshot=snapshot(self.metadata,{}),allowMissingHash=False)
        publish(self.release, self.manifest, 'hinario-idc', 3, True, client, baseline=baseline)
        client.request.assert_not_called()
        publish(self.release, self.manifest, 'hinario-idc', 3, False, client, baseline=baseline)
        client.request.assert_called_once()
        self.assertEqual(client.request.call_args.args[0], 'POST')
        self.assertEqual(len(client.request.call_args.args[2]['writes']), 2)

    def test_http_failures_and_pagination(self):
        session = Mock()
        client = Firestore('hinario-idc', session)
        def response(code, data):
            return Mock(status_code=code, json=Mock(return_value=data))
        session.request.side_effect = [response(404, {}),
            response(200, {'documents': [doc('hymns/001', hymn())], 'nextPageToken': 'a+/='}),
            response(200, {'documents': [doc('hymns/002', hymn(2))]})]
        metadata, existing = client.snapshot()
        self.assertIsNone(metadata)
        self.assertEqual(set(existing), {'001', '002'})
        self.assertIn('pageToken=a%2B%2F%3D', session.request.call_args.args[1])
        session.request.side_effect = None
        session.request.return_value = response(409, {})
        with self.assertRaisesRegex(ValueError, 'HTTP 409'):
            client.request('POST', client.url + ':commit', {})

    def test_value_encoding_roundtrip(self):
        value = {'bool': True, 'int': 4, 'empty': [], 'null': None, 'nested': [{'text': 'Ó Rei'}]}
        self.assertEqual(from_value(to_value(value)), value)

    def test_transport_error_is_reported_without_credential_details(self):
        from requests.exceptions import Timeout
        session = Mock()
        session.request.side_effect = Timeout('Sensitive internal request detail')
        client = Firestore('hinario-idc', session)
        with self.assertRaisesRegex(ValueError, 'publication not confirmed') as error:
            client.request('POST', client.url + ':commit', {})
        self.assertNotIn('Sensitive', str(error.exception))
