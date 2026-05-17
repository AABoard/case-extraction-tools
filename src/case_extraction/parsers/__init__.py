"""Document parsers for PDF, DOCX, and plain text."""

from .pdf_parser import extract_text_from_pdf
from .docx_parser import extract_text_from_docx
from .text_parser import extract_from_text

__all__ = ["extract_text_from_pdf", "extract_text_from_docx", "extract_from_text"]
