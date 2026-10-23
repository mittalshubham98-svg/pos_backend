"""Generates the app's icon set (brand red, white "PS" monogram) into mobile/assets.
Run from the repo root with the backend venv, which already has Pillow:
    .venv\\Scripts\\python.exe mobile\\scripts\\make-icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "assets"
RED = (236, 48, 19, 255)
INK = (32, 30, 29, 255)
WHITE = (255, 255, 255, 255)
FONT = "C:/Windows/Fonts/segoeuib.ttf"


def monogram(size: int, fill, bg, scale: float) -> Image.Image:
    img = Image.new("RGBA", (size, size), bg)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, int(size * scale))
    box = draw.textbbox((0, 0), "PS", font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text(((size - w) / 2 - box[0], (size - h) / 2 - box[1]), "PS", font=font, fill=fill)
    # Underline bar — a nod to the "speed" in SpeedBuy without needing artwork.
    bar_w, bar_h = int(w * 0.9), max(4, int(size * 0.035))
    top = (size + h) / 2 + size * 0.05
    draw.rounded_rectangle(((size - bar_w) / 2, top, (size + bar_w) / 2, top + bar_h), radius=bar_h // 2, fill=fill)
    return img


# Launcher icon (iOS + legacy Android): full-bleed red square.
monogram(1024, WHITE, RED, 0.42).save(ASSETS / "icon.png")
# Android adaptive icon: the launcher crops to the centre ~66%, so the mark stays small.
monogram(1024, WHITE, (0, 0, 0, 0), 0.30).save(ASSETS / "android-icon-foreground.png")
Image.new("RGBA", (1024, 1024), RED).save(ASSETS / "android-icon-background.png")
monogram(1024, WHITE, (0, 0, 0, 0), 0.30).save(ASSETS / "android-icon-monochrome.png")
# Splash: red mark on the white splash background.
monogram(1024, RED, (0, 0, 0, 0), 0.42).save(ASSETS / "splash-icon.png")
monogram(48, WHITE, RED, 0.42).save(ASSETS / "favicon.png")
print("icons written to", ASSETS)
