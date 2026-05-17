"""PDF text extraction using pypdf."""

from pathlib import Path

from pypdf import PdfReader


def extract_text_from_pdf(path: str | Path) -> str:
    """
    Extract plain text from a PDF file.

    Args:
        path: Path to the PDF file.

    Returns:
        Extracted text as a single string. Pages are separated by double newlines.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a valid PDF.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected .pdf file, got: {path.suffix}")

    reader = PdfReader(path)
    pages: list[str] = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())

    return "\n\n".join(pages)


def extract_text_from_pdf_with_meta(path: str | Path) -> tuple[str, dict]:
    """
    Extract text and metadata from a PDF.

    Returns:
        Tuple of (full_text, metadata_dict). Metadata may include title, author, subject, creation date.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    reader = PdfReader(path)
    text = extract_text_from_pdf(path)

    meta = reader.metadata
    metadata: dict[str, str | int | None] = {"page_count": len(reader.pages)}

    for key, attr, dict_key in [
        ("title", "title", "/Title"),
        ("author", "author", "/Author"),
        ("subject", "subject", "/Subject"),
        ("creator", "creator", "/Creator"),
    ]:
        val = None
        if meta:
            val = getattr(meta, attr, None) or (meta.get(dict_key) if hasattr(meta, "get") else None)
        metadata[key] = str(val).strip() if val else None

    if meta and hasattr(meta, "creation_date") and meta.creation_date:
        metadata["created"] = str(meta.creation_date)
    elif meta and hasattr(meta, "modification_date") and meta.modification_date:
        metadata["modified"] = str(meta.modification_date)

    return text, metadata
