"""Explicit consumer projection from a validated Gold release."""
import json
from .storage import ROOT

SEED = ROOT / 'packages/firebase/src/seed/initialHymns.ts'


def render_seed(release):
    hymns = [{k: h[k] for k in ('id', 'number', 'title', 'sections', 'version')}
             for h in release['hymns']]
    return ("import type { Hymn } from '@hinario/core';\n\n"
            f"export const INITIAL_HINARIO_VERSION = {release['version']};\n\n"
            'export const INITIAL_HYMNS_SEED: Hymn[] = '
            + json.dumps(hymns, ensure_ascii=False, indent=2) + ';\n')


def export_seed(release, check=False):
    content = render_seed(release)
    if check:
        if SEED.read_text(encoding='utf-8') != content:
            raise ValueError('Offline seed differs from Gold release; run hymns:seed')
    else:
        SEED.write_text(content, encoding='utf-8')
