"""Shared utilities: config paths, schema and config loading."""

import json
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parent
CONFIG_ROOT = PACKAGE_ROOT.parent.parent / "config"


def load_config(relative_path: str, default: dict | None = None) -> dict[str, Any]:
    """Load YAML or JSON config from config/relative_path."""
    default = default or {}
    p = CONFIG_ROOT / relative_path
    if not p.exists():
        return default
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in (".yaml", ".yml"):
        import yaml
        out = yaml.safe_load(text)
        return out if isinstance(out, dict) else default
    try:
        out = json.loads(text)
        return out if isinstance(out, dict) else default
    except json.JSONDecodeError:
        return default


def get_prompts_path() -> Path:
    """Path to prompts config (YAML or JSON)."""
    for name in ("extraction_prompts.yaml", "extraction_prompts.yml", "extraction_prompts.json"):
        p = CONFIG_ROOT / "prompts" / name
        if p.exists():
            return p
    return CONFIG_ROOT / "prompts" / "extraction_prompts.yaml"


def load_prompts() -> dict[str, Any]:
    """Load prompts config from config/prompts/. Supports YAML and JSON."""
    for name in ("prompts/extraction_prompts.yaml", "prompts/extraction_prompts.yml", "prompts/extraction_prompts.json"):
        p = CONFIG_ROOT / name
        if p.exists():
            return load_config(name, {})
    return {}


def load_batch_config() -> dict[str, Any]:
    """Load batch pipeline config from config/pipelines/."""
    return load_config("pipelines/batch_config.yaml", {})


def get_schema_path() -> Path:
    """Path to case_schema.json."""
    return CONFIG_ROOT / "schema" / "case_schema.json"


def get_vocabularies_path() -> Path:
    """Path to vocabularies.json."""
    return CONFIG_ROOT / "schema" / "vocabularies.json"


def load_schema() -> dict:
    """Load AAB case JSON schema."""
    p = get_schema_path()
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def load_vocabularies() -> dict:
    """Load controlled vocabularies."""
    p = get_vocabularies_path()
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
