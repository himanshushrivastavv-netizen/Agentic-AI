"""Converts INTERVIEW_PREP_GUIDE.md into an executive PDF with beautiful code snippet cards."""
import os
import re
import html
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def md_to_reportlab_xml(text: str) -> str:
    """Escapes XML entities and translates markdown bold, italics, and code tags cleanly."""
    escaped = html.escape(text)
    escaped = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', escaped)
    escaped = re.sub(r'\*(.*?)\*', r'<i>\1</i>', escaped)
    escaped = re.sub(r'`(.*?)`', r'<font face="Courier" color="#b91c1c"><b>\1</b></font>', escaped)
    return escaped

def build_pdf(md_file: str, output_pdf: str):
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=letter,
        rightMargin=32,
        leftMargin=32,
        topMargin=32,
        bottomMargin=32
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    COLOR_PRIMARY = colors.HexColor("#1e3a8a")     # Deep Blue
    COLOR_SECONDARY = colors.HexColor("#0284c7")   # Sky Blue
    COLOR_ACCENT = colors.HexColor("#0f766e")      # Teal
    COLOR_TEXT = colors.HexColor("#1f2937")        # Dark Slate
    COLOR_BG_CARD = colors.HexColor("#f8fafc")     # Light Slate Background
    COLOR_BG_CODE = colors.HexColor("#0f172a")     # Deep Dark Code Background
    COLOR_BORDER = colors.HexColor("#cbd5e1")      # Slate border

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=21,
        textColor=COLOR_PRIMARY,
        spaceAfter=3
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=COLOR_SECONDARY,
        spaceAfter=8
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=COLOR_PRIMARY,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=COLOR_ACCENT,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=COLOR_TEXT,
        spaceAfter=3
    )

    quote_style = ParagraphStyle(
        'QuoteStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.2,
        leading=11.5,
        textColor=colors.HexColor("#334155")
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.2,
        leading=9.5,
        textColor=colors.HexColor("#38bdf8")
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=COLOR_TEXT
    )

    story = []

    # Title Banner
    story.append(Paragraph("🎯 HR & Technical Interview Master Guide", title_style))
    story.append(Paragraph("Project: Agentic AI Desktop Workstation & Autonomous Copilot", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY, spaceAfter=8))

    with open(md_file, "r", encoding="utf-8") as f:
        md_text = f.read()

    lines = md_text.split("\n")
    in_table = False
    table_data = []
    in_code = False
    code_buffer = []

    def flush_table():
        nonlocal in_table, table_data
        if in_table and table_data:
            t = Table(table_data, colWidths=[125, 155, 265])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COLOR_BG_CARD, colors.white]),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(t)
            story.append(Spacer(1, 4))
            in_table = False
            table_data = []

    def flush_code():
        nonlocal in_code, code_buffer
        if in_code and code_buffer:
            raw_code = "\n".join(code_buffer)
            # escape html in code
            escaped_code = html.escape(raw_code).replace(" ", "&nbsp;").replace("\n", "<br/>")
            code_p = Paragraph(f"<b>PYTHON CODE SNIPPET:</b><br/>{escaped_code}", code_style)
            code_table = Table([[code_p]], colWidths=[548])
            code_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_CODE),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#1e293b")),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(code_table)
            story.append(Spacer(1, 5))
            in_code = False
            code_buffer = []

    for line in lines:
        l = line.rstrip()

        # Code block toggle
        if l.startswith("```"):
            if not in_code:
                in_code = True
                code_buffer = []
            else:
                flush_code()
            continue

        if in_code:
            code_buffer.append(l)
            continue

        l_strip = l.strip()
        if not l_strip:
            continue

        if l_strip.startswith("# 🎯 HR") or l_strip.startswith("## Project:"):
            continue

        # Horizontal Rule
        if l_strip == "---":
            flush_table()
            story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER, spaceBefore=3, spaceAfter=5))
            continue

        # Heading 1
        if l_strip.startswith("## "):
            flush_table()
            h_text = l_strip.replace("## ", "").strip()
            story.append(Paragraph(md_to_reportlab_xml(h_text), h1_style))
            continue

        # Heading 2
        if l_strip.startswith("### "):
            flush_table()
            h_text = l_strip.replace("### ", "").strip()
            story.append(Paragraph(md_to_reportlab_xml(h_text), h2_style))
            continue

        # Table Row
        if l_strip.startswith("|") and "|" in l_strip[1:]:
            if "---" in l_strip:
                continue
            cols = [c.strip() for c in l_strip.split("|")[1:-1]]
            if not in_table:
                in_table = True
                table_data = []
                table_data.append([Paragraph(md_to_reportlab_xml(c), table_header_style) for c in cols])
            else:
                table_data.append([Paragraph(md_to_reportlab_xml(c), table_cell_style) for c in cols])
            continue
        else:
            flush_table()

        # Blockquote Card
        if l_strip.startswith(">"):
            raw_quote = l_strip.lstrip(">").strip()
            quote_xml = md_to_reportlab_xml(raw_quote)
            card_p = Paragraph(f"<b>Key Insight / Response:</b><br/>{quote_xml}", quote_style)
            card_table = Table([[card_p]], colWidths=[548])
            card_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_CARD),
                ('BOX', (0, 0), (-1, -1), 1, COLOR_SECONDARY),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(card_table)
            story.append(Spacer(1, 3))
            continue

        # List items
        if l_strip.startswith("- ") or l_strip.startswith("* "):
            item_text = l_strip[2:].strip()
            story.append(Paragraph(f"• {md_to_reportlab_xml(item_text)}", body_style))
            continue

        if re.match(r"^\d+\.\s+", l_strip):
            match = re.match(r"^(\d+)\.\s+(.*)", l_strip)
            num, txt = match.group(1), match.group(2)
            story.append(Paragraph(f"<b>{num}.</b> {md_to_reportlab_xml(txt)}", body_style))
            continue

        # Standard Paragraph
        story.append(Paragraph(md_to_reportlab_xml(l_strip), body_style))

    flush_table()
    flush_code()

    # Build Document
    doc.build(story)
    print(f"PDF successfully generated at: {output_pdf}")

if __name__ == "__main__":
    src_md = os.path.abspath("./INTERVIEW_PREP_GUIDE.md")
    dest_pdf = os.path.abspath("./INTERVIEW_PREP_GUIDE.pdf")
    build_pdf(src_md, dest_pdf)
