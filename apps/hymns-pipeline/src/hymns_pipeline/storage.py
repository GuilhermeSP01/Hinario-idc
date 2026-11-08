"""Deterministic files and immutable, content-checked layer directories."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[4]
APP = ROOT / 'apps/hymns-pipeline'
DATA = APP / 'data'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def identifier(value):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}', value):
        raise ValueError('Invalid version/dataset identifier')
    return value


def immutable_directory(target, files):
    """A repeated write must be byte-identical; never overwrite an older artifact."""
    target = Path(target)
    if target.exists():
        actual = {str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()}
        if actual != files:
            raise ValueError(f'Immutable artifact differs: {target}')
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.writing-', dir=target.parent))
    try:
        for name, content in files.items():
            (temp / name).write_bytes(content)
        try:
            temp.rename(target)
        except OSError:
            if target.exists():
                return immutable_directory(target, files)
            raise
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return target
