"""Immutable v3 reference, independent of the working editorial head/current release."""
from pathlib import Path
import shutil
from hymns_pipeline.storage import DATA


def copy_baseline(target):
    target=Path(target);target.mkdir(parents=True)
    for layer in ('bronze','silver'):
        shutil.copytree(DATA/layer,target/layer)
    shutil.copytree(DATA/'gold/3',target/'gold/3')
    (target/'current.json').write_text('{"release":3}\n')
    return target
