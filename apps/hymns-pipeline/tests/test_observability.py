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
