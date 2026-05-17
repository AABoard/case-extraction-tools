"""Batch ingestion pipeline: process multiple documents."""

from pathlib import Path
from typing import Any, Iterator

from ..utils import load_batch_config
from .paper_to_case import PaperToCasePipeline
from .base import BasePipeline, PipelineResult


class BatchIngestPipeline(BasePipeline):
    """Process multiple documents. Config-driven extensions and output patterns."""

    def __init__(
        self,
        paper_pipeline: PaperToCasePipeline | None = None,
        extensions: list[str] | None = None,
    ) -> None:
        self.paper_pipeline = paper_pipeline or PaperToCasePipeline(export_formats=["json", "pdf"])
        self.extensions = extensions or self._load_extensions()

    def _load_extensions(self) -> list[str]:
        cfg = load_batch_config()
        exts = cfg.get("supported_extensions", [])
        return [e if e.startswith(".") else f".{e}" for e in exts]

    def _discover_inputs(self, input_path: Path, recursive: bool = False) -> list[Path]:
        """Discover document paths from dir or single file."""
        input_path = Path(input_path)
        if input_path.is_file():
            if input_path.suffix.lower() in [e.lower() for e in self.extensions]:
                return [input_path]
            return []
        if not input_path.is_dir():
            return []
        paths: list[Path] = []
        pattern = "**/*" if recursive else "*"
        for p in input_path.glob(pattern):
            if p.is_file() and p.suffix.lower() in [e.lower() for e in self.extensions]:
                paths.append(p)
        return sorted(paths)

    def _iter_csv_manifest(self, csv_path: Path) -> Iterator[tuple[Path, str | None]]:
        """Yield (path, doc_type) from CSV manifest."""
        import csv
        cfg = load_batch_config()
        path_col = cfg.get("csv_columns", {}).get("path", "path")
        doc_type_col = cfg.get("csv_columns", {}).get("doc_type", "doc_type")
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                p = row.get(path_col, "").strip()
                if not p:
                    continue
                path = Path(p)
                if not path.is_absolute():
                    path = csv_path.parent / path
                doc_type = row.get(doc_type_col, "").strip() or None
                yield path, doc_type

    def run(
        self,
        input_path: Path,
        output_dir: Path | None = None,
        recursive: bool = False,
        stop_on_error: bool = False,
        **kwargs: Any,
    ) -> list[PipelineResult]:
        """Process all documents. Returns list of results."""
        input_path = Path(input_path)
        out_dir = Path(output_dir) if output_dir else input_path if input_path.is_dir() else input_path.parent

        if input_path.suffix.lower() == ".csv":
            inputs = [(p, dt) for p, dt in self._iter_csv_manifest(input_path) if p.exists()]
        else:
            inputs = [(p, None) for p in self._discover_inputs(input_path, recursive)]

        results: list[PipelineResult] = []
        for path, doc_type in inputs:
            pipeline = self.paper_pipeline
            if doc_type and hasattr(pipeline, "doc_type_hint"):
                pipeline = PaperToCasePipeline(
                    export_formats=pipeline.export_formats,
                    validate_output=pipeline.validate_output,
                    doc_type_hint=doc_type,
                )
            result = pipeline.run(path, output_dir=out_dir, **kwargs)
            results.append(result)
            if not result.success and stop_on_error:
                break
        return results
