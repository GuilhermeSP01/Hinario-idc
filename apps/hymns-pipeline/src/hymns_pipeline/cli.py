"""CLI: every stage is explicit; extraction never publishes or overwrites the seed."""
import argparse
import json
from pathlib import Path
from time import perf_counter
from . import observability as logs
from .layers import ingest, silver, gold, load_gold
from .seed import export_seed
from .storage import DATA


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log-level', type=str.upper, choices=logs.LEVELS, default=None)
    parser.add_argument('--data-dir', type=Path, default=DATA)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('check')
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
    for subparser in commands.choices.values():
        subparser.add_argument('--log-level', type=str.upper, choices=logs.LEVELS, default=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        logs.configure(args.log_level, command=args.command)
    except ValueError:
        logs.configure('INFO', environment='production', command=args.command)
        logs.emit('pipeline.configuration.failed', level='error', errorCode='invalid_configuration')
        parser.exit(1)
    start = perf_counter()
    logs.emit('pipeline.command.started')
    try:
        if args.command == 'check':
            from .check import check
            check(args.data_dir)
        elif args.command == 'ingest':
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
                summary = publish(release, manifest, args.project, args.expected_remote_version, args.dry_run)
                print(json.dumps(dict(summary, project=args.project, dryRun=args.dry_run)))
            if args.command != 'publish':
                print(f'{args.command}: release {args.release} OK')
        logs.emit('pipeline.command.succeeded', durationMs=logs.elapsed(start))
    except Exception as error:
        if not getattr(error, 'logged', False):
            logs.emit('pipeline.command.failed', level='error', durationMs=logs.elapsed(start), **logs.error_context(error))
        parser.exit(1)
