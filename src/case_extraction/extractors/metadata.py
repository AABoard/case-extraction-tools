"""Metadata extraction from document text and embedded document metadata."""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedMetadata:
    """Structured metadata extracted from a document."""

    title: str | None = None
    authors: list[str] = field(default_factory=list)
    date: str | None = None
    venue: str | None = None
    document_type: str | None = None
    source_filename: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def extract_metadata(
    text: str,
    embedded_meta: dict[str, Any] | None = None,
    source_filename: str | None = None,
) -> ExtractedMetadata:
    """
    Extract metadata from document text and optional embedded metadata.

    Uses heuristics:
    - First non-empty line as candidate title (if short enough)
    - Common patterns: "Authors:", "Date:", "Abstract", etc.
    - Embedded metadata from PDF/DOCX takes precedence when present

    Args:
        text: Full document text.
        embedded_meta: Optional dict from PDF/DOCX (title, author, subject, etc.)
        source_filename: Optional source file name.

    Returns:
        ExtractedMetadata with populated fields.
    """
    out = ExtractedMetadata(raw={})

    if embedded_meta:
        out.raw["embedded"] = embedded_meta
        if embedded_meta.get("title"):
            out.title = _clean(embedded_meta["title"])
        if embedded_meta.get("author"):
            authors_str = _clean(embedded_meta["author"])
            out.authors = _split_authors(authors_str)
        if embedded_meta.get("subject"):
            out.raw["subject"] = _clean(embedded_meta["subject"])
        if embedded_meta.get("created"):
            out.date = _normalize_date(embedded_meta["created"])
        elif embedded_meta.get("modified"):
            out.date = _normalize_date(embedded_meta["modified"])

    if source_filename:
        out.source_filename = source_filename

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()][:50]

    # Heuristic: first substantial line as title if not set
    if not out.title and lines:
        for line in lines[:5]:
            if len(line) > 10 and len(line) < 200 and not line.startswith("http"):
                out.title = line
                break

    # Look for common patterns
    for i, line in enumerate(lines):
        line_lower = line.lower()
        # Authors
        if re.match(r"^(authors?|by):\s*", line_lower) and not out.authors:
            rest = re.sub(r"^(authors?|by):\s*", "", line, flags=re.I).strip()
            out.authors = _split_authors(rest)
        # Date
        if re.match(r"^(date|published|year):\s*", line_lower) and not out.date:
            rest = re.sub(r"^(date|published|year):\s*", "", line, flags=re.I).strip()
            out.date = _extract_year(rest) or rest[:50]
        # Venue / conference / journal
        if re.match(r"^(venue|conference|journal|institution):\s*", line_lower):
            out.venue = re.sub(r"^(venue|conference|journal|institution):\s*", "", line, flags=re.I).strip()[:200]
        # Document type hints
        if "abstract" in line_lower and len(line) < 30:
            out.document_type = "research_paper"
        if "project report" in line_lower or "case study" in line_lower:
            out.document_type = "report" if out.document_type != "research_paper" else out.document_type

    if not out.document_type:
        out.document_type = "unknown"

    return out


def _clean(s: str | None) -> str | None:
    if s is None:
        return None
    t = s.strip()
    return t if t else None


def _split_authors(s: str) -> list[str]:
    """Split author string by common separators (comma, semicolon, 'and')."""
    if not s or not s.strip():
        return []
    s = re.sub(r"\s+and\s+", ", ", s, flags=re.I)
    parts = re.split(r"[,;]|\s+and\s+", s)
    return [p.strip() for p in parts if p.strip()][:20]


def _normalize_date(s: str) -> str:
    """Extract YYYY or YYYY-MM from datetime string."""
    if not s:
        return ""
    m = re.search(r"(\d{4})(?:-(\d{2}))?", str(s))
    if m:
        return m.group(0)
    return str(s)[:50]


def _extract_year(s: str) -> str | None:
    m = re.search(r"\b(19|20)\d{2}\b", s)
    return m.group(0) if m else None
