"""Pure production-equivalent HTML title/text extraction for V2.50.61.

This module intentionally contains no URL fetching, link traversal, search,
model, file, environment, process, evaluator, benchmark, or credential access.
Its decoding and visible-text rules mirror ``native_search`` while omitting the
unused link inventory, keeping the external mechanism forward capability-small.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser


class _HTMLTextExtractor(HTMLParser):
    SKIP_TAGS = {
        "script",
        "style",
        "noscript",
        "iframe",
        "svg",
        "canvas",
        "template",
    }
    BLOCK_TAGS = {
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tr",
        "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.title_parts: list[str] = []
        self.in_title = False
        self.table_depth = 0
        self.row_depth = 0
        self.cell_depth = 0
        self.row_cells: list[str] = []
        self.cell_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "title":
            self.in_title = True
        if tag == "table":
            self.table_depth += 1
            self.parts.append("\n")
            return
        if self.table_depth and tag == "tr":
            self.row_depth += 1
            if self.row_depth == 1:
                self.row_cells = []
            return
        if self.row_depth and tag in {"td", "th"}:
            self.cell_depth += 1
            if self.cell_depth == 1:
                self.cell_parts = []
            return
        if self.cell_depth:
            if tag in {"br", "p", "div", "li"}:
                self.cell_parts.append(" ")
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        if tag == "li":
            self.parts.append("- ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag == "title":
            self.in_title = False
        if self.cell_depth and tag in {"td", "th"}:
            if self.cell_depth == 1:
                cell = re.sub(r"\s+", " ", "".join(self.cell_parts)).strip()
                self.row_cells.append(cell)
                self.cell_parts = []
            self.cell_depth -= 1
            return
        if self.cell_depth:
            return
        if self.row_depth and tag == "tr":
            if self.row_depth == 1 and any(self.row_cells):
                self.parts.append(" | ".join(self.row_cells) + "\n")
                self.row_cells = []
            self.row_depth -= 1
            return
        if self.table_depth and tag == "table":
            self.table_depth -= 1
            self.parts.append("\n")
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        value = html.unescape(data)
        if self.in_title:
            self.title_parts.append(value)
        if self.cell_depth:
            self.cell_parts.append(value)
            return
        self.parts.append(value)

    def result(self) -> tuple[str, str]:
        raw = "".join(self.parts).replace("\xa0", " ")
        lines: list[str] = []
        for line in raw.splitlines():
            normalized = re.sub(r"[ \t\r\f\v]+", " ", line).strip(" |")
            if normalized:
                lines.append(normalized)
            elif lines and lines[-1] != "":
                lines.append("")
        text = "\n".join(lines).strip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        title = " ".join(" ".join(self.title_parts).split()).strip()
        return title, text


def html_to_title_text(raw_html: str) -> tuple[str, str]:
    parser = _HTMLTextExtractor()
    parser.feed(raw_html)
    parser.close()
    return parser.result()


def decode_web_text(raw: bytes, declared_encoding: str | None) -> str:
    prefix = raw[:4096]
    charset_match = re.search(
        br"(?:charset\s*=|encoding\s*=\s*[\"'])([A-Za-z0-9._-]+)",
        prefix,
        re.IGNORECASE,
    )
    candidates: list[str] = []
    if charset_match:
        candidates.append(charset_match.group(1).decode("ascii", errors="ignore"))
    if declared_encoding and declared_encoding.casefold() not in {
        "iso-8859-1",
        "latin-1",
        "ascii",
    }:
        candidates.append(declared_encoding)
    candidates.extend(["utf-8", "gb18030"])
    for encoding in dict.fromkeys(value for value in candidates if value):
        try:
            return raw.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode(declared_encoding or "utf-8", errors="replace")


__all__ = ["decode_web_text", "html_to_title_text"]
