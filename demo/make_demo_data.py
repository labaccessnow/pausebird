"""Build the demo dataset: a made-up checkbook, the checks the bank paid, and check images.

Everything here is fake — names, bank, account and routing numbers. The story it
tells is real-world, though: one check washed (payee and amount changed),
counterfeits printed from the same account numbers, and a duplicate copy.

    python demo/make_demo_data.py
"""
from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
FONTS = Path("/usr/share/fonts/truetype/dejavu")
OWNER = ("DANIEL PARK", "123 SAMPLE STREET", "SPRINGFIELD, VA 22150")
BANK = "EXAMPLE COMMUNITY BANK  (DEMO — NOT A REAL CHECK)"
ROUTING, ACCOUNT = "000000000", "000123456789"

# number, date, payee, amount  — what Daniel actually wrote in his register
REGISTER = [
    (1041, "2026-09-28", "City Water Utility", 84.12),
    (1042, "2026-10-02", "Maple Dental", 160.00),
    (1043, "2026-10-05", "Grace Church", 100.00),
    (1044, "2026-10-09", "Lee's Lawn Care", 120.00),
    (1045, "2026-10-12", "Fairview HOA", 310.00),
]

# What the bank paid. `printed`/`micr` = numbers on the check image; `look` = how it was made.
CLEARED = [
    dict(number=1041, date="2026-09-30", payee="City Water Utility", amount=84.12, micr=1041, look="real"),
    dict(number=1042, date="2026-10-05", payee="Maple Dental", amount=160.00, micr=1042, look="real"),
    dict(number=1043, date="2026-10-14", payee="Quick Cash Services", amount=1100.00, micr=1043, look="washed"),
    dict(number=1044, date="2026-10-13", payee="Lee's Lawn Care", amount=120.00, micr=1044, look="real"),
    dict(number=1045, date="2026-10-15", payee="Fairview HOA", amount=310.00, micr=1045, look="real"),
    dict(number=5032, date="2026-10-16", payee="J. Smith Holdings", amount=2400.00, micr=1046, look="fake"),
    dict(number=1045, date="2026-10-19", payee="Express Check Cashing", amount=1975.00, micr=1045, look="fake"),
]

_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen " \
        "sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def words(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("-" + _ONES[n % 10] if n % 10 else "")
    if n < 1000:
        return _ONES[n // 100] + " hundred" + (" " + words(n % 100) if n % 100 else "")
    return words(n // 1000) + " thousand" + (" " + words(n % 1000) if n % 1000 else "")


def amount_words(a: float) -> str:
    d, c = int(a), round((a - int(a)) * 100)
    return f"{words(d).capitalize()} and {c:02d}/100"


def font(name: str, size: int):
    return ImageFont.truetype(str(FONTS / name), size)


def micr_symbol(d: ImageDraw.ImageDraw, x: int, y: int, kind: str) -> int:
    """Draw the E-13B transit (T) or on-us (U) symbol by hand; returns the next x."""
    k = (10, 10, 10)
    if kind == "T":  # tall bar + two stacked blocks
        d.rectangle([(x + 2, y), (x + 6, y + 26)], fill=k)
        d.rectangle([(x + 10, y), (x + 18, y + 9)], fill=k)
        d.rectangle([(x + 10, y + 17), (x + 18, y + 26)], fill=k)
    else:  # two blocks + low bar
        d.rectangle([(x + 2, y), (x + 8, y + 16)], fill=k)
        d.rectangle([(x + 12, y), (x + 18, y + 16)], fill=k)
        d.rectangle([(x + 2, y + 20), (x + 18, y + 26)], fill=k)
    return x + 24


def draw_check(c: dict, out: Path) -> None:
    W, H = 1200, 540
    paper = (236, 244, 238) if c["look"] != "fake" else (240, 240, 232)  # counterfeit stock is a bit off
    img = Image.new("RGB", (W, H), paper)
    d = ImageDraw.Draw(img)
    for y in range(0, H, 6):  # security pattern
        d.line([(0, y), (W, y)], fill=(226, 236, 229) if c["look"] != "fake" else (232, 232, 224))
    sans, sansb, mono = font("DejaVuSans.ttf", 20), font("DejaVuSans-Bold.ttf", 22), font("DejaVuSansMono.ttf", 30)
    hand = font("DejaVuSerif-Italic.ttf" if (FONTS / "DejaVuSerif-Italic.ttf").exists() else "DejaVuSerif.ttf", 30)
    d.multiline_text((40, 30), "\n".join(OWNER), font=sans, fill=(30, 30, 30), spacing=4)
    d.text((420, 30), BANK, font=font("DejaVuSans.ttf", 16), fill=(60, 60, 90))
    d.text((1080, 30), str(c["number"]), font=sansb, fill=(30, 30, 30))
    d.text((820, 110), "DATE", font=sans, fill=(60, 60, 60))
    d.line([(890, 135), (1150, 135)], fill=(80, 80, 80), width=2)
    d.text((900, 98), c["date"], font=hand, fill=(20, 30, 110))
    d.text((40, 190), "PAY TO THE\nORDER OF", font=sans, fill=(60, 60, 60))
    d.line([(170, 235), (900, 235)], fill=(80, 80, 80), width=2)
    d.rectangle([(930, 195), (1150, 245)], outline=(80, 80, 80), width=2)
    d.text((940, 205), "$", font=sansb, fill=(60, 60, 60))
    d.line([(40, 310), (1150, 310)], fill=(80, 80, 80), width=2)
    d.text((1080, 285), "DOLLARS", font=font("DejaVuSans.ttf", 14), fill=(60, 60, 60))
    d.text((40, 400), "MEMO", font=sans, fill=(60, 60, 60))
    d.line([(110, 425), (520, 425)], fill=(80, 80, 80), width=2)
    d.line([(700, 425), (1150, 425)], fill=(80, 80, 80), width=2)

    ink = (20, 30, 110)
    if c["look"] == "washed":
        # Washed: the original ink was lifted, then re-written — faint ghost of the old text under the new.
        orig = next(r for r in REGISTER if r[0] == c["number"])
        d.text((185, 198), orig[2], font=hand, fill=(205, 215, 210))
        d.text((965, 205), f"{orig[3]:,.2f}", font=hand, fill=(205, 215, 210))
        d.text((50, 270), amount_words(orig[3]), font=hand, fill=(205, 215, 210))
        ink = (25, 25, 25)  # new ink is a different color
    d.text((185, 196), c["payee"], font=hand, fill=ink)
    d.text((965, 203), f"{c['amount']:,.2f}", font=hand, fill=ink)
    d.text((50, 268), amount_words(c["amount"]) + " " + "—" * 6, font=hand, fill=ink)
    d.text((720, 380), "Daniel Park", font=font("DejaVuSerif-Italic.ttf" if (FONTS / "DejaVuSerif-Italic.ttf").exists()
                                                   else "DejaVuSerif.ttf", 36), fill=(20, 30, 110))
    # MICR line: transit symbol, routing, transit, account, on-us symbol, check number
    x = 140
    for part in ("T", ROUTING, "T", "  ", ACCOUNT, "U", "  ", f"{c['micr']:04d}"):
        if part in ("T", "U"):
            x = micr_symbol(d, x, 474, part)
        else:
            d.text((x, 470), part, font=mono, fill=(10, 10, 10))
            x += int(d.textlength(part, font=mono))
    img.save(out)


def main() -> None:
    (HERE / "checks").mkdir(exist_ok=True)
    with open(HERE / "register.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["number", "date", "payee", "amount"])
        w.writerows(REGISTER)
    with open(HERE / "cleared.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["number", "date", "payee", "amount", "image"])
        for i, c in enumerate(CLEARED):
            img = f"checks/{i + 1:02d}-check-{c['number']}.png"
            draw_check(c, HERE / img)
            w.writerow([c["number"], c["date"], c["payee"], f"{c['amount']:.2f}", img])
    print(f"wrote register.csv, cleared.csv and {len(CLEARED)} check images in {HERE}")


if __name__ == "__main__":
    main()
