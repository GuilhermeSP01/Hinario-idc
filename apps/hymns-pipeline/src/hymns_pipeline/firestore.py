"""Publish an immutable Gold release in one conditional, atomic Firestore commit."""
import json
import re
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
        if (remote.get('releaseHash') == manifest['releaseHash'] and active == desired
                and remote.get('totalHymns') == len(desired)
                and remote.get('updatedAt') == release['updatedAt']):
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
        tombstone = dict(id=key, number=int(fields.get('number', 0)),
                         title=str(fields.get('title', '')), sections=[], deleted=True,
                         version=release['version'], updatedAt=release['updatedAt'])
        writes.append(update_write(f'{base}/hymns/{key}', tombstone, previous))
        removals += 1
    target_metadata = dict(currentVersion=release['version'], updatedAt=release['updatedAt'],
                           totalHymns=len(desired), releaseHash=manifest['releaseHash'])
    writes.append(update_write(f'{base}/metadata/version', target_metadata, metadata))
    if len(writes) > MAX_WRITES or len(canonical({'writes': writes})) > MAX_COMMIT_BYTES:
        raise ValueError('Release exceeds atomic publication limits; no writes were sent')
    return writes, {'unchanged': False, 'upserts': len(desired), 'removals': removals,
                    'version': release['version'], 'writes': len(writes)}


class Firestore:
    def __init__(self, project, session=None):
        if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]', project):
            raise ValueError('Invalid Google Cloud project ID')
        if session is None:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession
            credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/datastore'])
            session = AuthorizedSession(credentials)
        self.session = session
        self.base = f'projects/{project}/databases/(default)/documents'
        self.url = f'https://firestore.googleapis.com/v1/{self.base}'

    def request(self, method, url, body=None, missing_ok=False):
        response = self.session.request(method, url, json=body, timeout=30)
        if missing_ok and response.status_code == 404:
            return None
        if not 200 <= response.status_code < 300:
            # Do not dump auth headers, credentials or response payloads into logs.
            raise ValueError(f'Firestore HTTP {response.status_code}; publication not confirmed. '
                             'For conflicts or timeouts, read remote state and repeat the dry-run.')
        return response.json()

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


def publish(release, manifest, project, expected_remote_version, dry_run=False, client=None):
    client = client or Firestore(project)
    metadata, existing = client.snapshot()
    writes, summary = plan(release, manifest, client.base, metadata, existing, expected_remote_version)
    print(json.dumps(dict(summary, project=project, dryRun=dry_run), ensure_ascii=False))
    if writes and not dry_run:
        # All documents and metadata share one commit. Per-document preconditions reject races.
        client.request('POST', client.url + ':commit', {'writes': writes})
    return summary
