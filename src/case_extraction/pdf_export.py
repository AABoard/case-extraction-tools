"""Generate AAB Case Registry PDF from a case JSON (schema-compliant)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
)


def _safe(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return "  ".join(str(x) for x in val)
    return str(val).strip()


def _lines(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if x]
    s = str(val).strip()
    return [s] if s else []


def _block_label_value(style_sheet: Any, label: str, value: Any, body_style: ParagraphStyle) -> list:
    """One label + value block (value can be multiline or list)."""
    parts = []
    if not label and value is None:
        return parts
    lines = _lines(value) if value is not None else []
    if not lines and value is not None:
        lines = [_safe(value)]
    if not lines:
        return parts
    parts.append(Paragraph(f'<b>{label}</b>', style_sheet["Normal"]))
    for line in lines:
        parts.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), body_style))
    return parts


def _section_title(style_sheet: Any, num: int, title: str) -> Paragraph:
    return Paragraph(f'<b>{num}. {title}</b>', style_sheet["Heading2"])


def build_story(case: dict[str, Any], style_sheet: Any) -> list:
    """Build reportlab story (list of flowables) from case dict."""
    body_style = ParagraphStyle(
        "Body",
        parent=style_sheet["Normal"],
        fontSize=10,
        spaceAfter=4,
    )
    small_style = ParagraphStyle(
        "Small",
        parent=style_sheet["Normal"],
        fontSize=9,
        spaceAfter=2,
    )
    story: list = []

    # ----- Header (page 1) -----
    case_type = case.get("case_type") or ""
    status = case.get("status") or ""
    case_id = case.get("case_id") or ""
    summary = case.get("summary") or ""
    story.append(Paragraph(f'Case Type {case_type} &nbsp;&nbsp; Status {status}', style_sheet["Heading2"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f'<b>{case_id}</b>', style_sheet["Heading2"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(summary.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), body_style))
    story.append(Spacer(1, 12))

    org = case.get("implementing_organization") or {}
    lc = case.get("learning_context") or {}
    cl = case.get("classification") or {}
    story.append(Paragraph(f'<b>Organization Type</b><br/>{_safe(org.get("organization_type"))}', body_style))
    story.append(Paragraph(f'<b>Location</b><br/>{_safe(org.get("location"))}', body_style))
    session = _safe(lc.get("session_format"))
    duration = _safe(lc.get("duration"))
    if duration:
        session = f"{session} • {duration}" if session else duration
    story.append(Paragraph(f'<b>Session Format</b><br/>{session}', body_style))
    group = _safe(lc.get("group_size"))
    devices = _safe(lc.get("devices"))
    group_devices = f"{group} • {devices}" if group and devices else (group or devices)
    story.append(Paragraph(f'<b>Group / Devices</b><br/>{group_devices}', body_style))
    story.append(Spacer(1, 8))
    age = _safe(cl.get("age"))
    setting = _safe(cl.get("setting"))
    ai_func = _safe(cl.get("ai_function"))
    pedagogy = _safe(cl.get("pedagogy"))
    risk = _safe(cl.get("risk_level"))
    data_sens = _safe(cl.get("data_sensitivity"))
    story.append(Paragraph(
        f'Age {age} &nbsp;&nbsp; Setting {setting} &nbsp;&nbsp; AI Function {ai_func}<br/>'
        f'Pedagogy {pedagogy} &nbsp;&nbsp; Risk Level {risk} &nbsp;&nbsp; Data Sensitivity {data_sens}',
        small_style,
    ))
    story.append(PageBreak())

    # ----- Section 1: Implementing Organization -----
    story.append(_section_title(style_sheet, 1, "Implementing Organization"))
    story.append(Spacer(1, 6))
    for lbl, key in [("Organization Type", "organization_type"), ("Location", "location"), ("Primary Facilitator Role", "primary_facilitator_role")]:
        for p in _block_label_value(style_sheet, lbl, org.get(key), body_style):
            story.append(p)
    story.append(Spacer(1, 12))

    # ----- Section 2: Learning Context -----
    story.append(_section_title(style_sheet, 2, "Learning Context"))
    story.append(Spacer(1, 6))
    setting_type = lc.get("setting_type")
    if setting_type:
        story.append(Paragraph("<b>Setting Type</b>", style_sheet["Normal"]))
        story.append(Paragraph("  ".join(str(x) for x in setting_type), body_style))
    for lbl, key in [("Session Format", "session_format"), ("Duration", "duration"), ("Group Size", "group_size"), ("Devices", "devices")]:
        for p in _block_label_value(style_sheet, lbl, lc.get(key), body_style):
            story.append(p)
    constraints = lc.get("constraints") or []
    if constraints:
        story.append(Paragraph("<b>Constraints</b>", style_sheet["Normal"]))
        for c in constraints:
            story.append(Paragraph(str(c).replace("&", "&amp;").replace("<", "&lt;"), body_style))
    story.append(Spacer(1, 12))

    # ----- Section 3: Learner Profile -----
    story.append(_section_title(style_sheet, 3, "Learner Profile (Non-identifiable)"))
    story.append(Spacer(1, 6))
    lp = case.get("learner_profile") or {}
    for lbl, key in [("Age Range", "age_range"), ("Prior AI Exposure (Assumed)", "prior_ai_exposure"), ("Prior Programming Background (Assumed)", "prior_programming_background")]:
        for p in _block_label_value(style_sheet, lbl, lp.get(key), body_style):
            story.append(p)
    story.append(Spacer(1, 12))

    # ----- Section 4: Educational Intent -----
    story.append(_section_title(style_sheet, 4, "Educational Intent"))
    story.append(Spacer(1, 6))
    ei = case.get("educational_intent") or {}
    for lbl, key in [
        ("Primary Learning Goals", "primary_learning_goals"),
        ("Secondary Learning Goals", "secondary_learning_goals"),
        ("What This Was Not", "what_this_was_not"),
    ]:
        val = ei.get(key)
        if val is not None:
            for p in _block_label_value(style_sheet, lbl, val, body_style):
                story.append(p)
    story.append(Spacer(1, 12))

    # ----- Section 5: AI Tool Description -----
    story.append(_section_title(style_sheet, 5, "AI Tool Description"))
    story.append(Spacer(1, 6))
    at = case.get("ai_tool") or {}
    for lbl, key in [
        ("Tool Type", "tool_type"),
        ("Languages", "languages"),
        ("AI Role", "ai_role"),
    ]:
        for p in _block_label_value(style_sheet, lbl, at.get(key), body_style):
            story.append(p)
    uim = at.get("user_interaction_model") or []
    if uim:
        story.append(Paragraph("<b>User Interaction Model</b>", style_sheet["Normal"]))
        for line in uim:
            story.append(Paragraph(str(line).replace("&", "&amp;").replace("<", "&lt;"), body_style))
    safeguards = at.get("safeguards") or []
    if safeguards:
        story.append(Paragraph("<b>Safeguards</b>", style_sheet["Normal"]))
        for s in safeguards:
            story.append(Paragraph(str(s).replace("&", "&amp;").replace("<", "&lt;"), body_style))
    story.append(Spacer(1, 12))

    # ----- Section 6: Activity Design -----
    story.append(_section_title(style_sheet, 6, "Activity Design"))
    story.append(Spacer(1, 6))
    ad = case.get("activity_design") or {}
    for lbl, key in [
        ("Activity Flow", "activity_flow"),
        ("Human vs AI Responsibilities", "human_vs_ai_responsibilities"),
        ("Scaffolding Strategies", "scaffolding_strategies"),
    ]:
        val = ad.get(key)
        if val is not None:
            for p in _block_label_value(style_sheet, lbl, val, body_style):
                story.append(p)
    story.append(Spacer(1, 12))

    # ----- Section 7: Observed Challenges -----
    story.append(_section_title(style_sheet, 7, "Observed Challenges (Educators‑Reported)"))
    story.append(Spacer(1, 6))
    for line in _lines(case.get("observed_challenges")):
        story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;"), body_style))
    story.append(Spacer(1, 12))

    # ----- Section 8: Design Adaptations -----
    story.append(_section_title(style_sheet, 8, "Design Adaptations Made"))
    story.append(Spacer(1, 6))
    for line in _lines(case.get("design_adaptations")):
        story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;"), body_style))
    story.append(Spacer(1, 12))

    # ----- Section 9: Reported Outcomes -----
    story.append(_section_title(style_sheet, 9, "Reported Outcomes (Descriptive, Not Measured)"))
    story.append(Spacer(1, 6))
    ro = case.get("reported_outcomes") or {}
    eng = ro.get("engagement")
    if eng is not None:
        for p in _block_label_value(style_sheet, "Engagement", eng, body_style):
            story.append(p)
    for p in _block_label_value(style_sheet, "Learning Signals (Qualitative)", ro.get("learning_signals"), body_style):
        story.append(p)
    for p in _block_label_value(style_sheet, "Educators Reflection", ro.get("educators_reflection"), body_style):
        story.append(p)
    story.append(Spacer(1, 12))

    # ----- Section 10: Ethical & Privacy -----
    story.append(_section_title(style_sheet, 10, "Ethical & Privacy Considerations"))
    story.append(Spacer(1, 6))
    for line in _lines(case.get("ethical_privacy")):
        story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;"), body_style))
    story.append(Spacer(1, 12))

    # ----- Section 11: Evidence Type -----
    story.append(_section_title(style_sheet, 11, "Evidence Type"))
    story.append(Spacer(1, 6))
    for line in _lines(case.get("evidence_type")):
        story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;"), body_style))
    story.append(Spacer(1, 12))

    # ----- Section 12: Research Relevance -----
    story.append(_section_title(style_sheet, 12, "Relevance to AI Education Research"))
    story.append(Spacer(1, 6))
    rr = case.get("research_relevance") or {}
    for p in _block_label_value(style_sheet, "Potential Research Use", rr.get("potential_research_use"), body_style):
        story.append(p)
    for p in _block_label_value(style_sheet, "Relevant Research Domains", rr.get("relevant_research_domains"), body_style):
        story.append(p)
    story.append(Spacer(1, 12))

    # ----- Section 13: Case Status -----
    story.append(_section_title(style_sheet, 13, "Case Status"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f'{_safe(case.get("status"))}', body_style))
    story.append(Spacer(1, 12))

    # ----- Section 14: AAB Classification Tags -----
    story.append(_section_title(style_sheet, 14, "AAB Classification Tags"))
    story.append(Spacer(1, 6))
    for lbl, key in [
        ("Age", "age"),
        ("Setting", "setting"),
        ("AI Function", "ai_function"),
        ("Pedagogy", "pedagogy"),
        ("Risk Level", "risk_level"),
        ("Data Sensitivity", "data_sensitivity"),
    ]:
        for p in _block_label_value(style_sheet, lbl, cl.get(key), body_style):
            story.append(p)
    story.append(Spacer(1, 12))

    # ----- Footer block (text for last page) -----
    case_date = case.get("case_date") or ""
    footer_text = f'Registry: Case &nbsp;&nbsp; ID: {case_id} &nbsp;&nbsp; Case Date: {case_date} &nbsp;&nbsp; AAB • Case Registry'
    story.append(Paragraph(footer_text, small_style))

    return story


def _add_footer(canvas, doc, case: dict[str, Any]) -> None:
    case_id = case.get("case_id") or ""
    case_date = case.get("case_date") or ""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawString(inch, 0.5 * inch, f"Registry: Case  |  ID: {case_id}  |  Case Date: {case_date}  |  AAB • Case Registry")
    canvas.restoreState()


def build_pdf(case: dict[str, Any], output_path: Path, source_url: str | None = None) -> None:
    """Generate AAB Case Registry PDF to output_path. Case must conform to case_schema.json."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    style_sheet = getSampleStyleSheet()
    style_sheet["Heading2"].fontSize = 12
    style_sheet["Heading2"].spaceAfter = 6
    story = build_story(case, style_sheet)

    def _footer(canvas, doc):
        _add_footer(canvas, doc, case)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


def load_case(path: Path) -> dict[str, Any]:
    """Load case JSON (or YAML) from path."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml
        return yaml.safe_load(text) or {}
    return json.loads(text)
