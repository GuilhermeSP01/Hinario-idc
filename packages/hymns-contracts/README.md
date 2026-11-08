# Contratos de hinos

`schemas/hymn.schema.json` e `schemas/release.schema.json` são a fonte dos contratos compartilhados entre a pipeline Python e o app TypeScript (JSON Schema draft-07).

- `pnpm --filter @hinario/hymns-contracts generate`: gera tipos TS; não editar `src/hymn.generated.ts` manualmente.
- `pnpm --filter @hinario/hymns-contracts check`: falha se os tipos estiverem desatualizados.
- `pnpm --filter @hinario/hymns-contracts validate <caminho/hymns.json>`: valida releases com Ajv.

Python valida os mesmos schemas com `jsonschema`. Os tipos gerados não substituem validação em runtime. Restrições de quantidade dos arrays ficam na validação JSON Schema; os tipos usam arrays TS comuns. Unicidade, ordenação, IDs e versões são verificados adicionalmente pela pipeline.

`@hinario/core` reexporta os tipos públicos para os consumidores do domínio. Tipos exclusivos de busca são definidos em TS. Alterações incompatíveis exigem uma nova versão do contrato e migração dos consumidores.

`hymn-content.schema.json` valida entradas de criação (`number`, `title`, `sections`).
`hymn-update.schema.json` valida atualizações parciais desses campos. Campos de
publicação e identidade são gerenciados pela pipeline, sem entrada manual.
Os IDs aceitam o formato numérico existente e UUID4; não derivam do número de
exibição. Números são inteiros de 1 a 65535. Python e JS usam os mesmos schemas.
