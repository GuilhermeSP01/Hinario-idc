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

test('stable legacy ID may have a different display number and UUID4 IDs are accepted', () => {
  const release=structuredClone(baseline);
  release.hymns[0].number=65535;
  assert.equal(validateRelease(release),true);
  release.hymns[0].id='51cfde53-5391-49fe-91ee-ecb8ee1e4bfa';
  assert.equal(validateRelease(release),true);
  release.hymns[0].number=65536;
  assert.equal(validateRelease(release),false);
});

test('creation and partial update contracts reject publication-managed fields', async () => {
  const {default:Ajv}=await import('ajv');
  const ajv=new Ajv({strict:false});
  const {default:addFormats}=await import("ajv-formats");
  addFormats(ajv);
  const hymn=JSON.parse(await readFile(new URL('../schemas/hymn.schema.json',import.meta.url)));
  ajv.addSchema(hymn,'hymn.schema.json');
  const content=ajv.compile(JSON.parse(await readFile(new URL('../schemas/hymn-content.schema.json',import.meta.url))));
  const update=ajv.compile(JSON.parse(await readFile(new URL('../schemas/hymn-update.schema.json',import.meta.url))));
  assert.equal(update({title:'Corrected'}),true);
  assert.equal(update({}),false);
  assert.equal(update({version:4}),false);
  assert.equal(content({title:'New'}),false);
  assert.equal(content({number:464,title:'New',sections:[{type:'verse',number:1,lines:['Verse']}]}),true);
});
