/** Structured console logging. Only catalogued fields and normalized errors leave this module. */
export type Environment = 'development' | 'test' | 'production';
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';
export type LogSink = (level: LogLevel, serialized: string) => void;
const levels: Record<LogLevel, number> = { debug: 10, info: 20, warn: 30, error: 40 };
const catalog = {
  'logging.configuration.invalid': ['warn', ['setting']],
  'app.init.started': ['info', []],
  'app.init.succeeded': ['info', []],
  'app.init.failed': ['error', []],
  'app.unhandled': ['error', []],
  'hymns.seed.loaded': ['info', ['hymnCount', 'localVersion']],
  'hymns.index.loaded': ['debug', ['hymnCount', 'localVersion']],
  'hymns.index.rebuilt': ['debug', ['hymnCount', 'localVersion']],
  'hymns.sync.started': ['debug', ['localVersion']],
  'hymns.sync.skipped': ['debug', ['reason', 'localVersion', 'remoteVersion']],
  'hymns.sync.succeeded': ['info', ['localVersion', 'remoteVersion', 'receivedCount', 'removedCount']],
  'hymns.sync.remote_failed': ['warn', ['localVersion']],
  'hymns.sync.storage_failed': ['error', ['localVersion']],
  'storage.read.succeeded': ['debug', []],
  'storage.write.succeeded': ['debug', []],
  'storage.read.failed': ['error', []],
  'storage.write.failed': ['error', []],
  'storage.invalid_json': ['warn', []],
  'firebase.init.failed': ['error', []],
  'firebase.metadata.invalid': ['warn', []],
  'firebase.delta.invalid_records': ['warn', ['invalidCount']],
  'share.failed': ['warn', ['kind']],
  'share.fallback': ['debug', ['kind']],
  'native.plugin.unavailable': ['debug', ['plugin']],
  'native.plugin.failed': ['warn', ['plugin']],
} as const;
export type LogEvent = keyof typeof catalog;

let environment: Environment = 'production';
let threshold: LogLevel = 'info';
const sessionId = operationId();
let reported = new WeakSet<object>();
const consoleSink: LogSink = (level, serialized) => console[level](serialized);
let sink = consoleSink;

export function operationId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
}

const member = (value: unknown, values: readonly string[]) => typeof value === 'string' && values.includes(value);
const count = (value: unknown) => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const validators: Record<string, (value: unknown) => boolean> = {
  operationId: value => typeof value === 'string' && /^[a-f0-9-]{10,64}$/.test(value),
  durationMs: count, hymnCount: count, localVersion: count, remoteVersion: count,
  receivedCount: count, removedCount: count, invalidCount: count,
  reason: value => member(value, ['offline', 'unconfigured', 'up_to_date', 'no_metadata', 'unavailable']),
  setting: value => member(value, ['level', 'environment']),
  kind: value => member(value, ['image', 'text', 'worship']),
  plugin: value => member(value, ['wake_lock', 'deep_link']),
  errorType: value => member(value, ['Error', 'TypeError', 'RangeError', 'SyntaxError', 'DOMException', 'FirebaseError', 'Unknown']),
  errorCode: value => member(value, ['unknown', 'permission-denied', 'unauthenticated', 'unavailable', 'deadline-exceeded',
    'failed-precondition', 'resource-exhausted', 'not-found', 'invalid-argument', 'aborted', 'AbortError',
    'UNIMPLEMENTED', 'UNAVAILABLE', 'QuotaExceededError', 'NotAllowedError', 'SecurityError', 'InvalidStateError', 'DataError', 'ConstraintError']),
};
const common = ['operationId', 'durationMs', 'errorType', 'errorCode'];

export function configureLogging(options: { environment: Environment; level?: string; sink?: LogSink }): void {
  sink = options.sink ?? consoleSink;
  environment = member(options.environment, ['development', 'test', 'production']) ? options.environment : 'production';
  const fallback: LogLevel = environment === 'development' ? 'debug' : 'info';
  const selected = options.level?.toLowerCase() ?? fallback;
  threshold = Object.hasOwn(levels, selected) ? selected as LogLevel : fallback;
  if (environment !== options.environment) log('logging.configuration.invalid', { setting: 'environment' });
  if (!Object.hasOwn(levels, selected)) log('logging.configuration.invalid', { setting: 'level' });
}

export function log(event: LogEvent, context: Record<string, unknown> = {}): void {
  try {
    if (!Object.hasOwn(catalog, event)) return;
    const [level, fields] = catalog[event];
    if (levels[level] < levels[threshold]) return;
    const allowed: readonly string[] = [...common, ...fields];
    const safe = Object.fromEntries(Object.entries(context)
      .filter(([key, value]) => allowed.includes(key) && validators[key]?.(value)));
    sink(level, JSON.stringify({ timestamp: new Date().toISOString(), level, component: 'mobile',
      environment, event, sessionId, context: safe }));
  } catch {
    // Logging and console failures must not interrupt the application.
  }
}

export function normalizeError(error: unknown): { errorType: string; errorCode: string } {
  try {
    const candidate = error as { name?: unknown; code?: unknown } | null;
    const name = candidate?.name;
    const rawCode = candidate?.code;
    const code = typeof rawCode === 'string' ? rawCode.replace(/^firestore\//, '') : name;
    return {
      errorType: validators.errorType(name) ? name as string : 'Unknown',
      errorCode: validators.errorCode(code) ? code as string : 'unknown',
    };
  } catch { return { errorType: 'Unknown', errorCode: 'unknown' }; }
}

export function reportError(event: LogEvent, error: unknown, context: Record<string, unknown> = {}): void {
  try {
    if (error !== null && (typeof error === 'object' || typeof error === 'function')) {
      if (reported.has(error)) return;
      reported.add(error);
    }
    log(event, { ...context, ...normalizeError(error) });
  } catch { /* Do not expose raw errors if a context object cannot be inspected. */ }
}

/** Useful for tests and explicit app restarts; never stores error text. */
export function resetReportedErrors(): void { reported = new WeakSet<object>(); }
