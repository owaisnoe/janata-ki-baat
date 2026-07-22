"""Spread-the-word poster PNGs (spec §6): 1080×1350, Ink & Letterpress,
rendered once per (id, letters-count) and cached to disk."""
from pathlib import Path

from flask import current_app
from PIL import Image, ImageDraw, ImageFont

PAPER = "#F7F3EC"
CARD = "#FBF8F2"
INK = "#171512"
VERM = "#E2401B"
VERM_DEEP = "#B93511"

W, H = 1080, 1350


def _font(name, size, variation=None):
    path = Path(current_app.root_path) / "static" / "fonts" / name
    f = ImageFont.truetype(str(path), size)
    if variation:
        try:
            f.set_variation_by_name(variation)
        except (OSError, ValueError):
            pass
    return f


def render_poster(poster):
    cache = Path(current_app.config["CARD_CACHE_DIR"])
    key = "".join(c for c in (poster["headline"] + poster["hand_line"])
                  if c.isdigit())
    path = cache / f"poster-{poster['id']}-{key}.png"
    if path.exists():
        return path

    dark = poster["theme"] == "dark"
    bg, fg = (INK, PAPER) if dark else (PAPER, INK)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    head = _font("PlayfairDisplay.ttf", 92, "Black")
    hand = _font("Caveat.ttf", 58, "SemiBold")

    d.rectangle([40, 40, W - 40, H - 40], outline=VERM_DEEP, width=3)
    y = 200
    for i, line in enumerate(poster["headline"].split("|")):
        color = VERM if (i == len(poster["headline"].split("|")) - 1 and not dark) else fg
        d.text((90, y), line.strip('"'), font=head, fill=color)
        y += 118
    if poster["hand_line"]:
        d.text((90, y + 60), poster["hand_line"], font=hand, fill=VERM_DEEP if not dark else VERM)
    d.text((90, H - 150), "JANATAKIBAAT.IN", font=_font("PlayfairDisplay.ttf", 40, "Bold"),
           fill=VERM if dark else VERM_DEEP)
    d.text((90, H - 95), "THE PEOPLE'S POST — FROM THE STUDENTS, FOR THE STUDENTS",
           font=_font("PlayfairDisplay.ttf", 24), fill=fg)

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")
    return path
