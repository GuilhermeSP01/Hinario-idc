# Contratos de hinos

`schemas/hymn.schema.json` e `schemas/release.schema.json` são a fonte dos contratos compartilhados entre a pipeline Python e o app TypeScript (JSON Schema draft-07).

- `pnpm --filter @hinario/hymns-contracts generate`: gera tipos TS; não editar `src/hymn.generated.ts` manualmente.
- `pnpm --filter @hinario/hymns-contracts check`: falha se os tipos estiverem desatualizados.
- `pnpm --filter @hinario/hymns-contracts validate <caminho/hymns.json>`: valida releases com Ajv.

Python valida os mesmos schemas com `jsonschema`. Os tipos gerados não substituem validação em runtime. Restrições de quantidade dos arrays ficam na validação JSON Schema; os tipos usam arrays TS comuns para manter compatibilidade com os consumidores existentes. Unicidade, ordenação, IDs e versões são verificados adicionalmente pela pipeline.

`@hinario/core` reexporta os tipos públicos para preservar os imports existentes. Tipos exclusivos de busca permanecem em TS. Alterações incompatíveis exigem uma nova versão do contrato e migração dos consumidores.
