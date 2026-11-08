"""Summarize a synthetic CI check without copying arbitrary log contents to Markdown."""
import json
from pathlib import Path
import re
import sys


def summarize(path):
    records = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    runs = sorted({r.get('runId') for r in records if isinstance(r.get('runId'), str)
                   and re.fullmatch(r'[a-f0-9-]{36}', r['runId'])})
    errors = sum(r.get('level') == 'error' for r in records)
    warnings = sum(r.get('level') == 'warn' for r in records)
    succeeded = any(r.get('event') == 'pipeline.command.succeeded' for r in records)
    result = 'Concluído' if succeeded and not errors else 'Falhou ou não foi concluído'
    return ('### Verificação da pipeline\n\n'
            f'- Resultado: {result}\n'
            f'- Run IDs: {", ".join(runs) or "indisponível"}\n'
            f'- Eventos: {len(records)}; avisos: {warnings}; erros: {errors}\n')


if __name__ == '__main__':
    print(summarize(sys.argv[1]))
