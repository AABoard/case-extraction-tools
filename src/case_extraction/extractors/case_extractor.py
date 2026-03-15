"""
Phase 2: AI summarizer + field mapping with config-driven prompts and validation.

- Loads prompts from config/prompts/ (no hardcoding)
- Loads schema and vocabularies from config
- Validates and normalizes output via validators
- Handles edge cases: empty text, malformed JSON, truncation, doc types
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from ..utils import load_schema, load_vocabularies, load_prompts
from ..validators import validate_case, ValidationResult

# Load .env from project root or .venv/
_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / ".venv" / ".env")

# Config keys (from env or prompts config)
MAX_INPUT_CHARS_KEY = "AAB_MAX_INPUT_CHARS"
DEFAULT_MAX_INPUT_CHARS = 80_000


def _get_max_input_chars() -> int:
    """Read max input chars from env or use default."""
    val = os.environ.get(MAX_INPUT_CHARS_KEY, "")
    if val.isdigit():
        return int(val)
    return DEFAULT_MAX_INPUT_CHARS


def _get_prompt_templates() -> tuple[str, str, str, dict]:
    """Load prompt templates from config. Returns (system, user, truncation, hints)."""
    prompts = load_prompts()
    system = prompts.get("system_template", "").strip()
    user = prompts.get("user_template", "").strip()
    trunc = prompts.get("truncation_notice", "\n\n[... document truncated ...]")
    hints = prompts.get("document_type_hints", {})

    # Fallback when config/prompts/ not found
    if not system:
        system = (
            "You are an expert at extracting structured case records from documents about AI in education. "
            "Produce a JSON object conforming to the provided schema. Use vocabularies when given. "
            "Output ONLY valid JSON, no markdown."
        )
    if not user:
        user = "Document text:\n{document_text}"
    return system, user, trunc, hints


def _build_system_prompt(
    schema: dict,
    vocab: dict,
    document_type_hint: str | None = None,
) -> str:
    """Build system prompt from config templates. Injects schema and vocab dynamically."""
    system_tpl, _, trunc_tpl, hints = _get_prompt_templates()
    schema_json = json.dumps(schema, indent=2)
    tags = vocab.get("classification_tags", {})
    classification_tags_json = json.dumps(tags, indent=2)

    system = system_tpl.replace("{schema_json}", schema_json)
    system = system.replace("{classification_tags_json}", classification_tags_json)
    system = system.replace("{vocab_json}", classification_tags_json)

    if document_type_hint and hints.get(document_type_hint):
        system += "\n\n" + str(hints[document_type_hint])
    return system


def _build_user_content(text: str, truncation_notice: str | None = None) -> str:
    """Format document text for LLM. Truncate if needed."""
    max_chars = _get_max_input_chars()
    trunc = truncation_notice or "\n\n[... document truncated ...]"
    if len(text) > max_chars:
        text = text[:max_chars] + trunc
    return text


def _detect_document_type(text: str) -> str | None:
    """
    Heuristic document-type detection. Returns: case_study, policy_report, research_paper, mixed, or None.
    Used to inject optional hints; does not affect extraction logic.
    """
    if not text or len(text.strip()) < 100:
        return None
    t = text[:3000].lower()
    case_indicators = [
        "afterschool", "summer camp", "workshop", "pilot", "classroom",
        "participants", "learners ages", "age range", "group of",
        "we implemented", "activity flow", "session format",
    ]
    policy_indicators = [
        "policy", "recommendation", "guidance", "department of education",
        "executive order", "blueprint", "guardrails", "legislative",
    ]
    research_indicators = [
        "abstract", "methodology", "findings", "literature review",
        "citation", "references", "study", "experiment", "hypothesis",
    ]
    case_score = sum(1 for w in case_indicators if w in t)
    policy_score = sum(1 for w in policy_indicators if w in t)
    research_score = sum(1 for w in research_indicators if w in t)
    if case_score >= 2 and (policy_score + research_score) < 2:
        return "case_study"
    if policy_score >= 2 and case_score < 2:
        return "policy_report"
    if research_score >= 2 and policy_score < 2:
        return "research_paper"
    if case_score >= 1 and (policy_score >= 1 or research_score >= 1):
        return "mixed"
    return None


def _extract_json_from_response(response: str) -> dict[str, Any]:
    """
    Robustly extract JSON from LLM response. Handles:
    - Raw JSON
    - Markdown code fences
    - Trailing commas (best-effort strip)
    - Multiple JSON objects (takes first)
    """
    raw = response.strip()
    if not raw:
        raise ValueError("LLM returned empty response")

    # Try markdown fence
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        raw = m.group(1).strip()

    # Try to find JSON object
    start = raw.find("{")
    if start >= 0:
        depth = 0
        for i, c in enumerate(raw[start:], start):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    raw = raw[start : i + 1]
                    break

    # Remove trailing commas before ] or }
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}") from e


def _call_llm(system_prompt: str, user_content: str) -> str:
    """Call LLM (OpenAI-compatible). Config from env: OPENAI_API_KEY, AAB_EXTRACT_MODEL, OPENAI_BASE_URL."""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "LLM extraction requires the openai package. Install with: pip install openai"
        )

    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")
    if not api_key:
        raise RuntimeError(
            "Set OPENAI_API_KEY in the environment to use extract. "
            "Get an API key from https://platform.openai.com/api-keys"
        )

    client = OpenAI(api_key=api_key)
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("AAB_EXTRACT_MODEL", "gpt-5-mini")

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_object"},
    }
    if base_url:
        kwargs["base_url"] = base_url

    resp = client.chat.completions.create(**kwargs)
    return (resp.choices[0].message.content or "").strip()


def extract_case_from_text(
    text: str,
    *,
    schema: dict | None = None,
    vocab: dict | None = None,
    document_type_hint: str | None = None,
    skip_llm: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Extract AAB case JSON from document text using an LLM and optional validation.

    Args:
        text: Document text (from any parser: PDF, DOCX, text, etc.)
        schema: Override schema (default: load from config)
        vocab: Override vocabularies (default: load from config)
        document_type_hint: Optional hint: case_study, policy_report, research_paper, mixed
        skip_llm: If True, return minimal placeholder case (for empty/short text)
        validate: If True, run validation and return normalized output

    Returns:
        Validated and normalized case dict.
    """
    schema = schema or load_schema()
    vocab = vocab or load_vocabularies()

    # Edge case: empty or very short text
    cleaned = (text or "").strip()
    if len(cleaned) < 50 and not skip_llm:
        skip_llm = True
    if skip_llm:
        raw = {
            "summary": cleaned or "No content extracted.",
            "case_type": "Research Summary",
            "status": "Completed",
            "case_id": "AAB-CASE-2025-EX-001",
        }
        if validate:
            result = validate_case(raw, schema=schema)
            return result.normalized
        from ..validators import normalize_case
        return normalize_case(raw, schema=schema, vocab=vocab)

    # Auto-detect document type if not provided
    doc_hint = document_type_hint or _detect_document_type(cleaned)

    # Build prompts from config
    system_prompt = _build_system_prompt(schema, vocab, doc_hint)
    doc_text = _build_user_content(cleaned)
    _, user_tpl, _, _ = _get_prompt_templates()
    if user_tpl and "{document_text}" in user_tpl:
        user_content = user_tpl.replace("{document_text}", doc_text)
    else:
        user_content = f"Document text:\n\n{doc_text}"

    # Call LLM
    response = _call_llm(system_prompt, user_content)

    # Parse JSON
    raw = _extract_json_from_response(response)

    # Validate and normalize
    if validate:
        result = validate_case(raw, schema=schema)
        return result.normalized

    from ..validators import normalize_case
    return normalize_case(raw, schema=schema, vocab=vocab)
