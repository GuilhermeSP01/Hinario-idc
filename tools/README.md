# Ferramentas de Extração e Sincronização (`tools/`)

Scripts em Python (sem dependências externas, utilizando apenas a biblioteca padrão do Python 3.10+) para extrair, higienizar e publicar os hinos no **Cloud Firestore** e no **seed local** do aplicativo.

## Scripts disponíveis

### 1. Extração e higienização do ODT ([`extract_hymns.py`](file:///c:/Users/pablo/Documents/DEV/Hinário%20idc/tools/extract_hymns.py))
Lê `docs/Hinário de São Vicente.odt` e gera:
- `tools/output/hymns.json`: arquivo estruturado com todos os 236 hinos;
- `packages/firebase/src/seed/initialHymns.ts`: seed embutido no app para carregamento offline instantâneo.

```bash
pnpm hymns:extract
# ou diretamente:
python tools/extract_hymns.py
```

### 2. Upload e sincronização com o Cloud Firestore ([`upload_firestore.py`](file:///c:/Users/pablo/Documents/DEV/Hinário%20idc/tools/upload_firestore.py))
Envia os hinos de `tools/output/hymns.json` para a coleção `hymns` no projeto Firebase (`hinario-idc`) e atualiza `metadata/version` usando a sessão autenticada do Firebase CLI (`firebase login`).

- Para enviar mantendo a versão definida no JSON:
  ```bash
  pnpm hymns:upload
  ```
- Para incrementar automaticamente a versão remota (`currentVersion + 1`) após editar numeração, ordem, título ou letra de qualquer hino (forçando o **Delta Sync** nos dispositivos):
  ```bash
  pnpm hymns:sync
  # ou:
  python tools/upload_firestore.py --bump
  ```
