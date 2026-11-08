import { readFile, writeFile } from 'node:fs/promises';
import { compile } from 'json-schema-to-typescript';
const schema = JSON.parse(await readFile(new URL('../schemas/hymn.schema.json', import.meta.url)));
const generated = await compile(schema, 'Hymn', {
  unreachableDefinitions: true,
  ignoreMinAndMaxItems: true,
  bannerComment: '/* Generated from schemas/hymn.schema.json. Run pnpm --filter @hinario/hymns-contracts generate. */',
});
const target = new URL('../src/hymn.generated.ts', import.meta.url);
if (process.argv.includes('--check')) {
  if (await readFile(target, 'utf8') !== generated) throw new Error('Generated types are stale');
} else {
  await writeFile(target, generated);
}
