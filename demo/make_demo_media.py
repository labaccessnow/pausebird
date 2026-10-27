"""Build the example screenshots: two made-up scam texts drawn like a phone's message screen.

They reuse the made-up senders and links from messages.json (555 numbers, fixture domains),
so the page can show a screenshot check without anyone's real messages.

    python demo/make_demo_media.py      # needs the Noto Sans CJK font (fonts-noto-cjk)
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
OUT = HERE / "media"
FONT = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
BOLD = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
KR = 1  # "Noto Sans CJK KR" inside the .ttc

SHOTS = [
    ("shot-ko-delivery.png", "+82 10-0000-0177", "오늘 오후 2:14",
     "[Web발신]\n[CJ대한통운] 주소지 불일치로 배송이 보류되었습니다. 24시간 내 주소 확인 바랍니다.\n"
     "주소 확인: cj-delivery-kr.top/a1"),
    ("shot-en-toll.png", "+1 (202) 555-0188", "Today 9:02 AM",
     "E-ZPass: You have an unpaid toll balance of $6.99. Pay now to avoid a $50 late fee: "
     "https://ezpass-tolls-pay.vip/pay"),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BOLD if bold else FONT), size, index=KR)


def wrap(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """Break by character, so Korean and long links both fit the bubble."""
    lines = []
    for para in text.split("\n"):
        line = ""
        for ch in para:
            if draw.textlength(line + ch, font=f) > width:
                lines.append(line)
                line = ch
            else:
                line += ch
        lines.append(line)
    return lines


def message_screen(path: Path, sender: str, when: str, text: str) -> None:
    W, H = 1080, 1500
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    d.text((48, 30), "9:41", font=font(40, True), fill="black")
    d.rectangle((0, 110, W, 300), fill="#f2f2f7")
    d.ellipse((W // 2 - 60, 125, W // 2 + 60, 245), fill="#a0a4ad")
    d.text(((W - d.textlength(sender, font=font(38))) / 2, 250), sender, font=font(38), fill="black")
    d.text(((W - d.textlength(when, font=font(30))) / 2, 340), when, font=font(30), fill="#8e8e93")
    f = font(44)
    lines = wrap(d, text, f, 760)
    d.rounded_rectangle((40, 400, 860, 440 + 62 * len(lines)), radius=44, fill="#e9e9eb")
    for i, ln in enumerate(lines):
        d.text((76, 420 + 62 * i), ln, font=f, fill="black")
    d.rounded_rectangle((40, H - 130, W - 40, H - 50), radius=40, outline="#c7c7cc", width=3)
    d.text((80, H - 115), "Text Message", font=font(36), fill="#c7c7cc")
    im.save(path, optimize=True)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for name, sender, when, text in SHOTS:
        message_screen(OUT / name, sender, when, text)
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
