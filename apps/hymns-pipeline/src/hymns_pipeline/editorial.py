"""Immutable editorial revisions. CRUD is local; publishing is a separate operation."""
from contextlib import contextmanager
from copy import deepcopy
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4
from .storage import DATA, digest, encode, immutable_directory, read_json
from .validation import validate_content, validate_hymns

CONTENT = ('id', 'number', 'title', 'sections')


def content(hymn):
    return {key: deepcopy(hymn[key]) for key in CONTENT}


def ordered(hymns):
    result = sorted(hymns, key=lambda h: (h['number'], h['id']))
    validate_hymns(result)
    return result


def revision_id(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        raise ValueError('Invalid editorial revision')
    return value


def location(data):
    return Path(data) / 'editorial'


@contextmanager
def edit_lock(data):
    directory = location(data)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.lock').open('a+b') as stream:
        try:
            if os.name == 'nt':
                import msvcrt
                if stream.tell() == 0:
                    stream.write(b'0'); stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError('Another editorial command holds the lock') from None
        try:
            yield
        finally:
            if os.name == 'nt':
                stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def initial(base_version, data):
    from .layers import load_gold, load_silver
    release, manifest = load_gold(base_version, data)
    hymns = [content(h) for h in release['hymns']]
    if manifest['schemaVersion'] == 2:
        prior = load_revision(manifest['revisionId'], data)
        mapping, retired = prior['sourceMapping'], prior['retiredIds']
    else:
        silver = load_silver(manifest['datasetId'], data)
        ids = {h['number']: h['id'] for h in hymns}
        mapping = {str(h['sourceOrdinal']): ids[h['number']] for h in silver['hymns']}
        historical = set()
        for path in (Path(data) / 'gold').iterdir():
            if path.is_dir() and path.name.isdigit() and int(path.name) < base_version:
                old, _ = load_gold(int(path.name), data)
                historical.update(h['id'] for h in old['hymns'])
        retired = sorted(historical - {h['id'] for h in hymns})
    return dict(schemaVersion=1, baseRelease=base_version, baseReleaseHash=digest(release),
                datasetId=manifest['datasetId'], sourceMapping=mapping, hymns=ordered(hymns),
                retiredIds=retired, checkpoint=None, parent=None,
                operation={'type': 'initialize', 'reason': 'Initialize from versioned release'})


def apply_operation(parent, operation, data):
    reason = operation.get('reason')
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
        raise ValueError('A nonempty editorial reason is required (up to 1000 characters)')
    result = deepcopy(parent)
    result['parent'] = digest(parent)
    result['operation'] = deepcopy(operation)
    by_id = {h['id']: h for h in result['hymns']}
    kind = operation['type']
    if kind == 'create':
        hymn = operation['after']
        if hymn['id'] in by_id or hymn['id'] in result['retiredIds']:
            raise ValueError('Hymn identity already used')
        if not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}', hymn['id']):
            raise ValueError('New hymn identity must be UUID4')
        validate_content({k:v for k,v in hymn.items() if k != 'id'})
        by_id[hymn['id']] = deepcopy(hymn)
    elif kind in ('update', 'delete'):
        target = operation['id']
        if target not in by_id:
            raise ValueError('Hymn not found in active editorial revision')
        if digest(by_id[target]) != operation['beforeHash']:
            raise ValueError('Editorial precondition changed')
        if kind == 'update':
            patch = operation['patch']
            validate_content(patch, partial=True)
            updated = dict(by_id[target], **deepcopy(patch))
            if updated == by_id[target]:
                raise ValueError('No editorial changes')
            by_id[target] = updated
        else:
            del by_id[target]
            result['retiredIds'] = sorted(set(result['retiredIds']) | {target})
    elif kind == 'source':
        from .source_reconciliation import apply_source
        return apply_source(parent, operation, data)
    elif kind == 'remote':
        from .remote import apply_remote
        return apply_remote(parent, operation, data)
    else:
        raise ValueError('Unknown editorial operation')
    result['hymns'] = ordered(list(by_id.values()))
    return result


def persist(record, data):
    rid = digest(record)
    immutable_directory(location(data) / 'revisions' / rid, {'revision.json': encode(record)})
    return rid


def load_revision(rid, data=DATA):
    """Replay the chain and compare every snapshot, not only its checksum."""
    rid = revision_id(rid)
    chain, seen = [], set()
    cursor = rid
    while cursor:
        if cursor in seen:
            raise ValueError('Cyclic editorial history')
        seen.add(cursor)
        record = read_json(location(data) / 'revisions' / revision_id(cursor) / 'revision.json')
        if digest(record) != cursor or record.get('schemaVersion') != 1:
            raise ValueError('Editorial checksum mismatch')
        chain.append(record)
        cursor = record['parent']
    first = chain.pop()
    if first != initial(first['baseRelease'], data):
        raise ValueError('Editorial baseline mismatch')
    current = first
    for recorded in reversed(chain):
        current = apply_operation(current, recorded['operation'], data)
        if current != recorded:
            raise ValueError('Editorial replay mismatch')
    return current


def head(data=DATA):
    from .layers import load_gold
    current_version = read_json(Path(data) / 'current.json')['release']
    if type(current_version) is not int or current_version < 1:
        raise ValueError('Invalid current release')
    pointer = location(data) / 'head.json'
    if not pointer.exists():
        record = initial(current_version, data)
        return digest(record), record
    rid = read_json(pointer)['revision']
    record = load_revision(rid, data)
    if current_version != record['baseRelease']:
        _, manifest = load_gold(current_version, data)
        if manifest.get('revisionId') != rid:
            raise ValueError('Current release changed while editorial work is pending')
        record = initial(current_version, data)
        return digest(record), record
    return rid, record


def write_head(rid, data):
    directory = location(data)
    fd, temporary = tempfile.mkstemp(prefix='.head-', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encode({'revision': rid})); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, directory / 'head.json')
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def commit_operation(parent, operation, data):
    result = apply_operation(parent, operation, data)
    persist(parent, data)
    rid = persist(result, data)
    write_head(rid, data)
    return rid, result


def mutate(kind, *, hymn_id=None, payload=None, reason, data=DATA):
    if kind in ('create', 'update'):
        validate_content(payload, partial=kind == 'update')
    with edit_lock(data):
        _, parent = head(data)
        operation = {'type': kind, 'reason': reason}
        previous = next((h for h in parent['hymns'] if h['id'] == hymn_id), None)
        if kind == 'create':
            operation['after'] = dict(id=str(uuid4()), **deepcopy(payload))
        elif kind in ('update', 'delete'):
            if previous is None: raise ValueError('Hymn not found in active editorial revision')
            operation.update(id=hymn_id, beforeHash=digest(previous))
            if kind == 'update': operation['patch'] = deepcopy(payload)
        else:
            raise ValueError('Unknown CRUD operation')
        rid, result = commit_operation(parent, operation, data)
        target = operation['after']['id'] if kind == 'create' else hymn_id
        after = next((h for h in result['hymns'] if h['id'] == target), None)
        return dict(revision=rid, id=target, before=previous, after=after,
                    warning='Links shared by number may resolve differently after renumbering.'
                    if previous and after and previous['number'] != after['number'] else None)


def release_revision(rid, version, updated_at, data=DATA):
    from .layers import load_silver
    from .validation import timestamp, validate_release
    record = load_revision(rid, data)
    if type(version) is not int or version <= record['baseRelease']:
        raise ValueError('Editorial release must be newer than its baseline')
    updated_at = timestamp(updated_at)
    hymns = [dict(h, version=version, updatedAt=updated_at, deleted=False) for h in record['hymns']]
    release = dict(schemaVersion=1, version=version, updatedAt=updated_at, totalHymns=len(hymns), hymns=hymns)
    validate_release(release)
    manifest = dict(schemaVersion=2, baseRelease=record['baseRelease'], revisionId=rid,
                    datasetId=record['datasetId'], silverHash=digest(load_silver(record['datasetId'], data)),
                    releaseHash=digest(release))
    return immutable_directory(Path(data)/'gold'/str(version),
                               {'hymns.json':encode(release),'manifest.json':encode(manifest)})
