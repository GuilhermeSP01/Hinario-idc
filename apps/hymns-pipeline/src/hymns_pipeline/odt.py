"""ODT reader preserving formatting needed to recognize titles and choruses."""
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from .rules import normalize_text

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
}

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


def read_hymns(source: Path) -> list[dict[str, Any]]:
    """Executa a extração completa do arquivo ODT retornando a lista de hinos higienizados."""
    if not source.exists():
        raise FileNotFoundError(f"Arquivo ODT não encontrado em: {source}")

    with zipfile.ZipFile(source, "r") as zf:
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

    return raw_hymns
