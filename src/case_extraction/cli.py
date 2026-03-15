"""CLI for Case Extraction Tools."""

import json
from pathlib import Path

import click

from .parsers import extract_text_from_pdf, extract_text_from_docx, extract_from_text
from .parsers.pdf_parser import extract_text_from_pdf_with_meta
from .parsers.docx_parser import extract_text_from_docx_with_meta
from .parsers.text_parser import extract_from_text_with_meta
from .extractors.metadata import extract_metadata, ExtractedMetadata
from .extractors.case_extractor import extract_case_from_text
from .pdf_export import build_pdf, load_case
from .validators import validate_case
from .pipelines import PaperToCasePipeline, BatchIngestPipeline
from .exporters import get_exporter, get_exporters_for_formats


def _to_json_serializable(obj: object) -> object:
    """Convert dataclass to JSON-serializable dict."""
    if hasattr(obj, "__dict__"):
        return {k: _to_json_serializable(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    if isinstance(obj, (list, tuple)):
        return [_to_json_serializable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    return obj


def _parse_document(path: Path) -> tuple[str, dict | None, str]:
    """Parse document and return (text, embedded_meta, format)."""
    sfx = path.suffix.lower()
    if sfx == ".pdf":
        text, meta = extract_text_from_pdf_with_meta(path)
        return text, meta, "pdf"
    if sfx in (".docx", ".doc"):
        text, meta = extract_text_from_docx_with_meta(path)
        return text, meta, "docx"
    if sfx in (".txt", ".md", ".html"):
        text, meta = extract_from_text_with_meta(path)
        return text, meta or {}, "text"
    raise click.BadParameter(f"Unsupported format: {sfx}. Use .pdf, .docx, .txt, .md, .html")


@click.group()
@click.version_option(version="0.2.0", prog_name="case-extract")
def main() -> None:
    """Convert research docs into AAB Case Registry entries."""


@main.command("parse")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Write text to file")
@click.option("--max-chars", default=0, help="Truncate output (0 = no limit)")
def parse(path: Path, output: Path | None, max_chars: int) -> None:
    """Parse a PDF, DOCX, or text file and extract plain text."""
    text, meta, fmt = _parse_document(path)
    if max_chars > 0:
        text = text[:max_chars] + ("..." if len(text) > max_chars else "")

    if output:
        output.write_text(text, encoding="utf-8")
        click.echo(f"Wrote {len(text)} chars to {output}")
    else:
        click.echo(text)


@main.command("metadata")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Write JSON to file")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output raw JSON")
def metadata(path: Path, output: Path | None, as_json: bool) -> None:
    """Extract metadata from a document (Phase 1: heuristics + embedded meta)."""
    text, embedded_meta, _ = _parse_document(path)
    meta = extract_metadata(text, embedded_meta, source_filename=path.name)

    data = _to_json_serializable(meta)
    payload = json.dumps(data, indent=2, default=str)

    if output:
        output.write_text(payload, encoding="utf-8")
        click.echo(f"Wrote metadata to {output}")
    else:
        click.echo(payload)


@main.command("extract")
@click.argument("path", type=click.Path(exists=True, path_type=Path), metavar="DOCUMENT")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output case JSON path (default: DOCUMENT_case.json)")
@click.option("--pdf", "gen_pdf", is_flag=True, help="Also generate AAB Case Registry PDF")
@click.option("--no-validate", is_flag=True, help="Skip schema validation (use raw LLM output)")
@click.option("--doc-type", type=click.Choice(["case_study", "policy_report", "research_paper", "mixed"]), default=None, help="Hint document type for extraction")
def extract(path: Path, output: Path | None, gen_pdf: bool, no_validate: bool, doc_type: str | None) -> None:
    """Extract AAB case JSON from a PDF, DOCX, or text file. Uses LLM + validation (Phase 2)."""
    text, _, _ = _parse_document(path)
    case = extract_case_from_text(
        text,
        document_type_hint=doc_type,
        validate=not no_validate,
    )
    out_json = output or path.with_name(path.stem + "_case.json")
    out_json.write_text(json.dumps(case, indent=2, default=str), encoding="utf-8")
    click.echo(f"Wrote case JSON to {out_json}")
    if gen_pdf:
        out_pdf = out_json.with_suffix(".pdf")
        build_pdf(case, out_pdf)
        click.echo(f"Wrote AAB Case Registry PDF to {out_pdf}")


@main.command("validate")
@click.argument("case_json", type=click.Path(exists=True, path_type=Path), metavar="CASE.json")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Write normalized JSON to file")
def validate_cmd(case_json: Path, output: Path | None) -> None:
    """Validate a case JSON against schema and optionally write normalized output."""
    import json
    case = load_case(case_json)
    result = validate_case(case)
    if result.valid:
        click.echo("Valid.")
    else:
        for e in result.errors:
            click.echo(f"Error [{e.path}]: {e.message}", err=True)
        raise SystemExit(1)
    if output:
        output.write_text(json.dumps(result.normalized, indent=2, default=str), encoding="utf-8")
        click.echo(f"Wrote normalized JSON to {output}")


@main.command("batch")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path), metavar="DIR|FILE|MANIFEST.csv")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output directory")
@click.option("--formats", "-f", multiple=True, default=["json"], help="Export formats (json, pdf, html). Default: json")
@click.option("--recursive", "-r", is_flag=True, help="Recurse into subdirectories")
@click.option("--stop-on-error", is_flag=True, help="Stop on first failure")
@click.option("--no-validate", is_flag=True, help="Skip schema validation")
def batch(input_path: Path, output: Path | None, formats: tuple[str, ...], recursive: bool, stop_on_error: bool, no_validate: bool) -> None:
    """Batch extract from directory, single file, or CSV manifest (Phase 3)."""
    pipeline = BatchIngestPipeline(
        paper_pipeline=PaperToCasePipeline(
            export_formats=list(formats) if formats else ["json"],
            validate_output=not no_validate,
        ),
    )
    results = pipeline.run(input_path, output_dir=output, recursive=recursive, stop_on_error=stop_on_error)
    ok = sum(1 for r in results if r.success)
    fail = sum(1 for r in results if not r.success)
    for r in results:
        if r.success:
            click.echo(f"OK {r.source_path} -> {r.output_path}")
        else:
            click.echo(f"FAIL {r.source_path}: {r.error}", err=True)
    click.echo(f"Done: {ok} succeeded, {fail} failed")
    if fail:
        raise SystemExit(1)


@main.command("export")
@click.argument("case_json", type=click.Path(exists=True, path_type=Path), metavar="CASE.json")
@click.option("--format", "-f", "fmt", type=click.Choice(["json", "pdf", "html"]), default="pdf", help="Export format")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output path")
def export_cmd(case_json: Path, fmt: str, output: Path | None) -> None:
    """Export case JSON to PDF, HTML, or JSON (Phase 4)."""
    case = load_case(case_json)
    exporter = get_exporter(fmt)
    out = output or case_json.with_suffix(exporter.file_extension)
    exporter.export(case, out)
    click.echo(f"Wrote {exporter.format_name} to {out}")


@main.command("pdf")
@click.argument("case_json", type=click.Path(exists=True, path_type=Path), metavar="CASE.json")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output PDF path (default: CASE.pdf)")
def pdf(case_json: Path, output: Path | None) -> None:
    """Generate AAB Case Registry PDF from a schema-compliant case JSON file."""
    case = load_case(case_json)
    out = output or case_json.with_suffix(".pdf")
    build_pdf(case, out)
    click.echo(f"Wrote {out}")


@main.command("serve")
@click.option("--host", default="127.0.0.1", help="Bind host")
@click.option("--port", type=int, default=5000, help="Bind port")
def serve(host: str, port: int) -> None:
    """Start web server for file upload and extraction."""
    from .web import create_app
    app = create_app()
    click.echo(f"Open http://{host}:{port} to upload files")
    app.run(host=host, port=port, debug=False)


@main.command("info")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def info(path: Path) -> None:
    """Show parse + metadata summary (no file output)."""
    path = Path(path)
    if not path.exists():
        raise click.FileError(str(path), "File not found")

    text, embedded_meta, fmt = _parse_document(path)
    meta = extract_metadata(text, embedded_meta, source_filename=path.name)

    click.echo(f"Format: {fmt}")
    click.echo(f"Text length: {len(text)} chars")
    click.echo(f"Title: {meta.title or '(none)'}")
    click.echo(f"Authors: {', '.join(meta.authors) if meta.authors else '(none)'}")
    click.echo(f"Date: {meta.date or '(none)'}")


if __name__ == "__main__":
    main()
