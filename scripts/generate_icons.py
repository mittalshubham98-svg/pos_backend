#!/usr/bin/env python3
"""Generate the two PWA app icons (192x192, 512x512) shared by both the customer app and
admin portal manifests, from brand colours only — no external image asset dependency.

Usage:
    python -m scripts.generate_icons

Run from the project root, with the virtualenv from requirements.txt active (Pillow>=10.2
is already a backend dependency, see requirements.txt).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from app.config import settings  # noqa: E402

BG = "#201e1d"      # near-black, matches customer.html body background
FG = "#ec3013"      # brand orange, matches the accent colour used throughout both UIs
MONOGRAM = "PS"

# Common bold sans-serif TrueType fonts to try, in order, across Windows/Linux/mac dev and
# deployment environments. Falls back to Pillow's bundled scalable default font (Pillow>=10.1)
# if none of these are present, so icon generation never hard-fails.
FONT_CANDIDATES = [
    "arialbd.ttf",                                                    # Windows
    "seguisb.ttf",                                                    # Windows (Segoe UI Semibold)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",           # Linux (fonts-dejavu-core)
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",   # Linux (fonts-liberation)
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",              # macOS
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def make_icon(size: int) -> Image.Image:
    """Rounded-square mark so it looks intentional even where a launcher shows the raw
    PNG (e.g. the install banner's own preview), rather than a hard box around it."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    radius = round(size * 0.22)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=BG)

    font = _load_font(round(size * 0.5))
    bbox = draw.textbbox((0, 0), MONOGRAM, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = ((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1])
    draw.text(pos, MONOGRAM, font=font, fill=FG)
    return img


def main() -> None:
    icons_dir = settings.STATIC_DIR / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        out_path = icons_dir / f"icon-{size}.png"
        make_icon(size).save(out_path, "PNG")
        print(f"wrote {out_path} ({size}x{size})")


if __name__ == "__main__":
    main()
