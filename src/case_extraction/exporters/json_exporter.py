"""JSON exporter for case records."""

import json
from pathlib import Path
from typing import Any

from .base import CaseExporter


class JsonExporter(CaseExporter):
    """Export case to JSON."""

    @property
    def format_name(self) -> str:
        return "JSON"

    @property
    def file_extension(self) -> str:
        return ".json"

    def export(self, case: dict[str, Any], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(case, indent=2, default=str), encoding="utf-8")
