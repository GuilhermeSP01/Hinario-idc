# Containers

Há duas imagens independentes: o aplicativo web em Vue/Vite e a pipeline Python.
Os Dockerfiles ficam junto de cada aplicação. Todos os comandos de build usam a
raiz do monorepo como contexto, para incluir os pacotes compartilhados.

## Aplicativo web

A imagem padrão compila o aplicativo com Node 24 e serve os arquivos estáticos com
Nginx sem privilégios de root, na porta 8080. Rotas SPA retornam `index.html`;
assets inexistentes retornam 404.

```bash
docker build -f apps/mobile/Dockerfile -t hinario-web .
docker run --rm -p 8090:8080 hinario-web
```

As variáveis `VITE_FIREBASE_*` são configurações públicas incorporadas pelo Vite
**durante o build**. Forneça as seis como `--build-arg`, por exemplo:

```bash
docker build -f apps/mobile/Dockerfile -t hinario-web \
  --build-arg VITE_FIREBASE_API_KEY \
  --build-arg VITE_FIREBASE_AUTH_DOMAIN \
  --build-arg VITE_FIREBASE_PROJECT_ID \
  --build-arg VITE_FIREBASE_STORAGE_BUCKET \
  --build-arg VITE_FIREBASE_MESSAGING_SENDER_ID \
  --build-arg VITE_FIREBASE_APP_ID .
```

Nesse exemplo, as variáveis devem estar exportadas no shell. Elas não são chaves
de service account. Variáveis passadas com `docker run -e` não reconfiguram o build
estático. Sem configuração Firebase, o app usa seu seed e armazenamento local.
O arquivo `.env` do host não é incluído na imagem.

Para desenvolvimento com Vite:

```bash
docker build --target development -f apps/mobile/Dockerfile -t hinario-web-dev .
docker run --rm -p 5173:5173 \
  --mount "type=bind,src=$(pwd)/apps/mobile/src,dst=/app/apps/mobile/src" \
  hinario-web-dev
```

O bind mount permite editar o código do app no host com atualização pelo Vite.
Para configurar Firebase nesse modo, acrescente `--env-file apps/mobile/.env` ao
`docker run`. Alterações em dependências ou pacotes compartilhados exigem rebuild
ou mounts específicos. A imagem web não gera APKs nem builds iOS.

## Pipeline

```bash
docker build -f apps/hymns-pipeline/Dockerfile -t hinario-pipeline .
docker run --rm hinario-pipeline
docker run --rm hinario-pipeline validate --release 3
docker run --rm --entrypoint python hinario-pipeline \
  -m unittest discover -s apps/hymns-pipeline/tests -v
```

A execução padrão roda `check`, sem acessar o Firestore. A imagem contém Python
3.12, dependências fixadas, camadas de dados, contratos JSON Schema e seed offline.
Ela executa com um usuário sem privilégios de root e aceita os subcomandos da
[CLI da pipeline](../../apps/hymns-pipeline/README.md).

Para persistir novas fontes e resultados no Linux, execute com seu UID/GID e monte
os dados do checkout, além da pasta externa que contém o documento de entrada:

```bash
docker run --rm --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$(pwd)/apps/hymns-pipeline/data,dst=/app/apps/hymns-pipeline/data" \
  --mount "type=bind,src=/caminho/das/fontes,dst=/input,readonly" \
  hinario-pipeline ingest --source /input/hinario.odt --source-version sv-002
```

Use o mesmo mount de dados em `transform`, `create`, `update`, `delete`,
`source-reconcile`, `reconcile`, `release`, `validate` e `publish`. Edições persistem
em `data/editorial`; monte arquivos JSON de entrada em `/input` e passe `--file`.
O diretório de dados precisa permitir escrita pelo UID escolhido. Para
persistir a geração do seed, monte também `packages/firebase/src/seed` em
`/app/packages/firebase/src/seed`. Sem mounts, alterações ficam no filesystem do
container e são descartadas com `--rm`.

A publicação continua exigindo ADC e permissões no projeto de destino. Credenciais
devem ser fornecidas em execução, por identidade do ambiente ou arquivo montado
somente para leitura, com `GOOGLE_APPLICATION_CREDENTIALS` apontando para esse
arquivo. Não use argumentos de build para credenciais privadas.

## Proxy e certificados

Em ambientes com inspeção HTTPS, o build aceita um bundle de CAs como secret
opcional do BuildKit, preservando a verificação TLS:

```bash
docker build --secret id=proxy_ca,src=/caminho/ca-bundle.pem \
  -f apps/hymns-pipeline/Dockerfile -t hinario-pipeline .
```

A mesma opção funciona no Dockerfile web. O bundle deve incluir as raízes públicas
e a CA do proxy; não é gravado na imagem. Configure o proxy pelo mecanismo padrão
do Docker. Containers que publicam dados também precisam receber a configuração
de proxy/CA em execução conforme seu ambiente.

## Logs e níveis

O build web aceita `--build-arg VITE_LOG_LEVEL=info` (padrão de produção). O target
de desenvolvimento usa o padrão `debug` do Vite, ajustável com `VITE_LOG_LEVEL` em
execução. A imagem Python usa `APP_ENV=production`; `APP_ENV` e `LOG_LEVEL` podem
ser sobrescritos no `docker run`.

Acessos do Nginx são JSON em `stdout`, com `X-Request-ID` nas respostas. Erros
nativos e mensagens de startup usam outro formato. Consulte o [guia de logs](../observability/README.md)
para os campos registrados e as limitações de sanitização desses streams.
