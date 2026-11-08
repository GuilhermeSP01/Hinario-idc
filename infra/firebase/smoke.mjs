import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const expected = await readFile(new URL('../../apps/mobile/dist/index.html', import.meta.url), 'utf8');
for (const route of ['/', '/hymn', '/favorites', '/settings']) {
  const response = await fetch(`http://127.0.0.1:5000${route}`);
  assert.equal(response.status, 200, route);
  assert.equal(await response.text(), expected, route);
}
console.log('Hosting serves the build and rewrites SPA routes.');

if (!process.argv.includes('--hosting-only')) {
  const base = 'http://127.0.0.1:8080/v1/projects/demo-hinario-idc/databases/(default)/documents';
  for (const collection of ['hymns', 'metadata']) {
    const response = await fetch(`${base}/${collection}`);
    assert.equal(response.status, 200, `Public read: ${collection}`);
    const denied = await fetch(`${base}/${collection}/infra-smoke`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fields: { title: { stringValue: 'Unauthorized write' } } }),
    });
    assert.equal(denied.status, 403, `Unauthenticated write denied: ${collection}`);
  }
  const denied = await fetch(`${base}/private`);
  assert.equal(denied.status, 403, 'Unmatched collection denied');
  console.log('Firestore allows public hymn/metadata reads and rejects unauthorized writes.');
}
