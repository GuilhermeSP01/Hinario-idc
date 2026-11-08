# Edição de hinos

Execute os comandos na raiz do monorepo, com o venv e dependências descritos no
[README](README.md). Edições são locais e auditáveis; somente `hymns:publish`
grava no Firestore. Bronze e silver permanecem intactos.

## Criar, atualizar e remover

Crie um arquivo JSON UTF-8 com o conteúdo completo do novo hino:

```json
{
  "number": 464,
  "title": "Novo Hino",
  "sections": [
    {"type": "verse", "number": 1, "lines": ["Primeiro verso", "Segundo verso"]},
    {"type": "chorus", "lines": ["Coro"]}
  ]
}
```

```bash
corepack pnpm hymns:create --file /tmp/new-hymn.json --reason "Incluir hino aprovado"
corepack pnpm hymns:update --id 145 --title "Rocha Eterna" --number 464 --reason "Revisar cabeçalho"
corepack pnpm hymns:update --id 145 --file /tmp/correction.json --reason "Corrigir letra"
corepack pnpm hymns:delete --id 145 --reason "Remover do acervo ativo"
```

Na atualização, o arquivo aceita qualquer subconjunto de `number`, `title` e
`sections`. Campos omitidos são preservados. `sections` substitui todas as seções,
sem mesclar por posição. É possível combinar arquivo e flags para campos distintos;
repetir um campo nas duas entradas é erro. Campos `id`, `version`, `updatedAt` e
`deleted` são gerenciados pelo sistema. Mudanças vazias, números repetidos, IDs
inexistentes ou entradas inválidas são rejeitados sem criar revisão.

O ID criado é UUID4; IDs removidos ficam aposentados e não podem ser reutilizados.
Atualizações preservam o ID. Números devem estar entre 1 e 65535. Renumerações
preservam favoritos e repertórios, mas links compartilhados usam números: um link
antigo pode apontar para outro hino ou deixar de funcionar.

Cada operação exige um motivo e retorna o hash da revisão, ID e comparação antes/
depois em `stdout`. Motivos e letras não são enviados aos logs. Esses resultados e
os arquivos editoriais contêm conteúdo explícito do acervo; revise-os como dados.

## Revisões e releases

`data/editorial/revisions/<sha256>/revision.json` contém snapshots imutáveis,
operação, motivo, revisão anterior, mapeamento da fonte e IDs aposentados.
`data/editorial/head.json` seleciona a revisão de trabalho. O primeiro comando de
edição inicializa a base a partir de `data/current.json`. Uma trava local impede
escritores simultâneos. Não edite snapshots ou o ponteiro manualmente.

```bash
corepack pnpm hymns:release --revision <sha256> --version 4 --updated-at 2026-11-08T12:00:00Z
corepack pnpm hymns:validate --release 4
corepack pnpm hymns:seed --release 4
```

Escolha uma versão superior à base e ao checkpoint remoto aceito. Atualize
`data/current.json` para a release escolhida, execute `hymns:check` e revise gold,
seed e revisões no PR. O check verifica hashes, reproduz as operações e reconstrói
a release. Uma release existente não é sobrescrita. Após selecionar a release
construída a partir do head, a próxima edição usa essa release como base.
`release --dataset` atende somente à reprodução das releases históricas; novas
releases usam `--revision`.

## Consultar e reconciliar o Firestore

Consultas usam ADC e não escrevem no banco:

```bash
corepack pnpm hymns:list --project hinario-idc
corepack pnpm hymns:get --id 145 --project hinario-idc
corepack pnpm hymns:reconcile --project hinario-idc > /tmp/remote-report.json
```

`list` retorna hinos ativos; `get` permite inspecionar também tombstones.
A publicação compara o estado completo com a base conhecida, inclusive metadados e
exclusões. Alterações externas bloqueiam a publicação mesmo sem mudança de versão.
Timestamps isolados não são divergências; uma base histórica pode não ter
`releaseHash`. Nunca contorne o bloqueio sobrescrevendo a release.

O relatório contém `expectedRevision`, `snapshotHash`, snapshot e diferenças.
Prepare um arquivo de decisões usando os hashes exatos e uma decisão para cada
ID divergente:

```json
{
  "expectedRevision": "<hash-do-head>",
  "snapshotHash": "<hash-do-relatório>",
  "resolutions": [{"id": "145", "choice": "local"}],
  "acceptMetadata": false
}
```

`choice: "remote"` importa o conteúdo remoto (ou aceita sua ausência/exclusão).
`local` mantém a decisão editorial local, inclusive ausência de um ID desconhecido.
Se os metadados divergirem, sua aceitação exige `acceptMetadata: true`.

```bash
corepack pnpm hymns:reconcile --project hinario-idc --file /tmp/remote-decisions.json --reason "Revisão das alterações externas"
```

A operação relê o banco, rejeita relatório desatualizado e registra um checkpoint
específico do projeto. Não publica. Gere uma nova release da revisão retornada e
simule a publicação com `--expected-remote-version` correto. Outra alteração remota
invalida o checkpoint e exige nova revisão. A publicação usa commit atômico e
precondições para rejeitar concorrência; após timeout, consulte o estado antes de
repetir. Veja os limites e autenticação no README.

## Incorporar uma nova fonte

Depois de ingestão e transformação, gere o relatório de mapeamento:

```bash
corepack pnpm hymns:source-reconcile --dataset <dataset-id> > /tmp/source-report.json
```

Não há associação automática por título ou número. Revise cada `sourceOrdinal`
(posição estável dentro daquele dataset) e decida explicitamente:

```json
{
  "expectedRevision": "<hash-do-head>",
  "assignments": [
    {"sourceOrdinal": 1, "id": "001", "use": "source"},
    {"sourceOrdinal": 2, "id": "002", "use": "local"},
    {"sourceOrdinal": 3, "new": true},
    {"sourceOrdinal": 4, "omit": true}
  ],
  "remaining": [{"id": "003", "action": "keep"}]
}
```

Inclua todas as entradas do dataset e todos os IDs ativos não mapeados em
`remaining` (`keep` ou `delete`). `source` usa o conteúdo silver; `local` preserva
correções locais. `new` gera um UUID4; `omit` exclui a entrada da fonte. O exemplo
mostra o formato: a quantidade real de decisões depende do relatório.

```bash
corepack pnpm hymns:source-reconcile --dataset <dataset-id> --file /tmp/source-decisions.json --reason "Incorporar edição revisada"
```

Revise a revisão resultante antes de gerar gold. Fontes novas não apagam correções
nem alteram identidades sem decisões explícitas.

## Testes e Docker

`hymns:test` testa validação, replay, CRUD, reconciliação e publicação com mocks.
`hymns:browser-test` usa Playwright para verificar IDs renumerados, UUIDs, favoritos,
repertório e links numéricos. Instale Chromium com `pnpm exec playwright install
--with-deps chromium`; `BROWSER_PATH` permite usar um navegador local existente.
`infra:test` inclui integração no emulador Firestore, com projeto `demo-` vazio.
O cliente só aceita `FIRESTORE_EMULATOR_HOST` em localhost/127.0.0.1 e projeto demo.

Na imagem Docker, monte o diretório `data` completo em modo leitura/escrita para
persistir revisões e gold entre comandos. Schemas e regras devem permanecer da
mesma versão do checkout. Veja [Docker](../../infra/docker/README.md). Nenhum
comando editorial exige credenciais; consultas e publicação exigem ADC fora do
emulador.
