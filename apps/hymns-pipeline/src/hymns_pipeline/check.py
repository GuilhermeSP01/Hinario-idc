"""Offline readiness and reproducibility checks for the current data release."""
from pathlib import Path
import tempfile
from . import observability as logs
from .layers import load_bronze, load_silver, load_gold, ingest, silver, gold
from .seed import export_seed
from .storage import DATA, read_json


def check(data=DATA):
    data = Path(data)
    for directory in sorted((data / 'bronze').iterdir()):
        if directory.is_dir() and not directory.name.startswith('.'):
            load_bronze(directory.name, data)
    for directory in sorted((data / 'silver').iterdir()):
        if directory.is_dir() and not directory.name.startswith('.'):
            load_silver(directory.name, data)
    for directory in sorted((data / 'gold').iterdir()):
        if directory.is_dir() and not directory.name.startswith('.'):
            load_gold(int(directory.name), data)
    current = read_json(data / 'current.json')['release']
    if type(current) is not int or current < 1:
        raise ValueError('Current release must be a positive integer')
    release, manifest = load_gold(current, data)
    payload = load_silver(manifest['datasetId'], data)
    directory, source = load_bronze(payload['sourceVersion'], data)
    # Reproduce the selected release in a clean directory, not just validate stored hashes.
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        incoming = root / source['originalName']
        incoming.write_bytes((directory / 'source.odt').read_bytes())
        ingest(incoming, payload['sourceVersion'], root)
        dataset = silver(payload['sourceVersion'], root)
        if dataset != manifest['datasetId']:
            raise ValueError('Current Silver was generated with different rules; create a new dataset/release')
        gold(dataset, release['version'], release['updatedAt'], root)
        rebuilt, rebuilt_manifest = load_gold(current, root)
        if rebuilt != release or rebuilt_manifest != manifest:
            raise ValueError('Current Gold release is not reproducible')
    export_seed(release, check=True)
    logs.emit('layers.check.succeeded', releaseVersion=current, hymnCount=len(release['hymns']))
    print(f'All stored layers valid; current release {current} reproduced; offline seed matches')
