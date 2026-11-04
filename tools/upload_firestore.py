#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de sincronização e upload dos hinos extraídos para o Cloud Firestore.

Funcionalidades:
- Lê o arquivo gerado `tools/output/hymns.json`.
- Autentica usando a sessão ativa do Firebase CLI (`~/.config/configstore/firebase-tools.json`)
  ou credenciais de Service Account (caso `firebase-admin` e `GOOGLE_APPLICATION_CREDENTIALS` estejam configurados).
- Consulta a versão atual em `metadata/version` no Firestore e garante que a nova versão
  seja incrementada (`max(version_json, remote_version + 1)`) quando `--bump` é utilizado,
  permitindo que o Delta Sync dos aplicativos clientes reconheça qualquer alteração
  futura de numeração, ordem, título ou letra.
- Marca automaticamente como `deleted: true` eventuais documentos antigos no Firestore
  cujo `id` tenha deixado de existir na nova lista.
- Envia todos os hinos e atualiza `metadata/version` em lotes atômicos (`documents:commit`).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
HYMNS_JSON_PATH = ROOT_DIR / "tools" / "output" / "hymns.json"
FIREBASE_RC_PATH = ROOT_DIR / ".firebaserc"
FIREBASE_TOOLS_CONFIG = Path.home() / ".config" / "configstore" / "firebase-tools.json"


def get_project_id() -> str:
    """Obtém o Project ID do arquivo .firebaserc."""
    if FIREBASE_RC_PATH.exists():
        data = json.loads(FIREBASE_RC_PATH.read_text(encoding="utf-8"))
        proj = data.get("projects", {}).get("default")
        if proj:
            return str(proj)
    return "hinario-idc"


def get_firebase_cli_access_token() -> str:
    """
    Obtém um OAuth2 access_token válido a partir da sessão do Firebase CLI.
    Se o token estiver próximo de expirar, executa um comando leve do Firebase CLI para renová-lo.
    """
    if not FIREBASE_TOOLS_CONFIG.exists():
        raise RuntimeError(
            "Configuração do Firebase CLI não encontrada. Execute 'firebase login' primeiro."
        )

    cfg = json.loads(FIREBASE_TOOLS_CONFIG.read_text(encoding="utf-8"))
    tokens = cfg.get("tokens", {})
    expires_at_ms = int(tokens.get("expires_at", 0))
    now_ms = int(time.time() * 1000)

    if not tokens.get("access_token") or now_ms >= (expires_at_ms - 60_000):
        print("Renovando token OAuth via Firebase CLI...")
        subprocess.run(
            ["firebase", "projects:list", "--json"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=(sys.platform == "win32"),
            check=False,
        )
        cfg = json.loads(FIREBASE_TOOLS_CONFIG.read_text(encoding="utf-8"))
        tokens = cfg.get("tokens", {})

    token = tokens.get("access_token")
    if not token:
        raise RuntimeError("Não foi possível obter access_token do Firebase CLI.")
    return str(token)


def to_firestore_value(val: Any) -> dict[str, Any]:
    """Converte um valor Python nativo para o formato tipado da API REST do Firestore."""
    if val is None:
        return {"nullValue": None}
    if isinstance(val, bool):
        return {"booleanValue": val}
    if isinstance(val, int):
        return {"integerValue": str(val)}
    if isinstance(val, float):
        return {"doubleValue": val}
    if isinstance(val, str):
        return {"stringValue": val}
    if isinstance(val, list):
        return {"arrayValue": {"values": [to_firestore_value(item) for item in val]}}
    if isinstance(val, dict):
        return {
            "mapValue": {
                "fields": {k: to_firestore_value(v) for k, v in val.items()}
            }
        }
    return {"stringValue": str(val)}


def from_firestore_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """Extrai valores simples de um mapa de fields do Firestore."""
    out: dict[str, Any] = {}
    for k, v in fields.items():
        if "integerValue" in v:
            out[k] = int(v["integerValue"])
        elif "stringValue" in v:
            out[k] = v["stringValue"]
        elif "booleanValue" in v:
            out[k] = bool(v["booleanValue"])
    return out


def firestore_request(
    method: str, url: str, token: str, body: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Executa uma requisição HTTP autenticada contra a API REST do Firestore."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace")
        if err.code == 404:
            return {}
        raise RuntimeError(f"Erro HTTP {err.code} em {url}: {err_body}") from err


def fetch_remote_version(base_doc_url: str, token: str) -> int:
    """Lê a versão atual em metadata/version no Firestore (retorna 0 se não existir)."""
    res = firestore_request("GET", f"{base_doc_url}/metadata/version", token)
    fields = res.get("fields", {})
    if not fields:
        return 0
    parsed = from_firestore_fields(fields)
    return int(parsed.get("currentVersion", 0))


def fetch_existing_hymn_ids(base_doc_url: str, token: str) -> dict[str, dict[str, Any]]:
    """Lista todos os documentos atualmente existentes na coleção `hymns` do Firestore."""
    existing: dict[str, dict[str, Any]] = {}
    page_token = ""
    while True:
        url = f"{base_doc_url}/hymns?pageSize=300"
        if page_token:
            url += f"&pageToken={page_token}"
        res = firestore_request("GET", url, token)
        for doc in res.get("documents", []):
            doc_name = doc.get("name", "")
            doc_id = doc_name.split("/")[-1]
            parsed = from_firestore_fields(doc.get("fields", {}))
            existing[doc_id] = parsed
        page_token = res.get("nextPageToken", "")
        if not page_token:
            break
    return existing


def upload_to_firestore(bump_version: bool = False) -> None:
    if not HYMNS_JSON_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo {HYMNS_JSON_PATH} não encontrado. Execute 'python tools/extract_hymns.py' primeiro."
        )

    payload = json.loads(HYMNS_JSON_PATH.read_text(encoding="utf-8"))
    hymns: list[dict[str, Any]] = payload["hymns"]
    json_version = int(payload.get("version", 2))

    project_id = get_project_id()
    token = get_firebase_cli_access_token()
    base_doc_path = f"projects/{project_id}/databases/(default)/documents"
    base_doc_url = f"https://firestore.googleapis.com/v1/{base_doc_path}"

    remote_version = fetch_remote_version(base_doc_url, token)
    if bump_version and remote_version >= json_version:
        target_version = remote_version + 1
    else:
        target_version = max(json_version, remote_version)

    now_iso = datetime.now(timezone.utc).isoformat()
    existing_docs = fetch_existing_hymn_ids(base_doc_url, token)
    new_ids = {str(h["id"]) for h in hymns}

    writes: list[dict[str, Any]] = []

    # 1. Prepara gravação de todos os hinos ativos
    for hymn in hymns:
        doc_id = str(hymn["id"])
        hymn_doc = {
            "id": doc_id,
            "number": int(hymn["number"]),
            "title": str(hymn["title"]),
            "sections": hymn["sections"],
            "updatedAt": now_iso,
            "version": target_version,
            "deleted": False,
        }
        writes.append(
            {
                "update": {
                    "name": f"{base_doc_path}/hymns/{doc_id}",
                    "fields": {
                        k: to_firestore_value(v) for k, v in hymn_doc.items()
                    },
                }
            }
        )

    # 2. Trata documentos antigos que não estão na nova lista
    soft_deleted_count = 0
    hard_deleted_count = 0
    for old_id, old_data in existing_docs.items():
        if old_id not in new_ids:
            # Se o ID antigo não seguia o padrão de 3 dígitos (ex: migração de formato), remove fisicamente
            if len(old_id) < 3:
                writes.append({"delete": f"{base_doc_path}/hymns/{old_id}"})
                hard_deleted_count += 1
            elif not old_data.get("deleted", False):
                soft_delete_doc = {
                    "id": old_id,
                    "number": int(old_data.get("number", 0)),
                    "title": str(old_data.get("title", "")),
                    "sections": [],
                    "updatedAt": now_iso,
                    "version": target_version,
                    "deleted": True,
                }
                writes.append(
                    {
                        "update": {
                            "name": f"{base_doc_path}/hymns/{old_id}",
                            "fields": {
                                k: to_firestore_value(v)
                                for k, v in soft_delete_doc.items()
                            },
                        }
                    }
                )
                soft_deleted_count += 1

    # 3. Atualiza o documento global de versão (metadata/version)
    writes.append(
        {
            "update": {
                "name": f"{base_doc_path}/metadata/version",
                "fields": {
                    "currentVersion": to_firestore_value(target_version),
                    "updatedAt": to_firestore_value(now_iso),
                    "totalHymns": to_firestore_value(len(hymns)),
                },
            }
        }
    )

    # Envia em lotes de até 400 operações por commit
    batch_size = 400
    commit_url = f"{base_doc_url}:commit"
    for i in range(0, len(writes), batch_size):
        chunk = writes[i : i + batch_size]
        firestore_request("POST", commit_url, token, {"writes": chunk})
        print(
            f"Lote enviado com sucesso ({min(i + batch_size, len(writes))}/{len(writes)} operações)..."
        )

    print("\nSincronização com Cloud Firestore concluída!")
    print(f"  - Projeto: {project_id}")
    print(f"  - Hinos enviados: {len(hymns)}")
    print(f"  - Hinos obsoletos marcados como removidos: {soft_deleted_count}")
    print(f"  - Versão publicada (metadata/version): v{target_version}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Faz o upload dos hinos extraídos para o Cloud Firestore."
    )
    parser.add_argument(
        "--bump",
        action="store_true",
        help="Incrementa automaticamente a versão remota em +1 para forçar Delta Sync nos clientes.",
    )
    args = parser.parse_args()
    upload_to_firestore(bump_version=args.bump)


if __name__ == "__main__":
    main()
