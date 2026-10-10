"""Small ReportLab building blocks shared by pdf.py."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle

log = logging.getLogger(__name__)

HINDI_FONT = "NotoSansDevanagari"
DECISION_LABEL = {"PENDING": "Pending", "ACCEPTED": "Accepted for field check", "REJECTED": "Not taken forward"}


def register_hindi_font(font_path: Path | None) -> bool:
    """Register the Devanagari font if present. Returns False (with a warning) otherwise; never raises."""
    if HINDI_FONT in pdfmetrics.getRegisteredFontNames():
        return True
    if font_path is None or not font_path.is_file():
        log.warning("Hindi font not found at %s; PDF will be English-only.", font_path)
        return False
    try:
        pdfmetrics.registerFont(TTFont(HINDI_FONT, str(font_path)))
        return True
    except Exception as exc:  # noqa: BLE001 - a bad font must never break report creation
        log.warning("Could not load Hindi font %s (%s); PDF will be English-only.", font_path, exc)
        return False


def para(text: object, style: ParagraphStyle) -> Paragraph:
    """Paragraph with XML-escaped text (ReportLab parses a mini-markup)."""
    return Paragraph(escape(str(text)), style)


def pct(value: object) -> str:
    """0.224 -> '22.4%'. Non-numbers are shown as-is."""
    return f"{float(value) * 100:.1f}%" if isinstance(value, (int, float)) else str(value)


def grid_table(rows: list[list[Any]], widths: list[float]) -> Table:
    """Simple bordered table with a shaded header row."""
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    return table


def summary_rows(audit: dict[str, Any]) -> list[list[str]]:
    """Totals plus the constituency baseline as table rows."""
    summary = audit.get("summary", {})
    rows = [["Measure", "Value"]]
    rows += [[k.replace("_", " "), str(v)] for k, v in summary.get("totals", {}).items()]
    baseline = summary.get("constituency_baseline", {})
    if "deletion_rate" in baseline:
        rows.append(["constituency baseline deletion rate", pct(baseline["deletion_rate"])])
    return rows


def booth_rows(audit: dict[str, Any]) -> list[list[Any]]:
    """Flagged booths as table rows."""
    rows: list[list[Any]] = [["Part", "Removed", "Removal rate", "Risk score", "Flags"]]
    for entry in audit.get("flagged_booths", []):
        b = entry["booth"]
        rows.append([b["part_no"], b["removed"], pct(b["deletion_rate"]), b["risk_score"], b["flag_count"]])
    return rows
