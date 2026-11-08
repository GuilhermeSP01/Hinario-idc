import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hymns_pipeline import observability as logs

APP = Path(__file__).resolve().parents[1]


class LoggingTests(unittest.TestCase):
    def setUp(self):
        self.stream = io.StringIO()
        logs.configure('INFO', environment='test', stream=self.stream)
        self.addCleanup(lambda: logs.configure('ERROR', environment='test', stream=io.StringIO()))

    def test_json_shape_filtering_and_run_correlation(self):
        logs.emit('pipeline.command.started', level='debug')
        logs.emit('pipeline.command.succeeded', durationMs=12, password='secret', token='secret')
        records = [json.loads(line) for line in self.stream.getvalue().splitlines()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['context'], {'durationMs': 12})
        self.assertEqual(records[0]['environment'], 'test')
        self.assertRegex(records[0]['runId'], r'^[a-f0-9-]{36}$')
        self.assertEqual(records[0]['component'], 'hymns-pipeline')

    def test_defaults_and_override_precedence(self):
        with patch.dict(os.environ, {'APP_ENV': 'development'}, clear=True):
            logs.configure(stream=self.stream)
            logs.emit('pipeline.command.started', level='debug')
            self.assertIn('debug', self.stream.getvalue())
        with patch.dict(os.environ, {'APP_ENV': 'production', 'LOG_LEVEL': 'ERROR'}, clear=True):
            logs.configure('DEBUG', stream=self.stream)
            self.assertEqual(logs.LOGGER.level, 10)
        for environment in ['test', 'production']:
            with patch.dict(os.environ, {}, clear=True):
                logs.configure(environment=environment, stream=self.stream)
                self.assertEqual(logs.LOGGER.level, 20)
        with self.assertRaises(ValueError): logs.configure('SECRET')
        with self.assertRaises(ValueError): logs.configure(environment='SECRET')

    def test_sanitization_at_debug_level_and_invalid_values(self):
        logs.configure('DEBUG', environment='test', stream=self.stream)
        logs.emit('pipeline.command.failed', level='error', **logs.error_context(ValueError('Bearer SECRET /private/file')),
                  schemaPath='https://private/?token=SECRET', durationMs=float('nan'))
        logs.emit('bronze.ingest.succeeded', sourceVersion='https://private/?token=SECRET', sourceHash='SECRET')
        self.assertNotIn('SECRET', self.stream.getvalue())
        self.assertNotIn('private', self.stream.getvalue())
        self.assertNotIn('NaN', self.stream.getvalue())

    def test_cli_stdout_is_machine_readable_and_error_once(self):
        env = dict(os.environ, APP_ENV='test', LOG_LEVEL='INFO')
        run = subprocess.run([sys.executable, str(APP/'run.py'), 'transform', '--source-version', 'sv-001'],
                             capture_output=True, text=True, env=env)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertRegex(run.stdout.strip(), '^[a-f0-9]{24}$')
        records = [json.loads(line) for line in run.stderr.splitlines()]
        self.assertEqual(len({record['runId'] for record in records}), 1)
        failed = subprocess.run([sys.executable, str(APP/'run.py'), 'validate', '--release', '999999'],
                                capture_output=True, text=True, env=env)
        self.assertEqual(failed.returncode, 1)
        self.assertEqual(failed.stdout, '')
        records = [json.loads(line) for line in failed.stderr.splitlines()]
        self.assertEqual(sum(record['level'] == 'error' for record in records), 1)
        self.assertNotIn('Traceback', failed.stderr)

    def test_publication_outcomes_are_distinct_and_confirmed_after_commit(self):
        from unittest.mock import Mock
        from test_firestore import BASE, hymn, doc
        from hymns_pipeline.firestore import publish, PublicationError
        from hymns_pipeline.storage import digest
        release = dict(schemaVersion=1, version=4, updatedAt=hymn()['updatedAt'], totalHymns=1, hymns=[hymn()])
        manifest = {'releaseHash': digest(release)}
        for outcome in ('success', 'simulation', 'conflict', 'timeout'):
            with self.subTest(outcome=outcome):
                self.stream.seek(0); self.stream.truncate()
                logs.configure('INFO', environment='test', stream=self.stream)
                client = Mock(base=BASE, url='https://example.invalid')
                client.snapshot.return_value = doc('metadata/version', {'currentVersion': 3}), {}
                def commit(*args):
                    self.assertNotIn('firestore.publish.succeeded', self.stream.getvalue())
                    if outcome == 'conflict': raise PublicationError('secret', http_status=409)
                    if outcome == 'timeout': raise PublicationError('secret', unknown=True)
                client.request.side_effect = commit
                if outcome in ('conflict', 'timeout'):
                    with self.assertRaises(PublicationError) as error:
                        publish(release, manifest, 'hinario-idc', 3, client=client)
                    self.assertTrue(error.exception.logged)
                else:
                    publish(release, manifest, 'hinario-idc', 3, outcome == 'simulation', client)
                records = [json.loads(line) for line in self.stream.getvalue().splitlines()]
                events = [r['event'] for r in records]
                self.assertNotIn('secret', self.stream.getvalue())
                expected = {'success':'succeeded', 'simulation':'simulated', 'conflict':'failed', 'timeout':'outcome_unknown'}[outcome]
                self.assertEqual(events[-1], 'firestore.publish.' + expected)
                self.assertEqual(sum(r['level'] == 'error' for r in records), int(outcome in ('conflict', 'timeout')))
                if outcome == 'simulation': client.request.assert_not_called()

    def test_post_transport_and_server_errors_are_indeterminate(self):
        from unittest.mock import Mock
        from requests.exceptions import Timeout
        from hymns_pipeline.firestore import Firestore, PublicationError
        session = Mock()
        client = Firestore('hinario-idc', session)
        for status in (409, 503):
            session.request.return_value = Mock(status_code=status)
            with self.assertRaises(PublicationError) as error:
                client.request('POST', client.url + ':commit', {})
            self.assertEqual(error.exception.unknown, status == 503)
        session.request.side_effect = Timeout('secret')
        with self.assertRaises(PublicationError) as error:
            client.request('POST', client.url + ':commit', {})
        self.assertTrue(error.exception.unknown)

    def test_cli_publication_failure_is_logged_once(self):
        from unittest.mock import Mock
        from hymns_pipeline.cli import main
        from hymns_pipeline.firestore import PublicationError
        from test_firestore import BASE
        client = Mock(base=BASE, url='https://example.invalid')
        client.snapshot.return_value = None, {}
        client.request.side_effect = PublicationError('secret', unknown=True)
        output, errors = io.StringIO(), io.StringIO()
        args = ['run.py', 'publish', '--release', '3', '--project', 'hinario-idc', '--expected-remote-version', '0']
        with patch.object(sys, 'argv', args), patch('hymns_pipeline.firestore.Firestore', return_value=client), \
             patch.dict(os.environ, {'APP_ENV':'test','LOG_LEVEL':'INFO'}), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors), self.assertRaises(SystemExit):
            main()
        records = [json.loads(line) for line in errors.getvalue().splitlines()]
        self.assertEqual(sum(r['level'] == 'error' for r in records), 1)
        self.assertEqual(output.getvalue(), '')
        self.assertNotIn('secret', errors.getvalue())
