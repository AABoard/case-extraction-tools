"""
Upload handler - single responsibility: receive uploaded files and run extraction.

Uses PaperToCasePipeline (composition); no duplication of extraction logic.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..pipelines import PaperToCasePipeline
from .config import get_web_config, get_upload_dir


@dataclass
class UploadResult:
    """Result of processing an uploaded file."""
    success: bool
    original_filename: str
    case: dict[str, Any] | None = None
    output_files: dict[str, Path] = field(default_factory=dict)
    error: str | None = None


class UploadHandler:
    """Handles file upload and extraction. Config-driven."""

    def __init__(
        self,
        pipeline: PaperToCasePipeline | None = None,
        allowed_extensions: list[str] | None = None,
    ) -> None:
        cfg = get_web_config()
        exts = allowed_extensions or cfg.get("allowed_extensions", [])
        self.allowed_extensions = [e if e.startswith(".") else f".{e}" for e in exts]
        formats = cfg.get("default_export_formats", ["json", "pdf"])
        self.pipeline = pipeline or PaperToCasePipeline(
            export_formats=formats,
            validate_output=True,
        )

    def is_allowed(self, filename: str) -> bool:
        """Check if filename has allowed extension."""
        ext = Path(filename).suffix.lower()
        return ext in [e.lower() for e in self.allowed_extensions]

    def process(self, file_path: Path, original_filename: str | None = None) -> UploadResult:
        """Run extraction on saved file. Returns result with case and output paths."""
        name = original_filename or file_path.name
        if not self.is_allowed(name):
            return UploadResult(
                success=False,
                original_filename=name,
                error=f"Extension not allowed. Use: {', '.join(self.allowed_extensions)}",
            )
        result = self.pipeline.run(file_path, output_dir=file_path.parent)
        if not result.success:
            return UploadResult(success=False, original_filename=name, error=result.error)
        output_files = {}
        stem = file_path.stem
        for ext in [".json", ".pdf", ".html"]:
            p = file_path.parent / f"{stem}_case{ext}"
            if p.exists():
                output_files[ext[1:]] = p
        return UploadResult(
            success=True,
            original_filename=name,
            case=result.case,
            output_files=output_files,
        )
