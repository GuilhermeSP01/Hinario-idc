"""CLI: every stage is explicit; extraction never publishes or overwrites the seed."""
import argparse
import json
from pathlib import Path
from time import perf_counter
from . import observability as logs
from .layers import ingest, silver, gold, load_gold
from .seed import export_seed
from .storage import DATA


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default errors echo invalid argument values; keep those out of logs.
        logs.configure('INFO', environment='production')
        logs.emit('pipeline.configuration.failed', level='error', errorCode='invalid_arguments')
        self.exit(2)


def main():
    parser = SafeArgumentParser(description=__doc__)
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
    release_input = p.add_mutually_exclusive_group(required=True)
    release_input.add_argument('--dataset')
    release_input.add_argument('--revision')
    p.add_argument('--version', required=True, type=int)
    p.add_argument('--updated-at', required=True)
    p = commands.add_parser('source-reconcile')
    p.add_argument('--dataset', required=True)
    p.add_argument('--file', type=Path)
    p.add_argument('--reason')
    for command in ('list', 'get', 'reconcile'):
        p = commands.add_parser(command)
        p.add_argument('--project', required=True)
        if command == 'get': p.add_argument('--id', required=True)
        if command == 'reconcile':
            p.add_argument('--file', type=Path)
            p.add_argument('--reason')
    for command in ('create', 'update', 'delete'):
        p = commands.add_parser(command)
        p.add_argument('--reason', required=True)
        if command != 'create': p.add_argument('--id', required=True)
        if command != 'delete': p.add_argument('--file', type=Path, required=command == 'create')
        if command == 'update':
            p.add_argument('--title')
            p.add_argument('--number', type=int)
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
        if args.command in ('create', 'update', 'delete'):
            from .editorial import mutate
            from .storage import read_json
            payload = read_json(args.file) if getattr(args, 'file', None) else {}
            if not isinstance(payload, dict): raise ValueError('Expected JSON object')
            for key in ('title', 'number'):
                value = getattr(args, key, None)
                if value is not None:
                    if key in payload: raise ValueError('Field supplied both in file and flags')
                    payload[key] = value
            result = mutate(args.command, hymn_id=getattr(args, 'id', None), payload=payload, reason=args.reason, data=args.data_dir)
            logs.emit('editorial.change.prepared', operation=args.command, revisionId=result['revision'])
            print(json.dumps(result, ensure_ascii=False))
        elif args.command in ('list', 'get', 'reconcile'):
            from .remote import read_remote, reconciliation_report, reconcile_remote
            from .storage import read_json
            if args.command == 'reconcile':
                if args.file and not args.reason: raise ValueError('A reason is required to reconcile')
                result = reconcile_remote(args.project,read_json(args.file),args.reason,args.data_dir) if args.file else reconciliation_report(args.project,args.data_dir)
            else:
                result = read_remote(args.project, getattr(args,'id',None))
            if args.command == 'reconcile' and args.file:
                logs.emit('editorial.change.prepared', operation='remote', revisionId=result['revision'])
            print(json.dumps(result,ensure_ascii=False))
        elif args.command == 'source-reconcile':
            from .source_reconciliation import reconcile_source, source_report
            from .storage import read_json
            if args.file and not args.reason: raise ValueError('A reason is required to reconcile')
            result = reconcile_source(args.dataset, read_json(args.file), args.reason, args.data_dir) if args.file else source_report(args.dataset,args.data_dir)
            if args.file: logs.emit('editorial.change.prepared', operation='source', revisionId=result['revision'])
            print(json.dumps(result, ensure_ascii=False))
        elif args.command == 'check':
            from .check import check
            check(args.data_dir)
        elif args.command == 'ingest':
            print(ingest(args.source, args.source_version, args.data_dir))
        elif args.command == 'transform':
            print(silver(args.source_version, args.data_dir))
        elif args.command == 'release':
            if args.revision:
                from .editorial import release_revision
                print(release_revision(args.revision, args.version, args.updated_at, args.data_dir))
            else:
                from .storage import read_json
                if args.version > read_json(args.data_dir / 'current.json')['release']:
                    raise ValueError('New releases require an editorial revision; reconcile new sources first')
                print(gold(args.dataset, args.version, args.updated_at, args.data_dir))
        else:
            release, manifest = load_gold(args.release, args.data_dir)
            if args.command == 'seed':
                export_seed(release, args.check)
            elif args.command == 'publish':
                from .firestore import publish
                from .remote import publication_baseline
                baseline=publication_baseline(release,manifest,args.project,args.data_dir)
                summary = publish(release, manifest, args.project, args.expected_remote_version, args.dry_run, baseline=baseline)
                print(json.dumps(dict(summary, project=args.project, dryRun=args.dry_run)))
            if args.command != 'publish':
                print(f'{args.command}: release {args.release} OK')
        logs.emit('pipeline.command.succeeded', durationMs=logs.elapsed(start))
    except Exception as error:
        if not getattr(error, 'logged', False):
            logs.emit('pipeline.command.failed', level='error', durationMs=logs.elapsed(start), **logs.error_context(error))
        parser.exit(1)
