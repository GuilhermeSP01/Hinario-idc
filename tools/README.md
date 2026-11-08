# Ferramentas

`generate-icons.mjs` gera ícones Web/PWA e assets do Capacitor em
`apps/mobile/public/` e `apps/mobile/assets/`. Utiliza o favicon SVG do aplicativo
e os desenhos SVG definidos no script.

Com as dependências do workspace instaladas, execute a partir da raiz:

```bash
node tools/generate-icons.mjs
```

O script grava os arquivos de imagem nos diretórios de destino, substituindo os
arquivos de mesmo nome.
