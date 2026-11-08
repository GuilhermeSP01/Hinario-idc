"""CLI: every stage is explicit; extraction never publishes or overwrites the seed."""
import argparse
from pathlib import Path
from .layers import ingest, silver, gold, load_gold
from .seed import export_seed
from .storage import DATA


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=DATA)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('ingest')
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--source-version', required=True)
    p = commands.add_parser('transform')
    p.add_argument('--source-version', required=True)
    p = commands.add_parser('release')
    p.add_argument('--dataset', required=True)
    p.add_argument('--version', required=True, type=int)
    p.add_argument('--updated-at', required=True)
    for command in ('validate', 'seed', 'publish'):
        p = commands.add_parser(command)
        p.add_argument('--release', type=int, required=True)
        if command == 'seed':
            p.add_argument('--check', action='store_true')
        if command == 'publish':
            p.add_argument('--project', required=True)
            p.add_argument('--dry-run', action='store_true')
            p.add_argument('--expected-remote-version', type=int, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'ingest':
            print(ingest(args.source, args.source_version, args.data_dir))
        elif args.command == 'transform':
            print(silver(args.source_version, args.data_dir))
        elif args.command == 'release':
            print(gold(args.dataset, args.version, args.updated_at, args.data_dir))
        else:
            release, manifest = load_gold(args.release, args.data_dir)
            if args.command == 'seed':
                export_seed(release, args.check)
            elif args.command == 'publish':
                from .firestore import publish
                publish(release, manifest, args.project, args.expected_remote_version, args.dry_run)
            print(f'{args.command}: release {args.release} OK')
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'Pipeline failed: {error}\n')
