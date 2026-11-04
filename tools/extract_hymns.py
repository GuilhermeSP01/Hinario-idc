#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrator e higienizador de hinos a partir do arquivo ODT ("Hinário de São Vicente.odt").

Regras aplicadas:
1. Bloco 1 (Hinos 1 a 230): mantém a numeração original (168 hinos presentes no intervalo).
2. Bloco 2 (Hinos 231 a 395): ignorado conforme definição do projeto.
3. Bloco 3 (Hinos sem número após o 395): numerados sequencialmente a partir de 396,
   removendo duplicatas exatas ("GRANDE É O SENHOR" e "CORAÇÃO IGUAL AO TEU").
4. Coros:
   - Identificados tanto por formatação em negrito (fo:font-weight="bold") quanto
     por prefixo explícito "Coro:" / "Coro Final...".
   - O prefixo "Coro:" é removido do texto final pois a UI já exibe o badge "Coro".
   - Indicações isoladas ou finais de repetição como "(Coro)", "- Coro (2x)" são limpas.
5. Títulos:
   - Padronizados em Title Case da língua portuguesa, preservando preposições/artigos
     em minúsculas no meio da frase e pronomes/nomes sagrados com inicial maiúscula.

Gera:
- tools/output/hymns.json (JSON estruturado para inspeção e upload ao Firestore)
- packages/firebase/src/seed/initialHymns.ts (Seed local para funcionamento offline imediato)
"""

from __future__ import annotations

import json
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
ODT_PATH = ROOT_DIR / "docs" / "Hinário de São Vicente.odt"
OUTPUT_JSON_PATH = ROOT_DIR / "tools" / "output" / "hymns.json"
SEED_TS_PATH = ROOT_DIR / "packages" / "firebase" / "src" / "seed" / "initialHymns.ts"

HINARIO_VERSION = 3
UPDATED_AT_ISO = "2026-11-03T12:00:00.000Z"

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
}

LOWERCASE_PARTICLES = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "contra",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "entre",
    "na",
    "nas",
    "no",
    "nos",
    "num",
    "numa",
    "o",
    "os",
    "ou",
    "para",
    "pela",
    "pelas",
    "pelo",
    "pelos",
    "por",
    "pra",
    "pro",
    "que",
    "se",
    "sem",
    "sob",
    "sobre",
    "um",
    "uma",
    "uns",
    "umas",
    "à",
    "às",
}

UPPERCASE_ROMAN_OR_ACRONYMS = {"i", "ii", "iii", "iv", "v", "idc"}


def normalize_text(text: str) -> str:
    """Normaliza acentuação decomposta (NFD -> NFC) e limpa espaços invisíveis."""
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\u00a0", " ").replace("\t", " ")
    # Corrige casos conhecidos de palavras coladas ou erros de digitação no documento original
    normalized = re.sub(r"\bEXUTALÇÃO\b", "EXALTAÇÃO", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bQUÃO GRANDE ÉS TÚ\b", "QUÃO GRANDE ÉS TU", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bÓRei\b", "Ó Rei", normalized)
    normalized = re.sub(r"\bATeu\b", "A Teu", normalized)
    normalized = re.sub(r"\bATua\b", "A Tua", normalized)
    normalized = re.sub(r"\bestáandando\b", "está andando", normalized)
    normalized = re.sub(r"\bOmeu\b", "O meu", normalized)
    normalized = re.sub(r";H:", "; H:", normalized)
    normalized = re.sub(r"\.\(bis\)", ". (bis)", normalized)
    normalized = re.sub(r" {2,}", " ", normalized)
    return normalized.strip()


def format_title_pt(raw_title: str) -> str:
    """Converte um título em CAIXA ALTA para Title Case adequado ao português."""
    cleaned = normalize_text(raw_title)
    # Remove ponto final isolado em títulos, mas preserva "!", "?", "..."
    if cleaned.endswith(".") and not cleaned.endswith("..."):
        cleaned = cleaned[:-1].strip()

    # Divide mantendo espaços e pontuações
    tokens = re.split(r"(\s+)", cleaned)
    word_indices = [i for i, tok in enumerate(tokens) if not tok.isspace() and tok]
    if not word_indices:
        return cleaned

    first_word_idx = word_indices[0]
    result: list[str] = []

    prev_ended_with_punct = False
    for idx, token in enumerate(tokens):
        if token.isspace() or not token:
            result.append(token)
            continue

        # Separa pontuação inicial/final da palavra (ex: "(Salmo", "Senhor!", "D'Ele", "Minh’Alma")
        match = re.match(r"^([^\wÀ-ÿ'’]*)([\wÀ-ÿ'’–.,-]+?)([^\wÀ-ÿ'’]*)$", token)
        if not match:
            result.append(token)
            prev_ended_with_punct = any(p in token for p in ":?!;—-")
            continue

        prefix, core, suffix = match.groups()
        lower_core = core.lower().replace("–", "-").replace("’", "'")

        is_first = idx == first_word_idx or prev_ended_with_punct

        if lower_core in UPPERCASE_ROMAN_OR_ACRONYMS and len(lower_core) > 1:
            formatted_core = lower_core.upper()
        elif "'" in lower_core:
            # Ex: d'Ele, Minh'Alma
            parts = lower_core.split("'")
            if parts[0] == "d" and len(parts) == 2:
                first_part = parts[0].capitalize() if is_first else parts[0]
                formatted_core = f"{first_part}'{parts[1].capitalize()}"
            else:
                formatted_core = "'".join(p.capitalize() for p in parts)
        elif "-" in lower_core and not re.search(r"\d", lower_core):
            parts = lower_core.split("-")
            formatted_core = "-".join(
                p.capitalize() if (j == 0 or p not in LOWERCASE_PARTICLES) else p
                for j, p in enumerate(parts)
            )
        elif not is_first and lower_core in LOWERCASE_PARTICLES:
            formatted_core = lower_core
        else:
            formatted_core = lower_core.capitalize()

        result.append(f"{prefix}{formatted_core}{suffix}")
        prev_ended_with_punct = any(p in suffix for p in ":?!;") or token in ("-", "–", "—")

    return "".join(result)


def parse_styles(root: ET.Element, styles_root: ET.Element) -> dict[str, dict[str, Any]]:
    """Mapeia estilos de parágrafo e texto (cor, negrito, itálico) do ODT."""
    styles: dict[str, dict[str, Any]] = {}
    for s_root in (styles_root, root):
        for st in s_root.findall(".//style:style", NS):
            name = st.attrib.get(f"{{{NS['style']}}}name")
            parent = st.attrib.get(f"{{{NS['style']}}}parent-style-name")
            tp = st.find("style:text-properties", NS)
            bold: bool | None = None
            italic: bool | None = None
            color: str | None = None
            if tp is not None:
                fw = tp.attrib.get(f"{{{NS['fo']}}}font-weight")
                fs = tp.attrib.get(f"{{{NS['fo']}}}font-style")
                col = tp.attrib.get(f"{{{NS['fo']}}}color")
                if fw == "bold":
                    bold = True
                elif fw == "normal":
                    bold = False
                if fs == "italic":
                    italic = True
                elif fs == "normal":
                    italic = False
                if col:
                    color = col.upper()
            styles[name] = {
                "parent": parent,
                "bold": bold,
                "italic": italic,
                "color": color,
            }

    def resolve_prop(style_name: str | None, prop: str) -> Any:
        visited: set[str] = set()
        curr = style_name
        while curr and curr in styles and curr not in visited:
            visited.add(curr)
            if styles[curr][prop] is not None:
                return styles[curr][prop]
            curr = styles[curr]["parent"]
        return None

    resolved: dict[str, dict[str, Any]] = {}
    for name in styles:
        resolved[name] = {
            "bold": bool(resolve_prop(name, "bold")),
            "italic": bool(resolve_prop(name, "italic")),
            "color": resolve_prop(name, "color"),
        }
    return resolved


class LineSegment:
    """Representa uma linha individual extraída do ODT com seus metadados visuais."""

    def __init__(self, text: str, is_bold: bool, is_red_title: bool) -> None:
        self.text = text
        self.is_bold = is_bold
        self.is_red_title = is_red_title


def extract_lines_from_paragraph(
    elem: ET.Element, resolved_styles: dict[str, dict[str, Any]]
) -> list[LineSegment]:
    """
    Extrai as linhas de um <text:p> ou <text:h>, respeitando quebras de linha (<text:line-break/>)
    e preservando o estilo (negrito / cor de título #C00000) de cada linha individual.
    """
    p_style_name = elem.attrib.get(f"{{{NS['text']}}}style-name")
    p_style = resolved_styles.get(p_style_name or "", {"bold": False, "color": None})
    p_bold = bool(p_style["bold"])
    p_color = p_style["color"]

    # Uma linha é composta por uma lista de fragmentos (texto, bold, color)
    lines_fragments: list[list[tuple[str, bool, str | None]]] = [[]]

    def append_text(txt: str | None, bold: bool, color: str | None) -> None:
        if not txt:
            return
        parts = txt.split("\n")
        for idx, part in enumerate(parts):
            if idx > 0:
                lines_fragments.append([])
            if part:
                lines_fragments[-1].append((part, bold, color))

    append_text(elem.text, p_bold, p_color)

    for child in elem:
        tag = child.tag.split("}")[-1]
        if tag == "line-break":
            lines_fragments.append([])
            append_text(child.tail, p_bold, p_color)
        elif tag == "s":
            count = int(child.attrib.get(f"{{{NS['text']}}}c", "1"))
            append_text(" " * count, p_bold, p_color)
            append_text(child.tail, p_bold, p_color)
        elif tag == "tab":
            append_text(" ", p_bold, p_color)
            append_text(child.tail, p_bold, p_color)
        elif tag == "span":
            s_name = child.attrib.get(f"{{{NS['text']}}}style-name")
            s_style = resolved_styles.get(s_name or "", {"bold": None, "color": None})
            # Verifica se o span tem estilo próprio ou herda do parágrafo
            span_bold = p_bold
            span_color = p_color
            if s_name and s_name in resolved_styles:
                if resolved_styles[s_name]["bold"]:
                    span_bold = True
                if resolved_styles[s_name]["color"]:
                    span_color = resolved_styles[s_name]["color"]

            append_text(child.text, span_bold, span_color)
            for sub in child:
                sub_tag = sub.tag.split("}")[-1]
                if sub_tag == "line-break":
                    lines_fragments.append([])
                    append_text(sub.tail, span_bold, span_color)
                elif sub_tag == "s":
                    count = int(sub.attrib.get(f"{{{NS['text']}}}c", "1"))
                    append_text(" " * count, span_bold, span_color)
                    append_text(sub.tail, span_bold, span_color)
                else:
                    append_text("".join(sub.itertext()), span_bold, span_color)
                    append_text(sub.tail, span_bold, span_color)
            append_text(child.tail, p_bold, p_color)
        else:
            append_text("".join(child.itertext()), p_bold, p_color)
            append_text(child.tail, p_bold, p_color)

    segments: list[LineSegment] = []
    for frags in lines_fragments:
        raw_line = "".join(t for t, _, _ in frags)
        norm_line = normalize_text(raw_line)
        if not norm_line:
            segments.append(LineSegment("", False, False))
            continue

        non_space_chars = sum(len(t.strip()) for t, _, _ in frags)
        bold_chars = sum(len(t.strip()) for t, b, _ in frags if b)
        red_chars = sum(len(t.strip()) for t, _, c in frags if c == "#C00000")

        is_bold = non_space_chars > 0 and (bold_chars / non_space_chars) >= 0.5
        is_red = non_space_chars > 0 and (red_chars / non_space_chars) >= 0.5
        segments.append(LineSegment(norm_line, is_bold, is_red))

    return segments


def is_standalone_coro_marker(line: str) -> bool:
    """Verifica se a linha é apenas uma instrução de repetição do coro, ex: '(Coro)', '- Coro (2x)'."""
    return bool(
        re.match(
            r"^[-–—\s]*(\(\d+x\)\s*)?\(?\s*coro\s*(\(\d+x\))?\s*\)?(\s*\(\d+x\))?\.?\s*$",
            line,
            flags=re.IGNORECASE,
        )
    )


def clean_lyric_line(line: str) -> str:
    """Remove marcadores '(Coro)' ao final do verso e prefixos 'Ponte:'."""
    cleaned = re.sub(r"\s*\([Cc]oro\)\s*$", "", line).strip()
    cleaned = re.sub(r"^Ponte\s*:\s*", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def build_sections_from_lines(lines: list[LineSegment]) -> list[dict[str, Any]]:
    """
    Agrupa as linhas de um hino em estrofes (verse) e coros (chorus).
    Divide blocos quando:
    - Há uma linha em branco;
    - Há transição entre negrito (coro) e texto normal (estrofe);
    - Uma linha inicia explicitamente com 'Coro:' ou 'Ponte:'.
    """
    raw_blocks: list[tuple[list[str], bool]] = []
    current_lines: list[str] = []
    current_bold: bool | None = None
    force_chorus_next = False

    def flush_block() -> None:
        nonlocal current_lines, current_bold, force_chorus_next
        if current_lines:
            raw_blocks.append((current_lines, bool(current_bold or force_chorus_next)))
            current_lines = []
            current_bold = None
            force_chorus_next = False

    for seg in lines:
        txt = seg.text.strip()
        if not txt:
            # Se acabou de abrir um cabeçalho "Coro:" solto e veio linha vazia, mantém force_chorus_next
            if current_lines:
                flush_block()
            continue

        # Ignora linhas que são apenas referência "(Coro)" ou "- Coro (2x)"
        if is_standalone_coro_marker(txt):
            continue

        # Caso a linha seja apenas "Coro:" ou "Ponte:"
        if re.match(r"^Coro\s*:\s*$", txt, flags=re.IGNORECASE):
            flush_block()
            force_chorus_next = True
            continue

        if re.match(r"^Ponte\s*:\s*$", txt, flags=re.IGNORECASE):
            flush_block()
            continue

        # Caso a linha comece com "Coro: ..." ou "Coro Final..."
        coro_inline_match = re.match(
            r"^Coro(?:\s+Final\s*[-–—]?\s*[^:]*)?\s*:\s*(.+)$", txt, flags=re.IGNORECASE
        )
        if coro_inline_match:
            flush_block()
            force_chorus_next = True
            txt = coro_inline_match.group(1).strip()

        # Caso a linha comece com "Ponte: ..."
        ponte_inline_match = re.match(r"^Ponte\s*:\s*(.+)$", txt, flags=re.IGNORECASE)
        if ponte_inline_match:
            flush_block()
            txt = ponte_inline_match.group(1).strip()

        # Se mudou de negrito para normal (ou vice-versa) sem linha em branco no meio
        if current_lines and not force_chorus_next and seg.is_bold != current_bold:
            flush_block()

        cleaned = clean_lyric_line(txt)
        if not cleaned or is_standalone_coro_marker(cleaned):
            continue

        if current_bold is None:
            current_bold = seg.is_bold
        current_lines.append(cleaned)

    flush_block()

    sections: list[dict[str, Any]] = []
    verse_counter = 1
    for block_lines, is_chorus in raw_blocks:
        if not block_lines:
            continue
        if is_chorus:
            sections.append({"type": "chorus", "lines": block_lines})
        else:
            sections.append(
                {
                    "type": "verse",
                    "number": verse_counter,
                    "lines": block_lines,
                }
            )
            verse_counter += 1

    return sections


def extract_hymns() -> list[dict[str, Any]]:
    """Executa a extração completa do arquivo ODT retornando a lista de hinos higienizados."""
    if not ODT_PATH.exists():
        raise FileNotFoundError(f"Arquivo ODT não encontrado em: {ODT_PATH}")

    with zipfile.ZipFile(ODT_PATH, "r") as zf:
        content_root = ET.fromstring(zf.read("content.xml"))
        styles_root = ET.fromstring(zf.read("styles.xml"))

    resolved_styles = parse_styles(content_root, styles_root)
    body = content_root.find("office:body/office:text", NS)
    if body is None:
        raise RuntimeError("Elemento office:text não encontrado no ODT.")

    elements = [
        el
        for el in body
        if el.tag in (f"{{{NS['text']}}}p", f"{{{NS['text']}}}h")
    ]

    # Achata todos os parágrafos em uma sequência de linhas com fronteira de parágrafo (linha vazia entre parágrafos vazios)
    all_lines: list[LineSegment] = []
    for elem in elements:
        p_segments = extract_lines_from_paragraph(elem, resolved_styles)
        if not p_segments or (len(p_segments) == 1 and not p_segments[0].text):
            all_lines.append(LineSegment("", False, False))
        else:
            all_lines.extend(p_segments)

    # Identifica o início de cada hino pela cor de título (#C00000) ou numeração explícita (ex: 231..395 que não têm cor vermelha)
    raw_hymns: list[dict[str, Any]] = []
    current_header: str | None = None
    current_body: list[LineSegment] = []

    for seg in all_lines:
        is_numbered_header = bool(
            seg.text
            and re.match(r"^(?:23[1-9]|2[4-9]\d|3[0-8]\d|39[0-5])\.\s+", seg.text)
        )
        if (seg.is_red_title or is_numbered_header) and seg.text:
            # Se o título veio dividido em duas linhas vermelhas consecutivas (sem corpo ainda), junta
            if (
                current_header is not None
                and seg.is_red_title
                and not is_numbered_header
                and not any(s.text for s in current_body)
            ):
                current_header = f"{current_header} {seg.text}"
                continue
            if current_header is not None:
                raw_hymns.append({"header": current_header, "lines": current_body})
            current_header = seg.text
            current_body = []
        else:
            if current_header is not None:
                current_body.append(seg)

    if current_header is not None:
        raw_hymns.append({"header": current_header, "lines": current_body})

    final_hymns: list[dict[str, Any]] = []
    seen_unnumbered_titles: set[str] = set()
    next_unnumbered_num = 396
    reached_395 = False

    for item in raw_hymns:
        header = item["header"].strip()
        num_match = re.match(r"^(\d{1,3})\.\s*(.+)$", header)

        if num_match and not reached_395:
            hymn_num = int(num_match.group(1))
            raw_title = num_match.group(2).strip()
            if hymn_num == 395:
                reached_395 = True
            if 231 <= hymn_num <= 395:
                # Ignora os hinos 231 ao 395
                continue
            number = hymn_num
        else:
            # Hinos após o 395 (não numerados)
            raw_title = re.sub(r"^(\d{1,3})\.\s*", "", header).strip()
            dedup_key = re.sub(r"\s+", " ", raw_title.upper())
            if dedup_key in seen_unnumbered_titles:
                # Ignora duplicatas conhecidas no bloco final (ex: GRANDE É O SENHOR, CORAÇÃO IGUAL AO TEU)
                continue
            seen_unnumbered_titles.add(dedup_key)
            number = next_unnumbered_num
            next_unnumbered_num += 1

        title = format_title_pt(raw_title)
        sections = build_sections_from_lines(item["lines"])

        final_hymns.append(
            {
                "id": f"{number:03d}",
                "number": number,
                "title": title,
                "sections": sections,
                "version": HINARIO_VERSION,
            }
        )

    final_hymns.sort(key=lambda h: h["number"])
    return final_hymns


def write_outputs(hymns: list[dict[str, Any]]) -> None:
    """Salva o JSON estruturado em tools/output/hymns.json e atualiza initialHymns.ts."""
    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": HINARIO_VERSION,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "totalHymns": len(hymns),
        "hymns": hymns,
    }
    OUTPUT_JSON_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    ts_content = (
        "import type { Hymn } from '@hinario/core';\n\n"
        f"export const INITIAL_HINARIO_VERSION = {HINARIO_VERSION};\n\n"
        "export const INITIAL_HYMNS_SEED: Hymn[] = "
        f"{json.dumps(hymns, ensure_ascii=False, indent=2)};\n"
    )
    SEED_TS_PATH.write_text(ts_content, encoding="utf-8")


def main() -> None:
    hymns = extract_hymns()
    write_outputs(hymns)

    block1 = [h for h in hymns if h["number"] <= 230]
    block3 = [h for h in hymns if h["number"] >= 396]
    with_chorus = sum(
        1 for h in hymns if any(s["type"] == "chorus" for s in h["sections"])
    )
    empty_hymns = [h for h in hymns if not h["sections"]]

    print(f"Total de hinos extraídos: {len(hymns)}")
    print(f"  - Bloco 1 (1..230): {len(block1)} hinos")
    print(f"  - Bloco 3 (396..{block3[-1]['number'] if block3 else 395}): {len(block3)} hinos")
    print(f"  - Hinos com coro detectado: {with_chorus}")
    print(f"  - Hinos sem estrofes (erro): {len(empty_hymns)}")
    print(f"JSON salvo em: {OUTPUT_JSON_PATH}")
    print(f"Seed TS atualizado em: {SEED_TS_PATH}")


if __name__ == "__main__":
    main()
