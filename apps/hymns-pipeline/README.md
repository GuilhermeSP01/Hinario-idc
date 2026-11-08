# Pipeline de hinos

Aplicação Python executada a partir do checkout do monorepo. Transforma documentos
ODT em dados validados e reproduzíveis para Firestore e para o seed offline.
Atualmente há um leitor ODT; DOCX é outro formato e requer um leitor próprio.

## Preparação

Requisitos: Python 3.12, Node 24 e o pnpm fixado no `package.json`.
A partir da raiz do repositório:

```bash
python -m venv apps/hymns-pipeline/.venv
source apps/hymns-pipeline/.venv/bin/activate
python -m pip install -r apps/hymns-pipeline/requirements.lock
corepack pnpm install --frozen-lockfile
corepack pnpm hymns:test
corepack pnpm hymns:check
corepack pnpm contracts:check
corepack pnpm --filter @hinario/hymns-contracts validate --all
```

No Windows, ative `.venv\Scripts\Activate.ps1` no PowerShell.
`requirements.txt`/`pyproject.toml` declaram dependências diretas; `requirements.lock`
fixa também as transitivas para instalação e CI. Para atualizar, use um venv limpo,
instale as dependências diretas, regenere o lock com `python -m pip freeze` e teste.
Não é necessário instalar o pacote Python globalmente: os comandos usam `run.py`.

## Camadas e versionamento

```text
data/
├── bronze/<source-version>/    # Documento original + manifest.json com SHA-256
├── silver/<dataset-id>/        # Hinos padronizados + relatório + manifesto
├── gold/<release-version>/     # Documentos finais do banco + manifesto
└── current.json               # Release escolhida para o seed e reprodução no CI
```

Os artefatos das três camadas são versionados no Git para este acervo pequeno.
Os documentos de origem são armazenados diretamente em bronze. A edição
`sv-001` está em `data/bronze/sv-001/source.odt`, com seus bytes originais
preservados e o nome do arquivo registrado no manifesto.
Não há arquivo `latest` mutável nas camadas. Repetir uma etapa é permitido apenas
se produzir os mesmos bytes; uma versão existente nunca é sobrescrita.

Três versões independentes:

- `sourceVersion`: edição do documento; o mesmo documento pode ser reprocessado.
- `rulesHash`: hash do leitor, normalização, transformação e decisões editoriais.
  Participa do identificador silver, derivado do conteúdo completo padronizado.
- `version`: inteiro crescente da release gold, compartilhado pelo banco e seed.

Bronze não sofre limpeza. Silver preserva título original e posição do hino na
sequência de cabeçalhos (`sourceOrdinal`, começando em 1), além do título normalizado,
numeração e seções. `report.json` registra os cabeçalhos excluídos e os motivos.
Gold remove os campos de auditoria e acrescenta `id`, `version`, `updatedAt` e
`deleted: false`. O manifesto gold aponta para silver e seu hash; silver aponta
para a versão e hash do documento bronze.

Os timestamps são fornecidos explicitamente na criação da release. Nenhum horário
de execução é inserido no conteúdo transformado. Assim, repetir uma execução não
produz diferenças artificiais.

## Novo documento e nova release

Execute os comandos a partir da raiz, com o venv ativado. Exemplo para uma nova
edição (os números abaixo são exemplos; consulte a versão atual do banco):

```bash
corepack pnpm hymns:ingest --source /caminho/hinario-atualizado.odt --source-version sv-002
corepack pnpm hymns:transform --source-version sv-002
# O comando anterior imprime o dataset-id a usar no próximo comando.
corepack pnpm hymns:release --dataset <dataset-id> --version 4 --updated-at 2026-11-08T12:00:00Z
corepack pnpm hymns:validate --release 4
corepack pnpm hymns:seed --release 4
```

Depois, altere `data/current.json` para `{"release": 4}` e revise no PR as mudanças
de letras, números, títulos, exclusões e seed. Não edite JSONs gerados manualmente.
`hymns:seed` é a única etapa que escreve o seed TS; ingestão/transformação não
modificam consumidores nem acessam o banco.

Para experimentos sem gravar nas camadas versionadas:

```bash
python apps/hymns-pipeline/run.py --data-dir /tmp/hymns-experiment ingest \
  --source /caminho/hinario.odt --source-version experimento-001
```

Use o mesmo `--data-dir` antes do subcomando nas etapas seguintes.

## Regras editoriais

A seleção da fonte `sv-001` contém 236 hinos. O processamento aplica estas regras:

- Preserva a numeração dos hinos presentes entre 1 e 230.
- Exclui o intervalo 231 a 395.
- Numera os hinos após o 395 sequencialmente a partir de 396.
- Reconhece títulos pela cor e numeração; coros por negrito e marcadores explícitos.
- Normaliza Unicode/espaços, correções textuais, títulos em português e seções.

A quantidade 236 é uma referência da fonte `sv-001`, não uma restrição de futuras
edições. As regras de transformação ficam em módulos Python testados; decisões
editoriais declarativas ficam em `rules/`.

A deduplicação do bloco sem numeração compara títulos normalizados. Para
ocorrências com seções diferentes, `rules/duplicates-v1.json` registra as decisões
editoriais aprovadas, vinculadas aos hashes exatos das seções mantidas e descartadas.
As duas decisões cadastradas selecionam a primeira ocorrência de “Grande É o Senhor”
e de “Coração Igual ao Teu”. São versões das mesmas músicas, com diferenças nas
letras, repetições e estrutura. Uma colisão com conteúdo diferente sem decisão
cadastrada interrompe a transformação para revisão editorial.
Uma mudança nas decisões exige novo dataset silver e nova release gold.

Os IDs são derivados da numeração e identificam os hinos no Firestore,
nos favoritos e nos links compartilhados. Inserir/reordenar hinos no bloco sem numeração pode
mudar IDs; revise esse impacto editorial. Identidade permanente independente da
numeração exigiria uma migração própria dos consumidores.

## Contratos compartilhados

[`packages/hymns-contracts`](../../packages/hymns-contracts/README.md) contém os
JSON Schemas de hinos e releases. Python valida com `jsonschema`; JS valida com
Ajv; os tipos TS são gerados e reexportados por `@hinario/core`.

Além do schema, a pipeline verifica unicidade/ordem dos IDs e números, letras não
vazias, sequência das estrofes, versões, timestamps e integridade da linhagem.
`hymns:check` valida todas as camadas armazenadas, reproduz a release atual em um
diretório temporário com as regras atuais e compara o seed, sem modificar dados.
Releases históricas continuam auditáveis mesmo após novas regras.

## Publicação no Firestore

A publicação é separada da transformação e usa Application Default Credentials
(ADC). Localmente, utilize `gcloud auth application-default login` ou uma identidade
ADC já configurada. No CI, utilize Workload Identity Federation; não copie chaves
ou tokens para o repositório. A identidade precisa ler e gravar os documentos
necessários no projeto de destino, por exemplo via papel `roles/datastore.user`.
Não reutilize automaticamente a credencial do Firebase Hosting.

```bash
corepack pnpm hymns:publish --release 4 --project hinario-idc \
  --expected-remote-version 3 --dry-run
# Após revisar a simulação, execute o mesmo comando sem --dry-run.
```

A simulação faz leituras autenticadas, mas não envia gravações. A publicação:

1. Valida gold e sua linhagem antes de obter credenciais.
2. Confere a versão remota esperada e exige versão superior para conteúdo novo.
3. Prepara os documentos ativos e tombstones (`deleted: true`) para IDs removidos.
4. Envia hinos, tombstones e metadados em um único commit atômico, com precondições
   de `updateTime`/inexistência para rejeitar alterações concorrentes nos documentos.

IDs removidos recebem tombstones, sem exclusão física. Cada release é enviada
em um único commit.
A implementação recusa mais de 400 operações, documentos acima de 900 KiB ou
payload acima de 9 MiB antes de gravar. Esses limites conservadores preservam a
publicação atômica; acervos maiores precisam de uma estratégia própria.
Todos os escritores do acervo devem seguir o protocolo de publicação; alterações
avulsas diretamente no console não são uma forma suportada de atualizar hinos.

Uma repetição da mesma release é um no-op quando metadados e documentos ativos
correspondem exatamente. Versão igual com conteúdo diferente e downgrade são
recusados. Após conflito/timeout, consulte o estado e refaça a simulação; não há
retry cego de commits. Um rollback de conteúdo deve ser uma nova versão crescente.

O arquivo `data/current.json` seleciona a release usada no seed e na verificação
de reprodução. Antes de publicar, consulte a versão remota. Uma versão remota sem
`releaseHash` requer uma nova release com versão superior. O seed e o banco devem
receber o mesmo número de release, pois o cliente consulta `version > localVersion`.

## GitHub Actions

- **Hymns Pipeline CI:** PRs para `main`, pushes em `main` e execução manual; testa
  Python, contratos, reprodução das camadas/seed, tipos TS e build do app.
- **Publish Hymns to Firestore:** execução manual em `main`, release e versão
  remota explícitas; começa em modo simulação. Usa o environment
  `firestore-production` e serializa publicações.

Configure no GitHub o environment `firestore-production` com revisores obrigatórios
para publicação e restrição de branch `main`. A criação do YAML não ativa essas
proteções por si só. Configure suas variáveis:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`: nome completo do provedor WIF do Google.
- `HYMNS_PUBLISHER_SERVICE_ACCOUNT`: e-mail da service account com acesso ao banco.

O provedor deve confiar somente neste repositório e no environment/branch
permitidos, com impersonação da service account (`roles/iam.workloadIdentityUser`).
O workflow não cadastra infraestrutura, permissões ou credenciais automaticamente.
Configure também o check **Hymns Pipeline CI / validate** como obrigatório em
`main` se desejar bloquear merges inválidos. O deploy de Hosting continua separado.
