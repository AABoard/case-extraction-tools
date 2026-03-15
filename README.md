# Case Extraction Tools

Convert research publications, project reports, and educational documentation into structured case entries for the [AAB AI Education Case Registry](https://aaboard.org).

## Phases Implemented

- **Phase 1** — Schema, vocabularies, PDF/DOCX parsers, metadata extraction, PDF export
- **Phase 2** — AI summarizer + field mapping, config-driven prompts, validation
- **Phase 3** — Paper-to-case pipeline, batch ingestion, dataset manifest (CSV)
- **Phase 4** — HTML export, export command, tests

## Setup

```bash
cd case-extraction-tools
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
# Run via script (sets PYTHONPATH)
./run.sh parse document.pdf
./run.sh metadata document.pdf
./run.sh info document.pdf

# Or directly:
PYTHONPATH=src python -m case_extraction.cli parse document.pdf
```

```bash
# Save text to file
./run.sh parse document.pdf -o output.txt

# Extract metadata (title, authors, date, etc.)
./run.sh metadata document.pdf

# Extract AAB case JSON (Phase 2: LLM + validation; requires OPENAI_API_KEY)
./run.sh extract input/ai-report.pdf -o output/case.json
./run.sh extract input/ai-report.pdf -o output/case.json --pdf   # also generate PDF
./run.sh extract input/ai-report.pdf --doc-type policy_report    # hint document type
./run.sh extract input/ai-report.pdf --no-validate               # skip schema validation

# Validate a case JSON
./run.sh validate case.json -o normalized.json

# Save metadata as JSON
./run.sh metadata document.pdf -o meta.json

# Quick summary
./run.sh info document.pdf

# Generate AAB Case Registry PDF from a case JSON (schema-compliant)
./run.sh pdf case.json -o output.pdf

# Export case to PDF, HTML, or JSON (Phase 4)
./run.sh export case.json -f html -o case.html
./run.sh export case.json -f pdf -o case.pdf

# Batch extract from directory or CSV manifest (Phase 3)
./run.sh batch input/ -o output/ -f json -f pdf
./run.sh batch input/ -r  # recurse subdirectories

# Web UI: select and upload files, run extraction (no input folder)
./run.sh serve
# Open http://127.0.0.1:5000 — select files, click Extract, download JSON/PDF
```

Also works with `.docx`, `.txt`, `.md`, `.html` for parse/metadata. PDF generation expects a `.json` (or `.yaml`) case file that conforms to `config/schema/case_schema.json`.

## Project Structure

```
case-extraction-tools/
├── config/
│   ├── schema/          # case_schema.json, vocabularies.json
│   ├── prompts/         # extraction_prompts.yaml (Phase 2)
│   ├── pipelines/       # batch_config.yaml (Phase 3)
│   └── exporters/       # html_template.html (Phase 4)
├── src/case_extraction/
│   ├── parsers/         # PDF, DOCX, text
│   ├── extractors/      # metadata, case_extractor (LLM)
│   ├── validators/      # schema-driven validation
│   ├── pipelines/       # paper_to_case, batch_ingest
│   ├── exporters/       # JSON, PDF, HTML
│   ├── web/             # upload UI, config-driven
│   └── cli.py
├── tests/
├── requirements.txt
└── pyproject.toml
```

### Config (no hardcoding)

- **config/prompts/extraction_prompts.yaml** — LLM prompts. Placeholders: `{schema_json}`, `{classification_tags_json}`, `{document_text}`
- **config/pipelines/batch_config.yaml** — Supported extensions, output patterns, CSV column mapping
- **config/exporters/html_template.html** — Jinja2 HTML export template
- **config/web_config.yaml** — Web upload: allowed extensions, max file size

## Run Tests

```bash
pytest tests/ -v
```

## License

MIT
