"""Plain text and HTML/Markdown parsing (minimal processing)."""

from pathlib import Path


def extract_from_text(path: str | Path, encoding: str = "utf-8") -> str:
    """
    Read plain text from a file. For .txt, .md, .html.

    Args:
        path: Path to the text file.
        encoding: File encoding.

    Returns:
        File contents as string.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return path.read_text(encoding=encoding)


def extract_from_text_with_meta(path: str | Path, encoding: str = "utf-8") -> tuple[str, dict]:
    """
    Read text and return minimal metadata (filename, size).

    Returns:
        Tuple of (content, metadata_dict).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    content = path.read_text(encoding=encoding)
    metadata = {
        "filename": path.name,
        "size_bytes": path.stat().st_size,
    }
    return content, metadata
