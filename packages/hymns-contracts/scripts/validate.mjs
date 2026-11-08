import { readFile, readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { validateRelease as validate, errorsText } from './validator.mjs';
let paths = process.argv.slice(2);
if (paths.length === 1 && paths[0] === '--all') {
  const directory = new URL('../../../apps/hymns-pipeline/data/gold/', import.meta.url);
  paths = (await readdir(directory, { withFileTypes: true }))
    .filter(entry => entry.isDirectory() && /^\d+$/.test(entry.name))
    .map(entry => fileURLToPath(new URL(`${entry.name}/hymns.json`, directory)));
}
if (!paths.length) throw new Error('Provide at least one gold hymns.json path');
for (const path of paths) {
  if (!validate(JSON.parse(await readFile(path)))) throw new Error(`${path}: ${errorsText()}`);
  console.log(`Valid release: ${path}`);
}
