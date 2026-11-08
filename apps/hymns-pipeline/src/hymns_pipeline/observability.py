"""Allowlisted structured events on stderr; command results stay on stdout."""
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import math
import os
import re
import sys
from time import perf_counter
from uuid import uuid4

LOGGER = logging.getLogger('hinario.pipeline')
LOGGER.addHandler(logging.NullHandler())
LOGGER.propagate = False
RUN = ContextVar('pipeline_run', default=None)
ENVIRONMENT = ContextVar('pipeline_environment', default='production')
COMMAND = ContextVar('pipeline_command', default=None)
LEVELS = {'DEBUG': logging.DEBUG, 'INFO': logging.INFO, 'WARN': logging.WARNING, 'ERROR': logging.ERROR}
COMMANDS = {'ingest', 'transform', 'release', 'validate', 'seed', 'publish', 'check', 'create', 'update', 'delete', 'list', 'get', 'reconcile', 'source-reconcile'}


def token(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', value))


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


VALIDATORS = {
    'operation': lambda v: isinstance(v, str) and v in {'create', 'update', 'delete', 'source', 'remote'},
    'revisionId': lambda v: isinstance(v, str) and bool(re.fullmatch(r'[a-f0-9]{64}', v)),
    'sourceVersion': token, 'datasetId': lambda v: isinstance(v, str) and bool(re.fullmatch(r'[a-f0-9]{24}', v)),
    'sourceHash': lambda v: isinstance(v, str) and bool(re.fullmatch(r'[a-f0-9]{64}', v)),
    'rulesHash': lambda v: isinstance(v, str) and bool(re.fullmatch(r'[a-f0-9]{64}', v)),
    'releaseHash': lambda v: isinstance(v, str) and bool(re.fullmatch(r'[a-f0-9]{64}', v)),
    'projectId': lambda v: isinstance(v, str) and bool(re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]', v)),
    'expectedRemoteVersion': number, 'remoteVersion': number, 'releaseVersion': number, 'durationMs': number, 'hymnCount': number, 'rawCount': number,
    'excludedCount': number, 'approvedCount': number, 'writes': number, 'upserts': number,
    'removals': number, 'addedCount': number, 'changedCount': number, 'httpStatus': lambda v: type(v) is int and 100 <= v <= 599,
    'dryRun': lambda v: type(v) is bool,
    'errorType': lambda v: isinstance(v, str) and v in {'ValueError', 'OSError', 'KeyError', 'ValidationError', 'TypeError', 'Exception', 'PublicationError'},
    'errorCode': lambda v: isinstance(v, str) and v in {'invalid_input', 'filesystem_error', 'validation_failed', 'internal_error',
                                'publication_failed', 'publication_outcome_unknown', 'invalid_configuration', 'invalid_arguments',
                                'immutable_conflict', 'integrity_mismatch', 'editorial_review_required', 'remote_version_conflict',
                                'release_version_used', 'version_downgrade', 'publication_limit', 'credentials_unavailable'},
    'schemaPath': lambda v: isinstance(v, str) and len(v) < 300 and bool(re.fullmatch(r'[A-Za-z0-9_/$.-]+', v)),
}
ERROR_FIELDS = {'errorType', 'errorCode', 'schemaPath', 'httpStatus'}
RELEASE_FIELDS = {'expectedRemoteVersion', 'remoteVersion', 'releaseVersion', 'releaseHash', 'projectId', 'dryRun', 'writes', 'upserts',
                  'removals', 'addedCount', 'changedCount', 'hymnCount'}
EVENT_FIELDS = {
    'bronze.ingest.started': {'sourceVersion'},
    'silver.transform.started': {'sourceVersion'},
    'gold.release.started': {'datasetId', 'releaseVersion'},
    'editorial.change.prepared': {'operation', 'revisionId'},
    'pipeline.command.started': set(),
    'pipeline.command.succeeded': {'durationMs'},
    'pipeline.command.failed': ERROR_FIELDS | {'durationMs'},
    'pipeline.configuration.failed': {'errorCode'},
    'bronze.ingest.succeeded': {'sourceVersion', 'sourceHash', 'durationMs'},
    'silver.transform.succeeded': {'sourceVersion', 'datasetId', 'sourceHash', 'rulesHash', 'hymnCount', 'rawCount', 'excludedCount', 'approvedCount', 'durationMs'},
    'gold.release.succeeded': {'datasetId', 'releaseVersion', 'releaseHash', 'hymnCount', 'durationMs'},
    'seed.export.succeeded': {'releaseVersion', 'hymnCount'},
    'seed.check.succeeded': {'releaseVersion', 'hymnCount'},
    'layers.check.succeeded': {'releaseVersion', 'hymnCount'},
    'firestore.publish.planned': RELEASE_FIELDS,
    'firestore.publish.started': RELEASE_FIELDS,
    'firestore.publish.succeeded': RELEASE_FIELDS | {'durationMs'},
    'firestore.publish.simulated': RELEASE_FIELDS | {'durationMs'},
    'firestore.publish.unchanged': RELEASE_FIELDS | {'durationMs'},
    'firestore.publish.failed': RELEASE_FIELDS | ERROR_FIELDS | {'durationMs'},
    'firestore.publish.outcome_unknown': RELEASE_FIELDS | ERROR_FIELDS | {'durationMs'},
}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        context = {key: value for key, value in record.context.items()
                   if key in EVENT_FIELDS[record.event] and VALIDATORS[key](value)}
        if COMMAND.get() in COMMANDS:
            context['command'] = COMMAND.get()
        return json.dumps(dict(timestamp=datetime.now(timezone.utc).isoformat(),
                               level='warn' if record.levelno == logging.WARNING else record.levelname.lower(),
                               component='hymns-pipeline', event=record.event,
                               environment=ENVIRONMENT.get(), runId=RUN.get(), context=context),
                          ensure_ascii=False, allow_nan=False)


class SafeHandler(logging.StreamHandler):
    def handleError(self, record):
        # Logging must not break a command or leak raw records through logging diagnostics.
        pass


def configure(level=None, *, environment=None, command=None, stream=None):
    environment = environment or os.environ.get('APP_ENV', 'production')
    if environment not in {'development', 'test', 'production'}:
        raise ValueError('Invalid APP_ENV')
    selected = level or os.environ.get('LOG_LEVEL') or ('DEBUG' if environment == 'development' else 'INFO')
    if not isinstance(selected, str) or selected.upper() not in LEVELS:
        raise ValueError('Invalid LOG_LEVEL')
    handler = SafeHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(JsonFormatter())
    for old in LOGGER.handlers:
        old.close()
    LOGGER.handlers[:] = [handler]
    LOGGER.setLevel(LEVELS[selected.upper()])
    RUN.set(str(uuid4()))
    ENVIRONMENT.set(environment)
    COMMAND.set(command)
    return RUN.get()


def emit(event, *, level='info', **context):
    if event not in EVENT_FIELDS or level.upper() not in LEVELS:
        raise ValueError('Unknown logging event/level')
    LOGGER.log(LEVELS[level.upper()], event, extra={'event': event, 'context': context})


def elapsed(start):
    return round((perf_counter() - start) * 1000, 3)


def error_context(error):
    # Never serialize exception messages, response bodies, stack locals or paths.
    from jsonschema.exceptions import ValidationError
    if isinstance(error, ValidationError):
        return dict(errorType='ValidationError', errorCode='validation_failed',
                    schemaPath='/'.join(str(part) for part in error.absolute_schema_path))
    if isinstance(error, OSError):
        return dict(errorType='OSError', errorCode='filesystem_error')
    if isinstance(error, TypeError):
        return dict(errorType='TypeError', errorCode='internal_error')
    if isinstance(error, (ValueError, KeyError)):
        reasons = {'Immutable artifact differs': 'immutable_conflict', 'checksum mismatch': 'integrity_mismatch',
                   'hash mismatch': 'integrity_mismatch', 'requires review': 'editorial_review_required',
                   'Remote version changed': 'remote_version_conflict', 'Version already used': 'release_version_used',
                   'must be higher': 'version_downgrade', 'exceeds': 'publication_limit',
                   'ADC credentials unavailable': 'credentials_unavailable'}
        reason = next((code for marker, code in reasons.items() if marker in str(error)), 'invalid_input')
        return dict(errorType=type(error).__name__ if type(error).__name__ in {'ValueError', 'KeyError', 'TypeError'} else 'ValueError',
                    errorCode=reason)
    return dict(errorType='Exception', errorCode='internal_error')
