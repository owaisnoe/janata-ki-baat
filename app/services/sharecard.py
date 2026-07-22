"""Share cards (plan §6 step 6): server-rendered 1080×1080 and 1080×1920
PNGs in the zine-brutalist system (§7), cached to disk and served static.
"""
from pathlib import Path

from flask import current_app
from PIL import Image, ImageDraw, ImageFont

from .util import ist_now

BAND_BG = "#171512"    # was MAROON — top/bottom band fill
STAMP_RED = "#B93511"
PAPER = "#F7F3EC"
AGED = "#EFE7D8"
INK = "#171512"

# First hit wins — Windows dev box, then common shared-host Linux paths.
DISPLAY_FONTS = [
    "C:/Windows/Fonts/ariblk.ttf",     # Arial Black ≈ Archivo Black
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]
MONO_FONTS = [
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
]

_FONT_DIR = str(Path(__file__).resolve().parent.parent / "static" / "fonts")
DISPLAY_FONTS = [_FONT_DIR + "/PlayfairDisplay.ttf", *DISPLAY_FONTS]


def _font(candidates, size):
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def _wrap(draw, text, font, max_width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _perforation(draw, y, width, color, r=7, gap=34):
    for x in range(gap // 2, width, gap):
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def _postmark(draw, cx, cy, radius, date_str):
    for rr in (radius, radius - 8):
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                     outline=STAMP_RED, width=4)
    f1 = _font(DISPLAY_FONTS, 34)
    f2 = _font(MONO_FONTS, 26)
    draw.text((cx, cy - 22), "POSTED", font=f1, fill=STAMP_RED, anchor="mm")
    draw.text((cx, cy + 24), date_str, font=f2, fill=STAMP_RED, anchor="mm")


def render_card(order, fmt="square"):
    """Renders (or returns cached) card; returns the file path."""
    cache = current_app.config["CARD_CACHE_DIR"]
    key = f"L{order.serial_no}" if order.serial_no else "Q"
    path = Path(cache) / f"{order.public_code}-{key}-{fmt}.png"
    if path.exists():
        return path

    w, h = (1080, 1920) if fmt == "story" else (1080, 1080)
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)

    band = 170 if fmt == "story" else 150
    d.rectangle([0, 0, w, band], fill=BAND_BG)
    d.rectangle([0, h - band + 20, w, h], fill=BAND_BG)
    _perforation(d, band, w, PAPER)
    _perforation(d, h - band + 20, w, PAPER)

    mast = _font(DISPLAY_FONTS, 64)
    sub = _font(MONO_FONTS, 26)
    d.text((w // 2, band // 2 - 12), "JANATA KI BAAT", font=mast,
           fill=PAPER, anchor="mm")
    d.text((w // 2, band // 2 + 40), "VOL. 1 — THE PEOPLE'S POST", font=sub,
           fill=AGED, anchor="mm")

    big = _font(DISPLAY_FONTS, 100 if fmt == "story" else 88)
    margin = 90
    if order.serial_no:
        blocks = [
            (f"LETTER #{order.serial_no:,}", STAMP_RED),
            ("TO THE EDUCATION MINISTRY", INK),
            ("IS IN THE MAIL.", INK),
        ]
    else:
        blocks = [
            ("MY LETTER", STAMP_RED),
            ("TO THE EDUCATION MINISTRY", INK),
            ("IS ON ITS WAY.", INK),
        ]
    lines = []
    for text, color in blocks:
        for ln in _wrap(d, text, big, w - 2 * margin):
            lines.append((ln, color))
    line_h = 118 if fmt == "story" else 104
    total = len(lines) * line_h
    y = (h - total) // 2 - (60 if fmt == "story" else 40)
    for ln, color in lines:
        d.text((margin, y), ln, font=big, fill=color)
        y += line_h

    date_str = (order.posted_at or ist_now()).strftime("%d %b %Y").upper()
    _postmark(d, w - 230, y + 130, 120, date_str)

    small = _font(DISPLAY_FONTS, 40)
    tiny = _font(MONO_FONTS, 30)
    d.text((w // 2, h - band // 2 - 12), "janatakibaat.in", font=small,
           fill=PAPER, anchor="mm")
    d.text((w // 2, h - band // 2 + 42), "CAN'T MARCH? MAIL.", font=tiny,
           fill=AGED, anchor="mm")

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")
    return path
