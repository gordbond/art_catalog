"""PDF export of a (filtered) list of paintings, with thumbnails."""
from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .catalog import Catalog, Painting, format_price
from .config import SiteConfig
from .images import jpeg_bytes

THUMB_BOX = 1.8 * inch


def write_pdf(
    catalog: Catalog,
    paintings: list[Painting],
    out: Path,
    *,
    config: SiteConfig,
    subtitle: str = "",
    show_prices: bool = False,
) -> None:
    title, currency = config.title, config.currency
    styles = getSampleStyleSheet()
    name = ParagraphStyle("name", parent=styles["Heading3"], spaceAfter=2)
    body = ParagraphStyle("body", parent=styles["BodyText"], leading=13, textColor=colors.HexColor("#333333"))
    muted = ParagraphStyle("muted", parent=body, textColor=colors.HexColor("#777777"), fontSize=9)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawString(0.7 * inch, 0.45 * inch, f"{title} · {date.today():%B %-d, %Y}")
        canvas.drawRightString(letter[0] - 0.7 * inch, 0.45 * inch, f"Page {doc.page}")
        canvas.restoreState()

    story = [Paragraph(escape(title), styles["Title"])]
    summary = f"{len(paintings)} work{'s' if len(paintings) != 1 else ''}"
    story.append(Paragraph(escape(f"{subtitle} · {summary}" if subtitle else summary), muted))
    story.append(Spacer(1, 0.2 * inch))

    rows = []
    for p in paintings:
        data, (w, h) = jpeg_bytes(catalog.image_path(p), max_side=500)
        scale = THUMB_BOX / max(w, h)
        thumb = Image(BytesIO(data), width=w * scale, height=h * scale)
        details = [Paragraph(escape(p.title), name)]
        lines = [p.medium, p.size_label, str(p.year) if p.year else ""]
        details.append(Paragraph(escape(" · ".join(x for x in lines if x)), body))
        status = p.status_label
        if show_prices and p.price is not None:
            status = f"{status} · {format_price(p.price, currency)}" if status else format_price(p.price, currency)
        details.append(Paragraph(escape(f"{config.category(p.location).label} · {status}".rstrip(" ·")), muted))
        rows.append([thumb, details])

    if rows:
        table = Table(rows, colWidths=[THUMB_BOX + 0.2 * inch, None])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No works match these filters.", body))

    doc = SimpleDocTemplate(
        str(out), pagesize=letter, title=title, author=title,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch, topMargin=0.7 * inch, bottomMargin=0.8 * inch,
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
