import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { Config } = require('firebase-tools/lib/config');
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const config = Config.load({ cwd: root, configPath: 'firebase.json' });
const expected = {
  'firestore.rules': 'infra/firebase/firestore.rules',
  'firestore.indexes': 'infra/firebase/firestore.indexes.json',
  'hosting.public': 'apps/mobile/dist',
};
for (const [key, path] of Object.entries(expected)) {
  assert.equal(config.path(config.get(key)), resolve(root, path));
  assert.ok(existsSync(config.path(config.get(key))), `Missing ${path}; run pnpm build first`);
}
const indexes = JSON.parse(readFileSync(config.path(config.get('firestore.indexes'))));
assert.ok(Array.isArray(indexes.indexes));
assert.ok(existsSync(resolve(root, '.firebaserc')));
assert.deepEqual(config.get('hosting.rewrites'), [{ source: '**', destination: '/index.html' }]);
console.log('Firebase CLI resolves rules, indexes and Hosting build inside the repository.');
