# Logs e diagnóstico

O sistema registra eventos operacionais com campos permitidos por evento. Não há
envio de telemetria para um serviço externo. O app usa o console, a pipeline usa
`stderr` e o container web usa os streams padrão do Docker.

## Ambientes e níveis

| Componente | Desenvolvimento | Testes | Produção |
| --- | --- | --- | --- |
| App Vue/Vite | `debug` | `info` | `info` |
| Pipeline Python | `DEBUG` | `INFO` | `INFO` |

O nível mínimo permite os eventos de maior severidade: `debug`, `info`, `warn`,
`error`. A filtragem nunca desativa a sanitização.

### Aplicativo

O ambiente vem do Vite: modo `test`, servidor de desenvolvimento ou build de
produção. `VITE_LOG_LEVEL` permite escolher `debug`, `info`, `warn` ou `error`
sem depender do ambiente. Uma configuração inválida gera um aviso sem repetir seu
valor e utiliza o padrão do ambiente.

```bash
VITE_LOG_LEVEL=warn corepack pnpm dev
VITE_LOG_LEVEL=debug corepack pnpm build
```

Variáveis `VITE_*` são incorporadas ao JavaScript durante o build. O Dockerfile web
aceita `--build-arg VITE_LOG_LEVEL=info` (padrão). Alterar uma variável no container
Nginx já iniciado não reconfigura os logs do aplicativo. Nos workflows de Hosting,
o nível de build está definido explicitamente como `info`.

O pacote `@hinario/observability` oferece o catálogo de eventos, filtragem,
normalização de erros e saída JSON para o app e sua integração Firebase. Cada
carregamento tem um `sessionId` aleatório, mantido somente em memória. Operações
como inicialização e sincronização têm `operationId` próprio e duração.

São registrados inicialização, carregamento do seed/índice, operações de
persistência, sincronização e falhas de compartilhamento. Ausência de Firebase,
modo offline, indisponibilidade de plugins e fallback de compartilhamento são
eventos de diagnóstico. Cancelar o compartilhamento não gera erro.

Erros capturados são registrados uma vez por objeto de exceção, incluindo os
handlers globais de Vue, `error` e `unhandledrejection`. Os handlers não exibem
mensagens brutas; erros do Vue continuam seguindo o tratamento da aplicação.
O funcionamento offline e os fallbacks são preservados.

### Pipeline Python

O ambiente é definido por `APP_ENV=development|test|production`, com `production`
como padrão quando a variável estiver ausente. A precedência do nível é:

```text
--log-level → LOG_LEVEL → padrão de APP_ENV
```

São aceitos `DEBUG`, `INFO`, `WARN`, `ERROR`, sem distinção entre maiúsculas e
minúsculas. A opção da CLI funciona antes ou depois do subcomando:

```bash
APP_ENV=development python apps/hymns-pipeline/run.py check
APP_ENV=production LOG_LEVEL=INFO python apps/hymns-pipeline/run.py check
python apps/hymns-pipeline/run.py transform --source-version sv-001 --log-level DEBUG
```

Configurações inválidas encerram o comando com um evento sanitizado. Argumentos
inválidos retornam código 2; falhas da operação retornam código 1.

Os eventos JSON usam o módulo padrão `logging` e incluem timestamp UTC, nível,
ambiente, componente, evento, `runId` e contexto permitido. O `runId` é gerado a
cada execução. Etapas incluem hashes de linhagem, versões, contagens e duração,
sem modificar os artefatos medallion.

Os logs ficam em `stderr`; `stdout` contém os resultados dos comandos:

- `ingest` e `release`: diretório produzido.
- `transform`: identificador do dataset, em uma única linha.
- `publish`: resumo JSON somente após a conclusão, simulação ou confirmação de no-op.
- `validate`, `seed` e `check`: confirmação textual.

```bash
python apps/hymns-pipeline/run.py transform --source-version sv-001 \
  > dataset-id.txt 2> events.jsonl
```

Publicações distinguem `planned`, `started`, `succeeded`, `simulated`, `unchanged`,
`failed` e `outcome_unknown`. `succeeded` só é emitido após o retorno do commit.
Erros de transporte, respostas 5xx/408 ou respostas inválidas durante o commit
podem deixar o resultado desconhecido; consulte o banco e refaça a simulação antes
de tentar novamente. Erros de planejamento e conflitos HTTP são registrados como
falhas, sem confirmar que houve publicação.

O Dockerfile Python usa `APP_ENV=production`; substitua a configuração em execução
com `docker run -e APP_ENV=development -e LOG_LEVEL=DEBUG ...`.

## Privacidade e campos permitidos

Os loggers não serializam objetos arbitrários. Somente nomes de evento conhecidos
e os campos previstos no catálogo podem ser emitidos. Tipos e valores são
validados antes da serialização, inclusive em debug.

Não são registrados mensagens brutas de exceções, stacks com dados, letras,
favoritos, conteúdo compartilhado, credenciais, cabeçalhos ou URLs completas.
Erros usam tipos/códigos conhecidos; validações de contrato podem indicar o
caminho no schema. `sourceVersion` e `projectId` são identificadores operacionais:
use nomes de edições e projetos, nunca dados privados nesses identificadores.

Resultados explícitos da CLI, relatórios de dados e saída de ferramentas externas
não são eventos de telemetria. O JSON de resultado de `publish`, por exemplo,
contém IDs públicos de hinos afetados. Bibliotecas, navegador, Firebase CLI e Docker
podem emitir seus próprios diagnósticos fora dos loggers da aplicação.

## Nginx e requisições

O access log do container web é JSON em `stdout`. Inclui horário, status, método,
duração em segundos, bytes enviados e `requestId` gerado pelo Nginx. Esse ID é
retornado no cabeçalho `X-Request-ID`, inclusive em respostas 404, e não utiliza um
ID arbitrário enviado pelo cliente.

O caminho é limitado às categorias `/`, `/hymn`, `/favorites`, `/settings`,
`/assets/*` e `/other`. Query strings, caminhos arbitrários, IPs, cookies,
autorização, referer e corpo não são incluídos nesse access log.

O error log nativo do Nginx permanece **textual em `stderr`, a partir de `warn`**.
Ele pode incluir detalhes de requisições e não passa pelo sanitizador da aplicação.
A ausência de arquivos não é registrada nesse stream (`log_not_found off`), mas
seu status continua no access log. Exigências de sanitização integral do error log
precisam de um coletor/processador próprio. Mensagens de startup da imagem também
não usam o schema de eventos.

Essa configuração se aplica ao container. O Firebase Hosting usa os recursos de
logging da plataforma e não lê a configuração do Nginx.

## CI, retenção e verificação

Os workflows Python definem ambiente e nível explicitamente. O CI testa os loggers,
reproduz as camadas e registra um resumo seguro no GitHub Actions. Somente o JSONL
do comando `check` do próprio CI é guardado como artifact, com retenção de três
dias. Logs reais de dispositivos e de publicação não são anexados como artifacts.
A retenção dos logs normais do Actions segue as configurações do repositório.

```bash
corepack pnpm logs:test
python -m unittest discover -s apps/hymns-pipeline/tests -v
python -m unittest discover -s infra/observability/tests -v
```

As verificações cobrem níveis, sanitização, correlação, falhas de publicação,
stdout da CLI e resumos sem conteúdo arbitrário. O smoke test do container web
verifica também `X-Request-ID`. Para consultar os streams de uma imagem em execução:

```bash
docker logs <nome-do-container>
```

Sem um coletor remoto, falhas em dispositivos de usuários não são centralizadas.
A escolha de um serviço, retenção e política de coleta deve ser feita antes de
adicionar esse destino. Não há persistência automática dos logs do app no dispositivo.

Operações editoriais registram `editorial.change.prepared` com o tipo de operação
(`create`, `update`, `delete`, `source`, `remote`) e hash da revisão. Motivos,
letras, títulos e snapshots não entram na telemetria. Resultados explícitos de
CRUD, consultas e relatórios são JSON em stdout e podem conter conteúdo do acervo.
Divergências de conteúdo remoto usam o código seguro `remote_content_drift`.
