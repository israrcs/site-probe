from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.models import Issue

ACCENT = (239, 68, 68, 255)        # red-500 outline
FILL = (239, 68, 68, 38)           # translucent red
CHIP_BG = (239, 68, 68, 235)
CHIP_TEXT = (255, 255, 255, 255)


def annotate_and_crop(
    full_png: Path,
    issue: Issue,
    out_annotated: Path,
    out_element: Path,
    pad: int = 32,
) -> None:
    """Draw a red box + label chip over the issue location on the full-page
    screenshot, save it, and save a zoomed crop of the element area."""
    img = Image.open(full_png).convert("RGB")
    overlay = ImageDraw.Draw(img, "RGBA")

    b = issue.bounding_box
    assert b is not None
    x1 = max(0, int(b.x))
    y1 = max(0, int(b.y))
    x2 = min(img.width, int(b.x + b.width))
    y2 = min(img.height, int(b.y + b.height))

    if x2 - x1 < 6 or y2 - y1 < 6:
        # Degenerate box: draw a visible marker around the point instead.
        cx = min(max(int(b.x), 20), img.width - 20)
        cy = min(max(int(b.y), 20), img.height - 20)
        x1, y1, x2, y2 = cx - 20, cy - 20, cx + 20, cy + 20

    overlay.rectangle([x1, y1, x2, y2], fill=FILL, outline=ACCENT, width=3)

    try:
        font = ImageFont.load_default(16)
    except TypeError:  # Pillow < 10.1
        font = ImageFont.load_default()
    label = f"{issue.category.value} · {issue.severity.value}"
    tw = overlay.textlength(label, font=font)
    chip_h = 20
    chip_y = y1 - chip_h - 2 if y1 - chip_h - 2 > 0 else y1 + 2
    overlay.rectangle([x1, chip_y, x1 + tw + 10, chip_y + chip_h], fill=CHIP_BG)
    overlay.text((x1 + 5, chip_y + 2), label, fill=CHIP_TEXT, font=font)

    out_annotated.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_annotated, "PNG")

    cx1 = max(0, x1 - pad)
    cy1 = max(0, y1 - pad)
    cx2 = min(img.width, x2 + pad)
    cy2 = min(img.height, y2 + pad)
    img.crop((cx1, cy1, cx2, cy2)).save(out_element, "PNG")
