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
    parser = SafeArgumentParser(
        description='Pipeline de hinos: camadas medallion, edição local e publicação no Firestore.',
        epilog='Use help <comando> ou <comando> --help para consultar detalhes. '
               'Guia: apps/hymns-pipeline/EDITORIAL.md',
    )
    parser.add_argument('--log-level', type=str.upper, choices=logs.LEVELS, default=None)
    parser.add_argument('--data-dir', type=Path, default=DATA)
    descriptions = {
        'check': 'Valida todas as camadas e revisões, reproduz a release atual e confere o seed offline.',
        'ingest': 'Armazena um documento ODT e seu hash como versão imutável na camada bronze.',
        'transform': 'Extrai e padroniza os hinos de bronze, gerando um dataset silver imutável.',
        'release': 'Gera uma release gold imutável a partir de uma revisão editorial.',
        'source-reconcile': 'Relata ou aplica decisões explícitas de associação entre uma fonte silver e os IDs dos hinos.',
        'list': 'Consulta os hinos ativos no Firestore, sem gravar dados.',
        'get': 'Consulta um hino pelo ID no Firestore, incluindo tombstones, sem gravar dados.',
        'reconcile': 'Relata divergências no Firestore ou registra localmente decisões revisadas, sem publicar.',
        'create': 'Cria localmente um hino com UUID4 e registra uma revisão editorial.',
        'update': 'Atualiza campos de um hino local, preservando seu ID e registrando uma revisão.',
        'delete': 'Remove um hino do acervo local ativo e aposenta seu ID; a publicação gera o tombstone.',
        'validate': 'Valida uma release gold armazenada e a integridade de sua linhagem.',
        'seed': 'Gera o seed TypeScript offline a partir de uma release gold, ou confere o arquivo existente.',
        'publish': 'Publica atomicamente uma release no Firestore após verificar versão e divergências remotas.',
    }
    commands = parser.add_subparsers(dest='command', required=True)
    def add_command(name):
        return commands.add_parser(name, help=descriptions[name], description=descriptions[name])

    add_command('check')
    p = add_command('ingest')
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--source-version', required=True)
    p = add_command('transform')
    p.add_argument('--source-version', required=True)
    p = add_command('release')
    release_input = p.add_mutually_exclusive_group(required=True)
    release_input.add_argument('--dataset')
    release_input.add_argument('--revision')
    p.add_argument('--version', required=True, type=int)
    p.add_argument('--updated-at', required=True)
    p = add_command('source-reconcile')
    p.add_argument('--dataset', required=True)
    p.add_argument('--file', type=Path)
    p.add_argument('--reason')
    for command in ('list', 'get', 'reconcile'):
        p = add_command(command)
        p.add_argument('--project', required=True)
        if command == 'get': p.add_argument('--id', required=True)
        if command == 'reconcile':
            p.add_argument('--file', type=Path)
            p.add_argument('--reason')
    for command in ('create', 'update', 'delete'):
        p = add_command(command)
        p.add_argument('--reason', required=True)
        if command != 'create': p.add_argument('--id', required=True)
        if command != 'delete': p.add_argument('--file', type=Path, required=command == 'create')
        if command == 'update':
            p.add_argument('--title')
            p.add_argument('--number', type=int)
    for command in ('validate', 'seed', 'publish'):
        p = add_command(command)
        p.add_argument('--release', type=int, required=True)
        if command == 'seed':
            p.add_argument('--check', action='store_true')
        if command == 'publish':
            p.add_argument('--project', required=True)
            p.add_argument('--dry-run', action='store_true')
            p.add_argument('--expected-remote-version', type=int, required=True)
    argument_help = {
        'log_level': 'Nível de logging; também configurável por LOG_LEVEL.',
        'data_dir': 'Diretório de dados da pipeline; informe antes do subcomando.',
        'source': 'Caminho do documento ODT de entrada.',
        'source_version': 'Identificador da versão bronze, por exemplo sv-002.',
        'dataset': 'Identificador do dataset silver; em release, somente para reprodução histórica.',
        'revision': 'Hash SHA-256 da revisão editorial usada para gerar gold.',
        'version': 'Número inteiro crescente da nova release gold.',
        'updated_at': 'Timestamp explícito da release em ISO 8601, por exemplo 2026-11-08T12:00:00Z.',
        'project': 'ID explícito do projeto Firebase; acesso remoto usa ADC.',
        'id': 'ID permanente do hino, independente do número de exibição.',
        'reason': 'Motivo editorial obrigatório para alterações; também exigido ao reconciliar com --file.',
        'title': 'Novo título do hino; não pode repetir o campo do arquivo.',
        'number': 'Novo número de exibição (1 a 65535); renumerar pode invalidar links antigos.',
        'release': 'Número da release gold armazenada.',
        'check': 'Confere o seed existente sem sobrescrevê-lo.',
        'dry_run': 'Simula a publicação com leituras remotas, sem enviar gravações.',
        'expected_remote_version': 'Versão esperada no Firestore; alterações concorrentes bloqueiam a publicação.',
    }
    file_help = {
        'create': 'Arquivo JSON com number, title e sections; identidade e metadados são gerenciados pelo sistema.',
        'update': 'Arquivo JSON parcial com number, title e/ou sections; sections substitui todas as seções.',
        'source-reconcile': 'Arquivo JSON de decisões explícitas; sem --file, apenas gera o relatório.',
        'reconcile': 'Arquivo JSON com hashes e decisões local/remote; sem --file, apenas gera o relatório.',
    }
    examples = {
        'create': 'create --file /tmp/hino.json --reason "Incluir hino aprovado"',
        'update': 'update --id 145 --file /tmp/correcao.json --reason "Corrigir letra"',
        'release': 'release --revision <sha256> --version 4 --updated-at 2026-11-08T12:00:00Z',
        'publish': 'publish --release 4 --project hinario-idc --expected-remote-version 3 --dry-run',
    }
    for name, subparser in commands.choices.items():
        subparser.description = descriptions[name]
        subparser.epilog = ('Exemplo: python apps/hymns-pipeline/run.py ' + examples[name]
                            if name in examples else 'Guia: apps/hymns-pipeline/EDITORIAL.md')
    help_parser = commands.add_parser('help', help='Mostra a ajuda geral ou de um comando.',
                                      description='Consulta sintaxe e finalidade dos comandos sem executar operações.')
    help_parser.add_argument('topic', nargs='?', choices=tuple(descriptions), help='Comando cuja ajuda será exibida.')
    for subparser in commands.choices.values():
        subparser.add_argument('--log-level', type=str.upper, choices=logs.LEVELS, default=argparse.SUPPRESS)
    for current in (parser, *commands.choices.values()):
        for action in current._actions:
            if action.dest in argument_help:
                action.help = argument_help[action.dest]
            elif action.dest == 'file':
                action.help = file_help[current.prog.split()[-1]]
    args = parser.parse_args()
    if args.command == 'help':
        (commands.choices[args.topic] if args.topic else parser).print_help()
        return
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
