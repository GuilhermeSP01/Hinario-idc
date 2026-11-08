"""Shared JSON Schema contracts plus domain invariants."""
from datetime import datetime, timezone
from jsonschema import Draft7Validator, FormatChecker
from referencing import Registry, Resource
from .storage import ROOT, read_json

SCHEMAS = ROOT / 'packages/hymns-contracts/schemas'
HYMN = read_json(SCHEMAS / 'hymn.schema.json')
RELEASE = read_json(SCHEMAS / 'release.schema.json')
REGISTRY = Registry().with_resource('hymn.schema.json', Resource.from_contents(HYMN))


def timestamp(value):
    # Normalize explicit release timestamps; no wall clock in transformation outputs.
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Release timestamp must include timezone')
    return parsed.astimezone(timezone.utc).isoformat()


def validate_hymns(hymns):
    if not hymns:
        raise ValueError('Empty dataset')
    ids, numbers = set(), set()
    for hymn in hymns:
        number = hymn['number']
        if type(number) is not int or number < 1 or number in numbers:
            raise ValueError('Invalid/duplicate hymn number')
        numbers.add(number)
        if 'id' in hymn:
            if hymn['id'] != f'{number:03d}' or hymn['id'] in ids:
                raise ValueError('Invalid/duplicate hymn id')
            ids.add(hymn['id'])
        if not hymn['title'].strip() or not hymn['sections']:
            raise ValueError('Hymn must have title and sections')
        verse = 1
        for section in hymn['sections']:
            if not section['lines'] or any(not line.strip() for line in section['lines']):
                raise ValueError('Empty lyric line/section')
            if section['type'] == 'verse':
                if section.get('number') != verse:
                    raise ValueError('Verse numbers must be sequential')
                verse += 1
            elif section['type'] != 'chorus' or 'number' in section:
                raise ValueError('Invalid chorus')
    if [h['number'] for h in hymns] != sorted(numbers):
        raise ValueError('Hymns must be ordered by number')


def validate_release(release):
    Draft7Validator(RELEASE, registry=REGISTRY, format_checker=FormatChecker()).validate(release)
    validate_hymns(release['hymns'])
    if release['totalHymns'] != len(release['hymns']):
        raise ValueError('totalHymns mismatch')
    for hymn in release['hymns']:
        if hymn['version'] != release['version'] or hymn.get('deleted') is not False:
            raise ValueError('Release contains inconsistent version/deletion state')
        if hymn.get('updatedAt') != release['updatedAt']:
            raise ValueError('Release timestamp mismatch')
