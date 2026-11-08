"""Publish an immutable Gold release in one conditional, atomic Firestore commit."""
import re
import os
from time import perf_counter
from . import observability as logs
from urllib.parse import quote
from .storage import canonical, digest
from .validation import validate_release

MAX_WRITES = 400  # Conservative bound; never split a logical release across commits.
MAX_COMMIT_BYTES = 9 * 1024 * 1024
MAX_DOCUMENT_BYTES = 900 * 1024


def to_value(value):
    if value is None:
        return {'nullValue': None}
    if isinstance(value, bool):
        return {'booleanValue': value}
    if isinstance(value, int):
        return {'integerValue': str(value)}
    if isinstance(value, str):
        return {'stringValue': value}
    if isinstance(value, list):
        return {'arrayValue': {'values': [to_value(item) for item in value]}}
    if isinstance(value, dict):
        return {'mapValue': {'fields': {key: to_value(item) for key, item in value.items()}}}
    raise ValueError(f'Unsupported Firestore value: {type(value).__name__}')


def from_value(value):
    if 'nullValue' in value:
        return None
    if 'integerValue' in value:
        return int(value['integerValue'])
    if 'doubleValue' in value:
        return float(value['doubleValue'])
    if 'timestampValue' in value:
        return value['timestampValue']
    if 'booleanValue' in value:
        return value['booleanValue']
    if 'stringValue' in value:
        return value['stringValue']
    if 'arrayValue' in value:
        return [from_value(item) for item in value['arrayValue'].get('values', [])]
    if 'mapValue' in value:
        return {key: from_value(item) for key, item in value['mapValue'].get('fields', {}).items()}
    raise ValueError('Unexpected Firestore field type')


def document_fields(document):
    return {key: from_value(value) for key, value in document.get('fields', {}).items()}


def update_write(name, fields, previous=None):
    condition = {'updateTime': previous['updateTime']} if previous else {'exists': False}
    document = {'name': name, 'fields': {key: to_value(value) for key, value in fields.items()}}
    if len(canonical(document)) > MAX_DOCUMENT_BYTES:
        raise ValueError('Document exceeds conservative Firestore size limit')
    return {'update': document, 'currentDocument': condition}


def plan(release, manifest, base, metadata, existing, expected_remote_version):
    validate_release(release)
    if manifest['releaseHash'] != digest(release):
        raise ValueError('Release hash mismatch')
    remote = document_fields(metadata) if metadata else {}
    remote_version = remote.get('currentVersion', 0)
    if type(remote_version) is not int or remote_version < 0:
        raise ValueError('Invalid remote metadata version')
    if remote_version != expected_remote_version:
        raise ValueError(f'Remote version changed: expected {expected_remote_version}, got {remote_version}')
    desired = {hymn['id']: hymn for hymn in release['hymns']}
    active = {key: document_fields(doc) for key, doc in existing.items()
              if not document_fields(doc).get('deleted', False)}
    if remote_version == release['version']:
        from .remote import normalize_fields
        active_content = {key:normalize_fields(key,fields) for key,fields in active.items()}
        desired_content = {key:normalize_fields(key,fields) for key,fields in desired.items()}
        if (remote.get('releaseHash') == manifest['releaseHash'] and active_content == desired_content
                and remote.get('totalHymns') == len(desired)):
            return [], {'unchanged': True, 'upserts': 0, 'removals': 0, 'version': remote_version}
        raise ValueError('Version already used by different content; create a higher Gold release')
    if release['version'] < remote_version:
        raise ValueError('Release version must be higher than remote version')
    writes = [update_write(f'{base}/hymns/{key}', hymn, existing.get(key))
              for key, hymn in desired.items()]
    removals = 0
    for key in sorted(existing.keys() - desired.keys()):
        previous = existing[key]
        fields = document_fields(previous)
        if fields.get('deleted', False):
            continue
        # Preserve old IDs (including legacy IDs) so delta clients receive tombstones.
        tombstone = dict(id=key, number=fields.get('number', 0) if type(fields.get('number',0)) is int else 0,
                         title=fields.get('title','') if isinstance(fields.get('title',''),str) else '', sections=[], deleted=True,
                         version=release['version'], updatedAt=release['updatedAt'])
        writes.append(update_write(f'{base}/hymns/{key}', tombstone, previous))
        removals += 1
    target_metadata = dict(currentVersion=release['version'], updatedAt=release['updatedAt'],
                           totalHymns=len(desired), releaseHash=manifest['releaseHash'])
    writes.append(update_write(f'{base}/metadata/version', target_metadata, metadata))
    if len(writes) > MAX_WRITES or len(canonical({'writes': writes})) > MAX_COMMIT_BYTES:
        raise ValueError('Release exceeds atomic publication limits; no writes were sent')
    content_keys = ('id', 'number', 'title', 'sections')
    added = sorted(desired.keys() - active.keys())
    removed = sorted(active.keys() - desired.keys())
    changed = sorted(key for key in desired.keys() & active.keys()
                     if any(desired[key].get(field) != active[key].get(field) for field in content_keys))
    return writes, {'unchanged': False, 'addedIds': added, 'changedIds': changed,
                    'removedIds': removed, 'upserts': len(desired), 'removals': removals,
                    'version': release['version'], 'writes': len(writes)}


class PublicationError(ValueError):
    def __init__(self, message, *, unknown=False, http_status=None):
        super().__init__(message)
        self.unknown = unknown
        self.http_status = http_status
        self.logged = False


class Firestore:
    def __init__(self, project, session=None):
        if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]', project):
            raise ValueError('Invalid Google Cloud project ID')
        emulator = os.environ.get('FIRESTORE_EMULATOR_HOST')
        if emulator:
            if not project.startswith('demo-') or not re.fullmatch(r'(?:127\.0\.0\.1|localhost):[0-9]{1,5}',emulator) or not 0<int(emulator.rsplit(':',1)[1])<65536:
                raise ValueError('Emulator requires a demo project and a loopback endpoint')
            if session is None:
                import requests
                session = requests.Session()
                session.headers['Authorization'] = 'Bearer owner'
        if session is None:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession
            from google.auth.exceptions import DefaultCredentialsError
            try:
                credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/datastore'])
            except DefaultCredentialsError:
                raise ValueError('ADC credentials unavailable; configure Application Default Credentials '
                                 'or Workload Identity Federation before publishing.') from None
            session = AuthorizedSession(credentials)
        self.session = session
        self.base = f'projects/{project}/databases/(default)/documents'
        self.url = f'http://{emulator}/v1/{self.base}' if emulator else f'https://firestore.googleapis.com/v1/{self.base}'

    def request(self, method, url, body=None, missing_ok=False):
        from requests.exceptions import RequestException
        from google.auth.exceptions import GoogleAuthError
        try:
            response = self.session.request(method, url, json=body, timeout=30)
        except GoogleAuthError:
            raise PublicationError('Firestore authentication failed; no confirmed publication.') from None
        except RequestException:
            raise PublicationError('Firestore request failed; publication not confirmed. '
                             'Read remote state and repeat the dry-run before retrying.', unknown=method == 'POST') from None
        if missing_ok and response.status_code == 404:
            return None
        if not 200 <= response.status_code < 300:
            # Do not dump auth headers, credentials or response payloads into logs.
            raise PublicationError(f'Firestore HTTP {response.status_code}; publication not confirmed. '
                             'For conflicts or timeouts, read remote state and repeat the dry-run.',
                                   unknown=method == 'POST' and (response.status_code >= 500 or response.status_code == 408),
                                   http_status=response.status_code)
        try:
            return response.json()
        except ValueError:
            raise PublicationError('Invalid Firestore response; publication not confirmed.', unknown=method == 'POST') from None

    def snapshot(self):
        metadata = self.request('GET', self.url + '/metadata/version', missing_ok=True)
        existing = {}
        page = ''
        while True:
            url = self.url + '/hymns?pageSize=300'
            if page:
                url += '&pageToken=' + quote(page, safe='')
            result = self.request('GET', url)
            for doc in result.get('documents', []):
                existing[doc['name'].rsplit('/', 1)[1]] = doc
            page = result.get('nextPageToken', '')
            if not page:
                break
        return metadata, existing


def publish(release, manifest, project, expected_remote_version, dry_run=False, client=None, *, baseline=None):
    start = perf_counter()
    context = dict(projectId=project, releaseVersion=release['version'],
                   releaseHash=manifest['releaseHash'], dryRun=dry_run, expectedRemoteVersion=expected_remote_version)
    committing = False
    try:
        client = client or Firestore(project)
        metadata, existing = client.snapshot()
        context['remoteVersion'] = document_fields(metadata).get('currentVersion', 0) if metadata else 0
        writes, summary = plan(release, manifest, client.base, metadata, existing, expected_remote_version)
        from .remote import verify_baseline
        verify_baseline(release,baseline,project,metadata,existing,unchanged=not writes)
        context.update(writes=len(writes), upserts=summary['upserts'], removals=summary['removals'],
                       addedCount=len(summary.get('addedIds', [])), changedCount=len(summary.get('changedIds', [])))
        logs.emit('firestore.publish.planned', **context)
        if not writes:
            outcome = 'unchanged'
        elif dry_run:
            outcome = 'simulated'
        else:
            logs.emit('firestore.publish.started', **context)
            committing = True
            client.request('POST', client.url + ':commit', {'writes': writes})
            committing = False
            outcome = 'succeeded'
        logs.emit('firestore.publish.' + outcome, durationMs=logs.elapsed(start), **context)
        return summary
    except Exception as error:
        unknown = error.unknown if isinstance(error, PublicationError) else committing
        details = logs.error_context(error)
        if isinstance(error, PublicationError):
            details = dict(errorType='PublicationError', errorCode='publication_outcome_unknown' if unknown else 'publication_failed')
            if error.http_status is not None:
                details['httpStatus'] = error.http_status
        logs.emit('firestore.publish.outcome_unknown' if unknown else 'firestore.publish.failed',
                  level='error', durationMs=logs.elapsed(start), **details, **context)
        failure = error if isinstance(error, PublicationError) else PublicationError('Publication failed.', unknown=unknown)
        failure.logged = True
        raise failure from None
