# Hinário IDC

Monorepo do ecossistema **Hinário IDC**, organizado com `pnpm workspaces` para suportar o aplicativo mobile (Vue 3 + Vite + Capacitor) e futuras camadas de edição administrativa e análise de dados.

## Estrutura do Repositório

- **`packages/core` (`@hinario/core`)**: Modelos de domínio (`Hymn`, `HymnSection`, `HinarioMetadata`), normalização de texto sem acentos e motor de busca indexada em memória/cache (`MiniSearch`).
- **`packages/firebase` (`@hinario/firebase`)**: Integração modular com o Cloud Firestore, sincronização delta por versão (`version > localVersion`) e snapshot inicial de hinos (seed offline).
- **`apps/mobile` (`@hinario/mobile`)**: Aplicativo mobile com Vue 3, Vite, Tailwind CSS, Pinia, Dexie.js (IndexedDB) e Capacitor (Android/iOS).
- **`tools/`**: Scripts utilitários, ETL de hinos e futuros projetos de análise de dados.

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
