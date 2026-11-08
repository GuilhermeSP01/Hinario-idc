import assert from 'node:assert/strict';
import test from 'node:test';
import { configureLogging, log, reportError, normalizeError, resetReportedErrors } from '../src/index.ts';
function capture(environment, level) {
  const records = [];
  resetReportedErrors();
  configureLogging({ environment, level, sink: (_, serialized) => records.push(JSON.parse(serialized)) });
  return records;
}
test('production/test default to info; development to debug; explicit level overrides', () => {
  for (const environment of ['production', 'test']) {
    const records = capture(environment);
    log('hymns.sync.started'); log('app.init.started');
    assert.deepEqual(records.map(r => r.level), ['info']);
  }
  const records = capture('development');
  log('hymns.sync.started'); assert.equal(records[0].level, 'debug');
  const errors = capture('development', 'ERROR');
  log('app.init.started'); reportError('app.init.failed', Error('private'));
  assert.deepEqual(errors.map(r => r.level), ['error']);
});
test('invalid level falls back and warns without leaking the value', () => {
  const records = capture('production', 'SECRET');
  assert.equal(records[0].event, 'logging.configuration.invalid');
  assert.ok(!JSON.stringify(records).includes('SECRET'));
});
test('allowlist excludes secrets, lyrics, IDs, URLs, arbitrary codes and invalid numbers even in debug', () => {
  const records = capture('development');
  log('hymns.seed.loaded', { hymnCount: 236, localVersion: 3, token: 'SECRET', url: 'https://secret', lyrics: 'SECRET',
    operationId: 'SECRET', durationMs: NaN, errorCode: 'SECRET' });
  reportError('app.init.failed', { name: 'SECRET', code: 'SECRET', message: 'SECRET', stack: 'SECRET' });
  assert.deepEqual(records[0].context, { hymnCount: 236, localVersion: 3 });
  assert.ok(!JSON.stringify(records).includes('SECRET'));
  assert.ok(records.every(r => r.sessionId === records[0].sessionId));
});
test('same error is reported only once across local and global boundaries', () => {
  const records = capture('production'); const error = new Error('private');
  reportError('storage.read.failed', error); reportError('app.init.failed', error); reportError('app.unhandled', error);
  assert.equal(records.length, 1);
});
test('classifies expected cancellation, Firebase permissions and persistence errors', () => {
  assert.equal(normalizeError({ name: 'AbortError' }).errorCode, 'AbortError');
  assert.equal(normalizeError({ code: 'UNIMPLEMENTED' }).errorCode, 'UNIMPLEMENTED');
  assert.equal(normalizeError({ name: 'FirebaseError', code: 'firestore/permission-denied' }).errorCode, 'permission-denied');
  assert.equal(normalizeError({ name: 'QuotaExceededError' }).errorCode, 'QuotaExceededError');
});
test('sink failures and malicious error/context getters cannot break application flow', () => {
  configureLogging({ environment: 'development', sink: () => { throw Error('sink'); } });
  assert.doesNotThrow(() => log('app.init.started'));
  const records = capture('production');
  const error = { get name() { throw Error('SECRET'); } };
  assert.doesNotThrow(() => reportError('app.unhandled', error));
  assert.ok(!JSON.stringify(records).includes('SECRET'));
});
