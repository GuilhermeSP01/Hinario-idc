import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8090';
let index;
for (let attempt = 0; attempt < 20; attempt++) {
  try {
    const response = await fetch(base);
    assert.equal(response.status, 200);
    index = await response.text();
    break;
  } catch (error) {
    if (attempt === 19) throw error;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
}
assert.match(index, /<div id="app"><\/div>/);
for (const route of ['/hymn', '/favorites', '/settings']) {
  const response = await fetch(`${base}${route}`);
  assert.equal(response.status, 200, route);
  assert.equal(await response.text(), index, route);
}
const assets = [...index.matchAll(/(?:src|href)="(\/assets\/[^\"]+)"/g)].map(match => match[1]);
assert.ok(assets.length > 0);
for (const asset of assets) {
  const response = await fetch(`${base}${asset}`);
  assert.equal(response.status, 200, asset);
  assert.match(response.headers.get('cache-control'), /immutable/);
}
const missing = await fetch(`${base}/assets/does-not-exist.js`);
assert.equal(missing.status, 404);
console.log('Web container: index, SPA routes, assets, caching and missing assets verified.');
