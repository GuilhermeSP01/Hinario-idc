import { readFile } from 'node:fs/promises';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
const hymn = JSON.parse(await readFile(new URL('../schemas/hymn.schema.json', import.meta.url)));
const release = JSON.parse(await readFile(new URL('../schemas/release.schema.json', import.meta.url)));
const ajv = new Ajv({ allErrors: true });
addFormats(ajv);
ajv.addSchema(hymn, 'hymn.schema.json');
const validate = ajv.compile(release);
const paths = process.argv.slice(2);
if (!paths.length) throw new Error('Provide at least one gold hymns.json path');
for (const path of paths) {
  if (!validate(JSON.parse(await readFile(path)))) throw new Error(`${path}: ${ajv.errorsText(validate.errors)}`);
  console.log(`Valid release: ${path}`);
}
