"""HTML exporter for case records using Jinja2 templates."""

from pathlib import Path
from typing import Any

from ..utils import CONFIG_ROOT
from .base import CaseExporter


def _load_template() -> str:
    """Load HTML template from config; fallback to minimal inline template."""
    for name in ("html_template.html", "case_template.html"):
        p = CONFIG_ROOT / "exporters" / name
        if p.exists():
            return p.read_text(encoding="utf-8")
    return """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{{ case_id }}</title></head><body><h1>{{ case_id }}</h1><pre>{{ case | tojson(indent=2) }}</pre></body></html>"""


class HtmlExporter(CaseExporter):
    """Export case to HTML using config-driven Jinja2 template."""

    def __init__(self, template_path: Path | None = None) -> None:
        self._template_path = template_path

    @property
    def format_name(self) -> str:
        return "HTML"

    @property
    def file_extension(self) -> str:
        return ".html"

    def export(self, case: dict[str, Any], output_path: Path) -> None:
        from jinja2 import Environment, BaseLoader
        template_src = ""
        if self._template_path and self._template_path.exists():
            template_src = self._template_path.read_text(encoding="utf-8")
        else:
            template_src = _load_template()
        env = Environment(loader=BaseLoader())
        tpl = env.from_string(template_src)
        html = tpl.render(case=case)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
