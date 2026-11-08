"""Bronze sources -> standardized Silver -> database-ready Gold releases."""
from pathlib import Path
import zipfile
import re
from time import perf_counter
from . import observability as logs
from . import odt, transform
from .storage import APP, DATA, digest, encode, file_hash, identifier, immutable_directory, read_json
from .validation import timestamp, validate_hymns, validate_release


def rules_hash():
    paths = [APP / 'src/hymns_pipeline' / name for name in ('odt.py', 'rules.py', 'transform.py')]
    paths += sorted((APP / 'rules').glob('*.json'))
    return digest({str(path.relative_to(APP)): file_hash(path) for path in paths})


def ingest(source, source_version, data=DATA):
    start = perf_counter()
    logs.emit('bronze.ingest.started', level='debug', sourceVersion=source_version)
    source = Path(source)
    identifier(source_version)
    if source.suffix.lower() != '.odt':
        raise ValueError('Supported source format: ODT. DOCX requires a separate reader.')
    with zipfile.ZipFile(source) as archive:
        if archive.read('mimetype').decode().strip() != 'application/vnd.oasis.opendocument.text':
            raise ValueError('Not an ODT document')
        for name in ('content.xml', 'styles.xml'):
            archive.getinfo(name)
    manifest = {'schemaVersion': 1, 'sourceVersion': source_version, 'format': 'odt',
                'file': 'source.odt', 'originalName': source.name, 'sha256': file_hash(source)}
    result = immutable_directory(Path(data) / 'bronze' / source_version,
                               {'source.odt': source.read_bytes(), 'manifest.json': encode(manifest)})
    logs.emit('bronze.ingest.succeeded', sourceVersion=source_version, sourceHash=manifest['sha256'], durationMs=logs.elapsed(start))
    return result


def load_bronze(source_version, data=DATA):
    directory = Path(data) / 'bronze' / identifier(source_version)
    manifest = read_json(directory / 'manifest.json')
    if (manifest['schemaVersion'] != 1 or manifest['sourceVersion'] != source_version
            or manifest['format'] != 'odt' or manifest['file'] != 'source.odt'
            or not manifest['originalName'] or Path(manifest['originalName']).name != manifest['originalName']
            or file_hash(directory / 'source.odt') != manifest['sha256']):
        raise ValueError('Bronze manifest/checksum mismatch')
    return directory, manifest


def silver(source_version, data=DATA):
    start = perf_counter()
    logs.emit('silver.transform.started', level='debug', sourceVersion=source_version)
    directory, source = load_bronze(source_version, data)
    raw = odt.read_hymns(directory / 'source.odt')
    hymns, exclusions = transform.standardize(raw)
    validate_hymns(hymns)
    # Same normalized title with different lyrics must be reviewed, never silently discarded.
    for event in exclusions:
        if event['reason'] == 'duplicate_title':
            original = raw[event['sourceOrdinal'] - 1]
            title = ' '.join(re.sub(r'^(\d{1,3})\.\s*', '', original['header']).strip().upper().split())
            candidates = [h for h in hymns if h['number'] >= 396
                          and ' '.join(h['rawTitle'].upper().split()) == title]
            discarded = transform.build_sections_from_lines(original['lines'])
            if not candidates:
                raise ValueError(f'Duplicate without retained hymn: {title}')
            if candidates[0]['sections'] != discarded:
                decision = {'titleKey': title, 'keptSectionsHash': digest(candidates[0]['sections']),
                            'discardedSectionsHash': digest(discarded)}
                approvals = read_json(APP / 'rules/duplicates-v1.json')
                if not any(all(approval.get(k) == v for k, v in decision.items()) for approval in approvals):
                    raise ValueError(f'Conflicting duplicate title requires review: {title}')
                event['decision'] = decision
                event['reason'] = 'approved_legacy_duplicate'
    payload = {'schemaVersion': 1, 'sourceVersion': source_version, 'sourceHash': source['sha256'],
               'rulesHash': rules_hash(), 'hymns': hymns}
    dataset_id = digest(payload)[:24]
    report = {'rawHymns': len(raw), 'acceptedHymns': len(hymns), 'exclusions': exclusions}
    manifest = {'schemaVersion': 1, 'datasetId': dataset_id, 'sha256': digest(payload),
                'reportHash': digest(report)}
    immutable_directory(Path(data) / 'silver' / dataset_id,
                        {'hymns.json': encode(payload), 'report.json': encode(report),
                         'manifest.json': encode(manifest)})
    logs.emit('silver.transform.succeeded', sourceVersion=source_version, datasetId=dataset_id,
              sourceHash=source['sha256'], rulesHash=payload['rulesHash'], hymnCount=len(hymns),
              rawCount=len(raw), excludedCount=len(exclusions),
              approvedCount=sum(event['reason'] == 'approved_legacy_duplicate' for event in exclusions),
              durationMs=logs.elapsed(start))
    return dataset_id


def load_silver(dataset_id, data=DATA):
    directory = Path(data) / 'silver' / identifier(dataset_id)
    payload = read_json(directory / 'hymns.json')
    manifest = read_json(directory / 'manifest.json')
    report = read_json(directory / 'report.json')
    _, source = load_bronze(payload['sourceVersion'], data)
    if (manifest['schemaVersion'] != 1 or payload['schemaVersion'] != 1
            or manifest['datasetId'] != dataset_id or digest(payload)[:24] != dataset_id
            or digest(payload) != manifest['sha256'] or digest(report) != manifest['reportHash']
            or payload['sourceHash'] != source['sha256']):
        raise ValueError('Silver lineage/checksum mismatch')
    validate_hymns(payload['hymns'])
    return payload


def gold(dataset_id, version, updated_at, data=DATA):
    start = perf_counter()
    logs.emit('gold.release.started', level='debug', datasetId=dataset_id, releaseVersion=version)
    if type(version) is not int or version < 1:
        raise ValueError('Release version must be a positive integer')
    payload = load_silver(dataset_id, data)
    updated_at = timestamp(updated_at)
    hymns = [dict(id=f"{h['number']:03d}", number=h['number'], title=h['title'],
                  sections=h['sections'], version=version, updatedAt=updated_at, deleted=False)
             for h in payload['hymns']]
    release = {'schemaVersion': 1, 'version': version, 'updatedAt': updated_at,
               'totalHymns': len(hymns), 'hymns': hymns}
    validate_release(release)
    manifest = {'schemaVersion': 1, 'datasetId': dataset_id, 'silverHash': digest(payload),
                'releaseHash': digest(release)}
    result = immutable_directory(Path(data) / 'gold' / str(version),
                               {'hymns.json': encode(release), 'manifest.json': encode(manifest)})
    logs.emit('gold.release.succeeded', datasetId=dataset_id, releaseVersion=version,
              releaseHash=manifest['releaseHash'], hymnCount=len(hymns), durationMs=logs.elapsed(start))
    return result


def load_gold(version, data=DATA):
    directory = Path(data) / 'gold' / str(int(version))
    release = read_json(directory / 'hymns.json')
    manifest = read_json(directory / 'manifest.json')
    payload = load_silver(manifest['datasetId'], data)
    if (manifest['schemaVersion'] != 1 or digest(release) != manifest['releaseHash']
            or digest(payload) != manifest['silverHash'] or release['version'] != int(version)):
        raise ValueError('Gold lineage/checksum mismatch')
    validate_release(release)
    expected = [dict(id=f"{h['number']:03d}", number=h['number'], title=h['title'],
                     sections=h['sections'], version=release['version'],
                     updatedAt=release['updatedAt'], deleted=False) for h in payload['hymns']]
    if release['hymns'] != expected:
        raise ValueError('Gold does not match its Silver dataset')
    return release, manifest
