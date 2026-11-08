# Hinário IDC

Monorepo do ecossistema **Hinário IDC**, organizado com `pnpm workspaces` para suportar o aplicativo mobile (Vue 3 + Vite + Capacitor).

## Estrutura do Repositório

- **`packages/core` (`@hinario/core`)**: Reexportação dos contratos de domínio (`Hymn`, `HymnSection`, `HinarioMetadata`), normalização de texto sem acentos e motor de busca indexada em memória/cache (`MiniSearch`).
- **`packages/firebase` (`@hinario/firebase`)**: Integração modular com o Cloud Firestore, sincronização delta por versão (`version > localVersion`) e snapshot inicial de hinos (seed offline).
- **`apps/mobile` (`@hinario/mobile`)**: Aplicativo mobile com Vue 3, Vite, Tailwind CSS, Pinia, Dexie.js (IndexedDB) e Capacitor (Android/iOS).
- **`apps/hymns-pipeline/`**: Pipeline Python medallion: fontes versionadas em bronze, hinos padronizados em silver e releases do Firestore em gold.
- **`packages/hymns-contracts/`**: Contratos JSON Schema compartilhados e tipos TypeScript gerados.
- **`tools/`**: Utilitários de assets do aplicativo.
- **`infra/firebase/`**: Regras, índices, ferramentas e validação local do Firebase.
- **`infra/docker/`**: Instruções de execução e smoke test dos containers.

## Configuração do Firebase

Copie o arquivo `apps/mobile/.env.example` para `apps/mobile/.env` e preencha as variáveis do seu projeto Firebase:

```env
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
```

> Enquanto o `.env` não estiver preenchido ou o dispositivo estiver offline, o aplicativo opera normalmente utilizando o snapshot inicial embutido e o banco local IndexedDB.

## Infraestrutura Firebase

As regras e os índices do Firestore estão em [`infra/firebase/`](infra/firebase/README.md).
O `firebase.json` e o `.firebaserc` ficam na raiz para definir o projeto e os caminhos
do Hosting. O Firebase CLI é uma dependência de desenvolvimento do workspace de
infraestrutura, com versão fixada no lockfile.

Após gerar o build, `corepack pnpm infra:check` valida os caminhos da configuração.
`corepack pnpm infra:test` executa os testes dos emuladores de Hosting e Firestore.

## Deploy no Firebase Hosting

- Abra um PR para `main` a partir de uma branch do próprio repositório para receber a URL de prévia em um comentário. Novos commits atualizam a prévia. Ela expira sete dias após o último deploy.
- PRs de forks executam o build sem publicar uma prévia.
- Todo push para `main`, inclusive o gerado por um merge, publica o build web no canal de produção. Se o deploy deve acontecer somente após revisão, configure a proteção de `main` para exigir PR e aprovação.

Em **Settings → Secrets and variables → Actions**, cadastre as seis variáveis `VITE_FIREBASE_*` de `apps/mobile/.env.example` na aba **Variables**, com os valores do app web do projeto `hinario-idc`. As prévias e a produção usam o Firestore configurado nessas variáveis.

Na aba **Secrets**, cadastre o JSON da conta de serviço de deploy como `FIREBASE_SERVICE_ACCOUNT_HINARIO_IDC`. Siga a [configuração manual da conta de serviço](https://github.com/FirebaseExtended/action-hosting-deploy/blob/main/docs/service-account.md#manually-configure-the-service-account) para provisionar a chave. Também é possível usar `firebase init hosting:github` para cadastrar o secret automaticamente. Nesse caso, mantenha apenas os workflows deste repositório para evitar deploys duplicados.

## Comandos Principais

```bash
# Instalar dependências do workspace
corepack pnpm install

# Rodar o app mobile em modo de desenvolvimento
corepack pnpm dev

# Gerar build de produção do app mobile
corepack pnpm build

# Verificar tipos em todos os pacotes
corepack pnpm typecheck
```

## Pipeline de dados dos hinos

A aplicação [`apps/hymns-pipeline`](apps/hymns-pipeline/README.md) extrai,
padroniza e publica os hinos. Seus dados são organizados em três camadas:

- **Bronze:** documentos ODT originais, versionados com manifesto e hash de integridade.
- **Silver:** hinos extraídos e padronizados, com relatório das decisões editoriais.
- **Gold:** releases no formato do Firestore, usadas também para gerar o seed offline.

A ingestão, a geração do seed e a publicação no banco são etapas independentes.

Consulte o README da pipeline para preparar o venv Python, processar novas edições,
gerar releases e configurar a publicação manual via identidade federada.

```bash
# Com o venv da pipeline ativado:
corepack pnpm hymns:test
corepack pnpm hymns:check
corepack pnpm contracts:check
```

O processamento usa os comandos `hymns:ingest`, `hymns:transform`,
`hymns:release` e `hymns:validate`. A geração do seed usa `hymns:seed`,
e a publicação no Firestore usa `hymns:publish`.

## Docker

O app web e a pipeline possuem imagens independentes. Execute os builds a partir
da raiz do monorepo:

```bash
docker build -f apps/mobile/Dockerfile -t hinario-web .
docker run --rm -p 8090:8080 hinario-web

docker build -f apps/hymns-pipeline/Dockerfile -t hinario-pipeline .
docker run --rm hinario-pipeline
```

A imagem web serve o build estático; a imagem da pipeline executa a verificação
das camadas por padrão. Consulte [os comandos de Docker](infra/docker/README.md)
para desenvolvimento com Vite, configurações Firebase, persistência de dados e
credenciais em execução.
