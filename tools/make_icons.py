"""Draw the app icons (a white shield with a check mark on blue) into fraudshield/static/."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "fraudshield" / "static"
BLUE, WHITE, GREEN = (29, 78, 216), (255, 255, 255), (21, 128, 61)
S = 2048  # draw big, shrink for smooth edges


def shield(scale: float) -> Image.Image:
    im = Image.new("RGB", (S, S), BLUE)
    d = ImageDraw.Draw(im)
    c, w = S / 2, S * scale

    def pt(x, y):  # x, y in -0.5..0.5 of the shield box
        return (c + x * w, c + y * w)

    outline = [pt(0, -0.5), pt(0.42, -0.36), pt(0.42, 0.02), pt(0.32, 0.25), pt(0, 0.5),
               pt(-0.32, 0.25), pt(-0.42, 0.02), pt(-0.42, -0.36)]
    d.polygon(outline, fill=WHITE)
    d.line([pt(-0.2, 0.0), pt(-0.05, 0.16), pt(0.22, -0.16)], fill=GREEN, width=int(w * 0.11), joint="curve")
    return im


for name, size, scale in [("icon-512.png", 512, 0.78), ("icon-192.png", 192, 0.78), ("icon-180.png", 180, 0.78),
                          ("icon-maskable-512.png", 512, 0.58)]:  # maskable keeps the shield in the safe zone
    shield(scale).resize((size, size), Image.LANCZOS).save(OUT / name, optimize=True)
    print(OUT / name)
