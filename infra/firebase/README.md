# Firebase

Este diretório contém as regras de segurança e os índices do Firestore, além da
versão do Firebase CLI usada pelos comandos locais.

O `firebase.json` permanece na raiz do monorepo: ele define a raiz do projeto
Firebase e referencia `apps/mobile/dist` para Hosting e os arquivos deste diretório
para Firestore. O CLI exige que o diretório de publicação esteja dentro dessa raiz.
`.firebaserc`, também na raiz, define o projeto padrão `hinario-idc`.

## Preparação e validação

Requisitos: Node 24, pnpm do workspace e Java 21 para o emulador Firestore.
Se a dependência nativa `re2` não tiver binário para sua plataforma, a instalação
precisa de Python 3, `make` e compilador C++.

Na raiz do repositório:

```bash
corepack pnpm install --frozen-lockfile
corepack pnpm build
corepack pnpm infra:check
corepack pnpm infra:test
```

`infra:check` usa o Firebase CLI para conferir os caminhos das regras, índices e
build do Hosting. `infra:test` inicia os emuladores, verifica as rotas SPA, testa
leitura pública de hinos/metadados e rejeição de gravações sem autenticação, e
encerra os processos ao finalizar. O projeto de testes é `demo-hinario-idc`.
O download inicial do emulador Firestore requer acesso a `storage.googleapis.com`.

Para executar somente a verificação do Hosting:

```bash
corepack pnpm --filter @hinario/infra-firebase test:hosting
```

Para manter os emuladores abertos durante desenvolvimento:

```bash
corepack pnpm emulators
```

Hosting usa `127.0.0.1:5000` e Firestore usa `127.0.0.1:8080`.
A aplicação não se conecta automaticamente ao emulador Firestore; os testes
acessam sua API local diretamente.

## Deploy

Com uma identidade Firebase autenticada e acesso ao projeto padrão:

```bash
corepack pnpm deploy:hosting  # build e publicação do site
corepack pnpm deploy:rules    # regras e índices do Firestore
corepack pnpm deploy          # build, Hosting, regras e índices
```

Esses comandos utilizam o CLI fixado neste workspace. Os workflows de Hosting
leem o `firebase.json` da raiz e usam o projeto `hinario-idc` explicitamente.
A publicação dos documentos dos hinos usa o workflow próprio da
[pipeline](../../apps/hymns-pipeline/README.md).
