"""Human-readable PDF copy of a report (ReportLab). Its hash is stored off-chain only (CONTRACT.md 6.7)."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Spacer

from .pdf_parts import (
    DECISION_LABEL,
    HINDI_FONT,
    booth_rows,
    grid_table,
    para,
    pct,
    register_hindi_font,
    summary_rows,
)


def _flag_section(audit: dict[str, Any], styles: dict[str, ParagraphStyle], use_hindi: bool) -> list[Any]:
    """Each flag with metric, English (and optionally Hindi) explanation, checks and the reviewer decision."""
    out: list[Any] = [para("Flags and reviewer decisions", styles["h2"])]
    for entry in audit.get("flagged_booths", []):
        for flag in entry["flags"]:
            metric, review = flag["metric"], flag["review"]
            out += [
                para(f"Booth {flag['part_no']} · {flag['detector']} · {flag['severity']} ({flag['flag_id']})", styles["h3"]),
                para(f"{metric['name']}: {pct(metric['value'])} (baseline {pct(metric['baseline'])})", styles["small"]),
                para(flag["explanation"]["en"], styles["body"]),
            ]
            if use_hindi:
                out.append(para(flag["explanation"]["hi"], styles["hindi"]))
            out += [para(f"• {check['en']}", styles["small"]) for check in flag.get("recommended_checks", [])]
            note = f" Note: {review['note']}" if review.get("note") else ""
            decision = DECISION_LABEL.get(review["status"], review["status"])
            out.append(para(f"Reviewer decision: {decision}.{note}", styles["small"]))
    return out


def build_pdf(document: dict[str, Any], report_hash: str, hindi_font: Path | None = None) -> bytes:
    """Render the report document to PDF bytes. Hindi text is included only if the font loads."""
    base = getSampleStyleSheet()
    body = base["BodyText"]
    use_hindi = register_hindi_font(hindi_font)
    styles = {
        "body": body, "h1": base["Title"], "h2": base["Heading2"], "h3": base["Heading3"],
        "mono": ParagraphStyle("mono", parent=body, fontName="Courier", fontSize=8, leading=10),
        "small": ParagraphStyle("small", parent=body, fontSize=8, leading=10),
        "hindi": ParagraphStyle("hi", parent=body, fontName=HINDI_FONT if use_hindi else body.fontName),
    }
    audit: dict[str, Any] = document["audit"]

    story: list[Any] = [
        para("VoterGuard India: Electoral-roll revision audit report", styles["h1"]),
        para(f"Report {document['report_id']} · generated {document['generated_at']} · "
             f"reviewer {document['reviewer']['name']}", body),
        para(f"Supersedes: {document.get('supersedes') or 'none'}", styles["small"]),
        para("Synthetic data. This report does not decide anyone's eligibility.", styles["small"]),
        Spacer(1, 4 * mm),
        para("Audit summary", styles["h2"]),
        para(f"{audit.get('ac_name')} (AC {audit.get('ac_no')}), audit {audit.get('audit_id')}", body),
        grid_table(summary_rows(audit), [80 * mm, 50 * mm]),
        Spacer(1, 3 * mm),
        para("Roll snapshot hashes (SHA-256)", styles["h2"]),
    ]
    story += [para(f"{name}: {value}", styles["mono"]) for name, value in audit.get("snapshot_hashes", {}).items()]
    story += [
        Spacer(1, 3 * mm),
        para("Flagged booths", styles["h2"]),
        grid_table(booth_rows(audit), [20 * mm, 25 * mm, 30 * mm, 25 * mm, 20 * mm]),
    ]
    story += _flag_section(audit, styles, use_hindi)

    disclaimer = audit.get("disclaimer", {})
    story += [Spacer(1, 4 * mm), para("Disclaimer", styles["h2"]), para(disclaimer.get("en", ""), body)]
    if use_hindi and disclaimer.get("hi"):
        story.append(para(disclaimer["hi"], styles["hindi"]))
    story += [
        Spacer(1, 4 * mm),
        para("Report hash", styles["h2"]),
        para("SHA-256 of the canonical report JSON file. This PDF is a readable copy; verify the JSON file.",
             styles["small"]),
        para(report_hash, styles["mono"]),
    ]

    buffer = io.BytesIO()
    SimpleDocTemplate(
        buffer, pagesize=A4, title=f"VoterGuard report {document['report_id']}",
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
    ).build(story)
    return buffer.getvalue()
