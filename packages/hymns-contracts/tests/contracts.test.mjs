import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import test from 'node:test';
import { validateRelease } from '../scripts/validator.mjs';
const baseline = JSON.parse(await readFile(new URL('../../../apps/hymns-pipeline/data/gold/3/hymns.json', import.meta.url)));

test('Python-generated Gold release conforms to shared JS contract', () => {
  assert.equal(validateRelease(baseline), true);
});
for (const [name, mutate] of [
  ['unknown field', release => { release.hymns[0].unexpected = true; }],
  ['invalid section', release => { release.hymns[0].sections[0].type = 'bridge'; }],
  ['invalid timestamp', release => { release.hymns[0].updatedAt = 'not-a-date'; }],
  ['invalid ID', release => { release.hymns[0].id = '1'; }],
  ['empty lyric', release => { release.hymns[0].sections[0].lines = ['']; }],
]) {
  test(`Shared JS contract rejects ${name}`, () => {
    const release = structuredClone(baseline);
    mutate(release);
    assert.equal(validateRelease(release), false);
  });
}
