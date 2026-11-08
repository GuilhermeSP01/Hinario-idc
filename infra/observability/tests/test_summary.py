import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
spec = importlib.util.spec_from_file_location('summary', Path(__file__).resolve().parents[1] / 'summarize.py')
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


class SummaryTests(unittest.TestCase):
    def test_only_safe_generated_values_are_presented(self):
        records = [{'level': 'info', 'event': 'pipeline.command.succeeded', 'runId': 'a'*36,
                    'context': {'token': 'SECRET', 'message': '[SECRET](https://private)'}},
                   {'level': 'warn', 'event': 'SECRET', 'runId': 'SECRET'}]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'events.jsonl'
            path.write_text('\n'.join(json.dumps(r) for r in records))
            result = summary.summarize(path)
        self.assertNotIn('SECRET', result)
        self.assertIn('Concluído', result)
        self.assertIn('avisos: 1', result)

    def test_absent_success_does_not_report_success(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'events.jsonl'
            path.write_text('{"level":"error","event":"pipeline.command.failed"}')
            self.assertIn('Falhou', summary.summarize(path))
