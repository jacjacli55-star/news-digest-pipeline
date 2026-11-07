"""Render the Markdown digest to a clean PDF using ReportLab (no LaTeX)."""
from __future__ import annotations

import re
from urllib.parse import urlparse
import html as html_lib

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable)


def _clean_text(t: str) -> str:
    # decode HTML entities so we control what ReportLab sees
    t = html_lib.unescape(t or "")
    # strip markdown link syntax to plain text for the PDF body
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    # drop markdown/formatting characters
    t = re.sub(r"[#*_>`~]+", "", t)
    # escape the characters ReportLab treats as markup
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return t


def _pub_link(art) -> str:
    try:
        return urlparse(art.link).netloc
    except Exception:
        return art.link


def build_pdf(md_text: str, verified, stream, title: str, now) -> None:
    text_styles = ParagraphStyle(
        "Body", fontName="Helvetica", fontSize=9.2, leading=13,
        alignment=TA_LEFT, spaceAfter=6, spaceBefore=1,
    )
    h1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=20,
                        leading=24, spaceAfter=2, textColor=colors.HexColor("#1a1a1a"))
    date_s = ParagraphStyle("Date", parent=text_styles, fontSize=9,
                            textColor=colors.HexColor("#777777"))
    h2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13,
                        leading=16, spaceBefore=10, spaceAfter=2,
                        textColor=colors.HexColor("#0b5394"))
    h3 = ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=10.5,
                        leading=13, spaceBefore=7, spaceAfter=1,
                        textColor=colors.HexColor("#000000"))
    meta = ParagraphStyle("Meta", parent=text_styles, fontSize=8.4,
                          leading=11.5, textColor=colors.HexColor("#444444"))
    note = ParagraphStyle("Note", parent=text_styles, fontSize=7.4,
                          leading=10, textColor=colors.HexColor("#888888"))

    doc = SimpleDocTemplate(stream, pagesize=A4,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm,
                            title=title,
                            author="Daily News Digest")

    story = []
    story.append(Paragraph(title, h1))
    story.append(Paragraph(now.strftime("%A, %d %B %Y"), date_s))
    story.append(Spacer(1, 2))
    story.append(HRFlowable(width="100%", thickness=1.2,
                            color=colors.HexColor("#0b5394"), spaceAfter=8))

    by_domain = {}
    for a in verified:
        by_domain.setdefault(a.domain, []).append(a)

    from digest import DOMAIN_LABELS
    for dom in DOMAIN_LABELS:
        if dom not in by_domain:
            continue
        label = DOMAIN_LABELS[dom]
        story.append(Paragraph(label, h2))
        for a in sorted(by_domain[dom], key=lambda x: x.ts, reverse=True):
            story.append(Paragraph(_clean_text(a.title), h3))
            badge = "multi-source" if "corrob" in a.tags else a.source
            rows = [
                ["Source", _clean_text(a.source)],
                ["Status", _clean_text(f"Verified ({badge})")],
                ["Published", _clean_text(a.ts.strftime("%Y-%m-%d %H:%M UTC"))],
                ["Publisher link", f'<link href="{_clean_text(a.link)}" color="#0b5394">{_clean_text(_pub_link(a))}</link>'],
            ]
            tab = Table(rows, colWidths=[26 * mm, None])
            tab.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.6),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]))
            story.append(tab)
            if a.summary:
                prev = _clean_text(a.summary)[:320]
                story.append(Paragraph(f"<b>Summary:</b> {prev}", meta))
            story.append(Spacer(1, 3))
        story.append(Spacer(1, 2))

    story.append(HRFlowable(width="100%", thickness=0.6,
                            color=colors.HexColor("#cccccc"), spaceBefore=4))
    story.append(Paragraph(
        "<b>Credibility note:</b> Automated screening checks source credibility "
        "and multi-outlet corroboration. It does not independently verify every "
        "factual claim sentence-by-sentence; please do a final human review "
        "before redistribution.", note))
    doc.build(story)