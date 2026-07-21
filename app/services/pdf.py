"""All print artefacts (plan §8): the formal A4 letter, the admin print-run
(merged letters + address labels), and the free DIY kit.

Letters are formal, lawful petitions — no satire anywhere in this file's
output (plan §4 register rule).
"""
import io
from xml.sax.saxutils import escape

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .util import ist_now

INK = colors.HexColor("#191111")

BODY = ParagraphStyle(
    "body", fontName="Times-Roman", fontSize=11, leading=16,
    alignment=TA_JUSTIFY, textColor=INK, spaceAfter=8,
)
SENDER = ParagraphStyle("sender", parent=BODY, alignment=TA_RIGHT, spaceAfter=2)
ADDR = ParagraphStyle("addr", parent=BODY, spaceAfter=2, alignment=0)
SUBJECT = ParagraphStyle("subject", parent=BODY, fontName="Times-Bold")
LABEL_TXT = ParagraphStyle(
    "label", fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK,
)
LABEL_HEAD = ParagraphStyle(
    "labelhead", parent=LABEL_TXT, fontName="Helvetica-Bold", fontSize=10,
)
H_DISPLAY = ParagraphStyle(
    "display", fontName="Helvetica-Bold", fontSize=22, leading=26,
    textColor=INK, spaceAfter=10,
)


def _e(text):
    return escape(text or "")


def _letter_date():
    return ist_now().strftime("%d %B %Y")


def _letter_flowables(template, name, city, personal_para=None,
                      reply_address=None, date_str=None):
    cfg = current_app.config
    story = []
    story.append(Paragraph(_e(name), SENDER))
    story.append(Paragraph(_e(city), SENDER))
    story.append(Paragraph(date_str or _letter_date(), SENDER))
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("To,", ADDR))
    for line in cfg["MINISTRY_ADDRESS"].split("\n"):
        story.append(Paragraph(_e(line), ADDR))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph(f"<b>Subject:</b> {_e(template.subject_line)}", SUBJECT))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Respected Sir/Madam,", BODY))

    paras = [p.strip() for p in template.body.split("\n\n") if p.strip()]
    # The user's own paragraph goes in before the formal "on record" closer.
    closing_para = paras[-1]
    for p in paras[:-1]:
        story.append(Paragraph(_e(p), BODY))
    if personal_para and personal_para.strip():
        story.append(Paragraph(_e(personal_para.strip()), BODY))
    story.append(Paragraph(_e(closing_para), BODY))

    if reply_address and reply_address.strip():
        story.append(Paragraph(
            "A reply may kindly be addressed to: "
            + _e(", ".join(l.strip() for l in reply_address.splitlines()
                           if l.strip())),
            BODY,
        ))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Yours faithfully,", BODY))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(f"<b>{_e(name)}</b>", ADDR))
    story.append(Paragraph(_e(city), ADDR))
    story.append(Paragraph("(signed via janatakibaat.in)", ADDR))
    return story


def _doc(buf, title):
    return SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=25 * mm, rightMargin=25 * mm,
        topMargin=22 * mm, bottomMargin=20 * mm,
        title=title, author="Janata Ki Baat",
    )


def letter_pdf(template, name, city, personal_para=None, reply_address=None):
    """Single letter — the write-flow preview and the status-page download."""
    buf = io.BytesIO()
    doc = _doc(buf, f"Letter — {template.subject_line}")
    doc.build(_letter_flowables(template, name, city, personal_para, reply_address))
    buf.seek(0)
    return buf


def _label_table(order):
    cfg = current_app.config
    tier = cfg["TIERS"][order.tier]["label"].upper()
    to_lines = "<br/>".join(_e(l) for l in cfg["MINISTRY_ADDRESS"].split("\n"))
    left = [
        Paragraph(f"{tier} &nbsp;·&nbsp; {order.public_code} &nbsp;·&nbsp; "
                  f"Letter #{order.serial_no}", LABEL_HEAD),
        Spacer(1, 2 * mm),
        Paragraph("<b>To:</b>", LABEL_TXT),
        Paragraph(to_lines, LABEL_TXT),
        Spacer(1, 2 * mm),
        Paragraph(f"<b>From:</b> {_e(order.name)}, {_e(order.city)} "
                  f"(via janatakibaat.in)", LABEL_TXT),
    ]
    t = Table([[left]], colWidths=[160 * mm])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def print_run_pdf(orders):
    """Merged batch: every letter on its own page(s), then cut-out address
    labels. This is the morning-ops artefact (plan §10 step 1)."""
    buf = io.BytesIO()
    doc = _doc(buf, "Janata Ki Baat — Print run")
    story = []
    for order in orders:
        story.extend(_letter_flowables(
            order.template, order.name, order.city,
            order.personal_para, order.reply_address,
        ))
        story.append(PageBreak())

    story.append(Paragraph("ADDRESS LABELS — cut along the boxes", H_DISPLAY))
    story.append(Paragraph(
        f"Batch of {len(orders)} · generated {_letter_date()}", LABEL_TXT))
    story.append(Spacer(1, 6 * mm))
    for order in orders:
        story.append(_label_table(order))
        story.append(Spacer(1, 5 * mm))

    doc.build(story)
    buf.seek(0)
    return buf


DIY_STEPS = [
    ("STEP / 01 — PRINT OR COPY",
     "Print any letter from this kit, or copy it out by hand — a handwritten "
     "letter counts just as much. Fill in your name and city in the blanks, "
     "add today's date, and sign it."),
    ("STEP / 02 — ADDRESS THE ENVELOPE",
     "The Union Minister of Education, Ministry of Education, Government of "
     "India, Shastri Bhawan, Dr. Rajendra Prasad Road, New Delhi – 110001. "
     "Write your own name and address on the back flap."),
    ("STEP / 03 — POST IT",
     "Ordinary post: ₹5 stamp (up to 20 g), no tracking. Speed Post: about "
     "₹41 from most of India at the post office counter — you get a receipt "
     "with a consignment number you can track on indiapost.gov.in."),
    ("STEP / 04 — SHOW IT OFF (OPTIONAL)",
     "Photograph your envelope before you post it and share it with "
     "#JanataKiBaat. Every visible letter tells someone else it can be done."),
]


def diy_kit_pdf(templates):
    """The free tier (plan §5): zero-rupee participation, full instructions."""
    buf = io.BytesIO()
    doc = _doc(buf, "Janata Ki Baat — DIY letter kit")
    story = [
        Paragraph("JANATA KI BAAT — DIY LETTER KIT", H_DISPLAY),
        Paragraph(
            "Post your own letter to the Education Ministry. Costs a stamp. "
            "No sign-up, no payment, nothing owed to us — this kit is free "
            "because the point is the mailbag, not the money.", BODY),
        Spacer(1, 4 * mm),
    ]
    for head, text in DIY_STEPS:
        story.append(Paragraph(f"<b>{head}</b>", BODY))
        story.append(Paragraph(text, BODY))
        story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "Rules of the road: letters are formal petitions. No threats, no "
        "abuse, no incitement — that is what gets a letter logged and read "
        "instead of binned.", BODY))
    story.append(PageBreak())

    for tpl in templates:
        story.append(Paragraph(f"TEMPLATE — {_e(tpl.title)}", H_DISPLAY))
        story.extend(_letter_flowables(
            tpl,
            "__________________________ (your name)",
            "__________________________ (your city)",
        ))
        story.append(PageBreak())

    doc.build(story)
    buf.seek(0)
    return buf
