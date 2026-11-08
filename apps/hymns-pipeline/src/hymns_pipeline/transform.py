"""Silver editorial transformations, independent of storage and publishing."""
import re
from typing import Any
from .odt import LineSegment
from .rules import format_title_pt

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


def standardize(raw_hymns: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    final_hymns: list[dict[str, Any]] = []
    seen_unnumbered_titles: set[str] = set()
    next_unnumbered_num = 396
    reached_395 = False

    exclusions = []
    for ordinal, item in enumerate(raw_hymns, 1):
        header = item["header"].strip()
        num_match = re.match(r"^(\d{1,3})\.\s*(.+)$", header)

        if num_match and not reached_395:
            hymn_num = int(num_match.group(1))
            raw_title = num_match.group(2).strip()
            if hymn_num == 395:
                reached_395 = True
            if 231 <= hymn_num <= 395:
                # Ignora os hinos 231 ao 395
                exclusions.append({"sourceOrdinal": ordinal, "header": header, "reason": "excluded_range"})
                continue
            number = hymn_num
        else:
            # Hinos após o 395 (não numerados)
            raw_title = re.sub(r"^(\d{1,3})\.\s*", "", header).strip()
            dedup_key = re.sub(r"\s+", " ", raw_title.upper())
            if dedup_key in seen_unnumbered_titles:
                # Ignora duplicatas conhecidas no bloco final (ex: GRANDE É O SENHOR, CORAÇÃO IGUAL AO TEU)
                exclusions.append({"sourceOrdinal": ordinal, "header": header, "reason": "duplicate_title"})
                continue
            seen_unnumbered_titles.add(dedup_key)
            number = next_unnumbered_num
            next_unnumbered_num += 1

        title = format_title_pt(raw_title)
        sections = build_sections_from_lines(item["lines"])

        final_hymns.append(
            {
                "sourceOrdinal": ordinal,
                "rawTitle": raw_title,
                "number": number,
                "title": title,
                "sections": sections,

            }
        )

    final_hymns.sort(key=lambda h: h["number"])
    return final_hymns, exclusions


