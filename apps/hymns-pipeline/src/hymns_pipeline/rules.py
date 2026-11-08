"""Portuguese editorial normalization; compatibility rules v1."""
import re
import unicodedata

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


