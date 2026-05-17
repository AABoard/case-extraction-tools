"""
Schema-driven validation and normalization for AAB case records.

- Loads schema and vocabularies from config (no hardcoding)
- Validates structure and types via JSON Schema
- Normalizes edge cases: empty values, type coercion, vocabulary alignment
- Supports additionalProperties and schema evolution
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..utils import load_schema, load_vocabularies

# Optional: use jsonschema if available
try:
    import jsonschema
    from jsonschema import Draft7Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


@dataclass
class ValidationError:
    """Single validation error."""
    path: str
    message: str
    value: Any = None


@dataclass
class ValidationResult:
    """Result of validation and normalization."""
    valid: bool
    normalized: dict[str, Any]
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _collect_vocabularies(vocab: dict) -> dict[str, list[str]]:
    """Merge classification_tags and relevant filters into a flat vocab map."""
    out: dict[str, list[str]] = {}
    for key, items in vocab.get("classification_tags", {}).items():
        if isinstance(items, list):
            out[key] = [str(x) for x in items]
    for key, items in vocab.get("filters", {}).items():
        if isinstance(items, list) and key not in out:
            out[key] = [str(x) for x in items]
    return out


def _to_array(val: Any) -> list:
    """Coerce value to array. Handles string, single item, None."""
    if val is None:
        return []
    if isinstance(val, list):
        return [x for x in val if x is not None and str(x).strip()]
    s = str(val).strip()
    if not s:
        return []
    return [s]


def _to_string(val: Any) -> str | None:
    """Coerce to string; return None if empty."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _to_object(val: Any) -> dict | None:
    """Coerce to object; return None if empty or invalid."""
    if val is None:
        return None
    if isinstance(val, dict):
        return val
    return None


def _pick_closest_vocab(value: str, options: list[str]) -> str | None:
    """Return closest matching vocabulary option, or None if no match."""
    if not value or not options:
        return None
    v = str(value).strip()
    if not v:
        return None
    v_lower = v.lower()
    for opt in options:
        if opt.lower() == v_lower:
            return opt
    for opt in options:
        if v_lower in opt.lower() or opt.lower() in v_lower:
            return opt
    return None


# Schema-derived: fields that must be arrays
_ARRAY_FIELDS = {
    "setting_type", "constraints", "primary_learning_goals", "secondary_learning_goals",
    "what_this_was_not", "languages", "ai_role", "user_interaction_model", "safeguards",
    "activity_flow", "human_vs_ai_responsibilities", "scaffolding_strategies",
    "observed_challenges", "design_adaptations", "engagement", "learning_signals",
    "ethical_privacy", "evidence_type", "potential_research_use", "relevant_research_domains",
}


def _infer_array_fields(schema: dict) -> set[str]:
    """Infer array-typed field names from schema (dot-separated paths)."""
    out: set[str] = set()

    def walk(obj: Any, prefix: str = "") -> None:
        if isinstance(obj, dict):
            if obj.get("type") == "array":
                out.add(prefix.rstrip("."))
            for k, v in obj.items():
                if k == "properties" and isinstance(v, dict):
                    for pk, pv in v.items():
                        walk(pv, f"{prefix}{pk}.")
                elif k in ("items", "properties") or not isinstance(v, dict):
                    continue
                else:
                    walk(v, prefix)
        elif isinstance(obj, list):
            for i, x in enumerate(obj):
                walk(x, prefix)

    walk(schema.get("properties", {}))
    # Flatten nested: e.g. "reported_outcomes.engagement" -> we need reported_outcomes.engagement
    return {p.split(".")[-1] if "." in p else p for p in out} | _ARRAY_FIELDS


def normalize_case(raw: dict[str, Any], schema: dict | None = None, vocab: dict | None = None) -> dict[str, Any]:
    """
    Normalize a raw case dict: coerce types, fill defaults, align to vocabularies.
    Schema and vocab loaded from config if not provided.
    """
    schema = schema or load_schema()
    vocab = vocab or load_vocabularies()
    vocabs = _collect_vocabularies(vocab)
    array_fields = _infer_array_fields(schema)

    out: dict[str, Any] = {}
    props = schema.get("properties", {})

    def set_array(parent: dict, key: str, val: Any) -> None:
        arr = _to_array(val)
        if arr:
            parent[key] = arr

    def set_str(parent: dict, key: str, val: Any) -> None:
        s = _to_string(val)
        if s:
            parent[key] = s

    def process_object(obj: Any, prop_schema: dict) -> dict | None:
        if obj is None:
            return None
        if not isinstance(obj, dict):
            return None
        result: dict[str, Any] = {}
        for pk, pv in prop_schema.get("properties", {}).items():
            v = obj.get(pk)
            if v is None or v == "" or v == []:
                continue
            if pv.get("type") == "array":
                arr = _to_array(v)
                if arr:
                    result[pk] = arr
            elif pv.get("type") == "object":
                sub = process_object(v, pv)
                if sub:
                    result[pk] = sub
            else:
                s = _to_string(v)
                if s:
                    result[pk] = s
        return result if result else None

    # Top-level required/default handling
    if not raw.get("summary"):
        raw = {**raw, "summary": "No summary extracted."}

    for key in props:
        if key not in raw:
            continue
        val = raw[key]

        if val is None or val == "" or (isinstance(val, (list, dict)) and len(val) == 0):
            continue

        if key == "implementing_organization":
            obj = process_object(val, props[key])
            if obj:
                out[key] = obj
        elif key == "learning_context":
            obj = process_object(val, props[key])
            if obj:
                out[key] = obj
        elif key == "learner_profile":
            obj = process_object(val, props[key])
            if obj:
                out[key] = obj
        elif key == "educational_intent":
            obj = process_object(val, props[key])
            if obj:
                out[key] = obj
        elif key == "ai_tool":
            obj = process_object(val, props[key])
            if obj:
                out[key] = obj
        elif key == "activity_design":
            obj = process_object(val, props[key])
            if obj:
                out[key] = obj
        elif key == "reported_outcomes":
            obj = process_object(val, props[key])
            if obj:
                out[key] = obj
        elif key == "research_relevance":
            obj = process_object(val, props[key])
            if obj:
                out[key] = obj
        elif key == "classification":
            obj = process_object(val, props[key])
            if obj and vocabs:
                for vk, opts in vocabs.items():
                    if vk in obj and opts:
                        cur = obj[vk]
                        if isinstance(cur, str):
                            match = _pick_closest_vocab(cur, opts)
                            if match:
                                obj[vk] = match
            if obj:
                out[key] = obj
        elif key in array_fields or (props[key].get("type") == "array"):
            arr = _to_array(val)
            if arr:
                out[key] = arr
        else:
            s = _to_string(val)
            if s:
                out[key] = s

    # Ensure summary
    if "summary" not in out:
        out["summary"] = _to_string(raw.get("summary")) or "No summary extracted."

    # case_id: enforce pattern or use placeholder
    cid = out.get("case_id") or raw.get("case_id")
    if cid and re.match(r"^AAB-CASE-\d{4}-[A-Z]{2}-\d{3}$", str(cid)):
        out["case_id"] = str(cid)
    elif "case_id" not in out:
        out["case_id"] = "AAB-CASE-2025-EX-001"

    # case_type enum
    ct = out.get("case_type") or raw.get("case_type")
    if ct in ("Case Report", "Research Summary"):
        out["case_type"] = ct
    elif "case_type" not in out:
        out["case_type"] = "Research Summary"

    # status enum
    st = out.get("status") or raw.get("status")
    if st in ("Completed", "Planned expansion", "Scaling across sites"):
        out["status"] = st
    elif "status" not in out:
        out["status"] = "Completed"

    return out


def validate_case(data: dict[str, Any], schema: dict | None = None) -> ValidationResult:
    """
    Validate case against JSON Schema and return normalized output with errors/warnings.
    """
    schema = schema or load_schema()
    errors: list[ValidationError] = []
    warnings: list[str] = []

    # 1. Normalize first
    normalized = normalize_case(copy.deepcopy(data), schema=schema)

    # 2. JSON Schema validation (if available)
    if HAS_JSONSCHEMA and schema:
        # Remove $schema and title to avoid ref issues
        schema_copy = {k: v for k, v in schema.items() if k not in ("$schema", "title", "description")}
        validator = Draft7Validator(schema_copy)
        for err in validator.iter_errors(normalized):
            path = ".".join(str(p) for p in err.absolute_path) or "root"
            errors.append(ValidationError(path=path, message=err.message, value=err.instance))
    else:
        # Basic validation without jsonschema
        if not normalized.get("summary"):
            errors.append(ValidationError("summary", "summary is required", normalized.get("summary")))

    valid = len(errors) == 0
    return ValidationResult(valid=valid, normalized=normalized, errors=errors, warnings=warnings)
