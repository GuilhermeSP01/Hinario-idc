import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';

const container = process.argv[2];
const base = process.argv[3] || 'http://127.0.0.1:8090';
assert.ok(container && /^[a-zA-Z0-9_.-]+$/.test(container), 'Provide a container name');
const marker = 'PRIVATE_LOG_SENTINEL';
const requests = [];
for (const [path, category, status] of [
  [`/?token=${marker}`, '/', 200],
  [`/hymn?c=${marker}`, '/hymn', 200],
  [`/${marker}?token=${marker}`, '/other', 200],
  [`/assets/${marker}.js?token=${marker}`, '/assets/*', 404],
]) {
  const response = await fetch(base + path, { headers: {
    Authorization: `Bearer ${marker}`, Cookie: `session=${marker}`,
    Referer: `https://example.invalid/?token=${marker}`, 'X-Request-ID': marker,
  } });
  await response.arrayBuffer();
  const requestId = response.headers.get('x-request-id');
  assert.match(requestId, /^[a-f0-9]{32}$/);
  assert.equal(response.status, status);
  requests.push({ requestId, category, status });
}
let records;
for (let attempt = 0; attempt < 10; attempt++) {
  const result = spawnSync('docker', ['--host=unix:///var/run/docker.sock', 'logs', container], { encoding: 'utf8' });
  assert.equal(result.status, 0);
  const output = result.stdout + result.stderr;
  assert.ok(!output.includes(marker), 'Sensitive synthetic input leaked to container logs');
  records = output.split('\n').flatMap(line => {
    try { const record = JSON.parse(line); return record.event === 'http.request.completed' ? [record] : []; }
    catch { return []; }
  });
  if (requests.every(request => records.some(record => record.requestId === request.requestId))) break;
  await new Promise(resolve => setTimeout(resolve, 100));
}
for (const request of requests) {
  const record = records.find(record => record.requestId === request.requestId);
  assert.ok(record, 'Response ID must correlate with access log');
  assert.equal(record.context.path, request.category);
  assert.equal(record.context.status, request.status);
  assert.equal(typeof record.context.durationSeconds, 'number');
  assert.deepEqual(Object.keys(record.context).sort(), ['durationSeconds', 'method', 'path', 'responseBytes', 'status']);
}
console.log('Nginx logs: JSON, request correlation and exclusion of query/header/private path verified.');
