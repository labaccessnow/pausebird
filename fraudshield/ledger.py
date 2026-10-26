"""Read a checkbook, or a bank's list of paid checks, from CSV.

Columns: number, amount, payee, date (optional), image (optional, a path next to the CSV).
Header names are matched loosely ("Check #", "Check Number", "Pay To") because every
bank export spells them differently.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from .models import CheckItem

ALIASES = {
    "number": {"number", "check", "check number", "check no", "check #", "check num", "no", "#"},
    "amount": {"amount", "amt", "debit", "check amount"},
    "payee": {"payee", "pay to", "paid to", "pay to the order of", "name"},
    "date": {"date", "posted", "posting date", "date paid", "paid date", "date written"},
    "image": {"image", "image file", "picture"},
}
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y")


def _column(header: str) -> Optional[str]:
    h = " ".join(re.sub(r"[^a-z0-9#]", " ", header.lower()).split())
    return next((k for k, names in ALIASES.items() if h in names), None)


def _date(s: str) -> Optional[dt.date]:
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unknown date '{s}'")


def parse_checks(text: str, image_dir: Optional[Path] = None) -> list[CheckItem]:
    """Raises ValueError with a short, human reason when a row can't be read."""
    rows = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    cols = {h: _column(h) for h in rows.fieldnames or []}
    missing = {"number", "amount", "payee"} - set(cols.values())
    if missing:
        raise ValueError(f"missing column(s): {', '.join(sorted(missing))}")
    out = []
    for line, raw in enumerate(rows, start=2):
        r = {cols[h]: (v or "").strip() for h, v in raw.items() if cols.get(h)}
        if not any(r.values()):
            continue
        try:
            out.append(CheckItem(
                number=int(r["number"].lstrip("#")),
                amount=abs(float(re.sub(r"[$,\s]", "", r["amount"]))),  # some banks show debits as negative
                payee=r["payee"],
                date=_date(r["date"]) if r.get("date") else None,
                image=str(image_dir / r["image"]) if image_dir and r.get("image") else None))
        except (ValueError, ValidationError) as e:
            raise ValueError(f"row {line}: {str(e).splitlines()[0]}") from None
    return out


def read_checks(path: Path) -> list[CheckItem]:
    return parse_checks(Path(path).read_text(encoding="utf-8-sig"), image_dir=Path(path).parent)
