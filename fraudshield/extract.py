"""Pull links, phone numbers, emails and money amounts out of message text.

Pure text work — nothing here touches the network or opens a link.
"""
from __future__ import annotations

import re

import phonenumbers

# Undo common "defanging" so hxxp://bad[.]com is still caught.
_REFANG = [(re.compile(r"hxxp", re.I), "http"), (re.compile(r"\[\.\]|\(\.\)|\{\.\}"), "."),
           (re.compile(r"\[:\]"), ":")]

_URL = re.compile(r"""(?:https?://|www\.)[^\s<>"'()\[\]]+""", re.I)
# Bare domains such as "usps-redeliver.top/track" (no scheme). Needs a dot and a 2+ letter TLD.
_BARE = re.compile(r"""(?<![@\w.-])((?:[a-z0-9-]+\.)+[a-z]{2,24})(/[^\s<>"']*)?""", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_MONEY = re.compile(r"(?:\$\s?\d[\d,]*(?:\.\d{2})?|\d[\d,]*\s?(?:원|만원|dollars?))", re.I)

# Words that end in a dot+letters but are not domains ("e.g", file names).
_NOT_DOMAINS = {"e.g", "i.e", "a.m", "p.m"}
_FILE_EXT = {"jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt", "mp3", "mp4", "zip"}


def refang(text: str) -> str:
    for pat, rep in _REFANG:
        text = pat.sub(rep, text)
    return text


def urls(text: str) -> list[str]:
    text = refang(text)
    found: list[str] = []
    for m in _URL.finditer(text):
        found.append(m.group(0).rstrip(".,;:!?"))
    emails = {e.split("@", 1)[1].lower() for e in _EMAIL.findall(text)}
    covered = " ".join(found).lower()
    for m in _BARE.finditer(text):
        host = m.group(1).lower()
        if host in _NOT_DOMAINS or host.rsplit(".", 1)[-1] in _FILE_EXT:
            continue
        if host in emails or host in covered:
            continue
        found.append((m.group(1) + (m.group(2) or "")).rstrip(".,;:!?"))
    seen, out = set(), []
    for u in found:
        if u.lower() not in seen:
            seen.add(u.lower())
            out.append(u)
    return out


def phones(text: str, default_region: str = "US") -> list[str]:
    """E.164 numbers found in the text. Korean numbers are tried too."""
    out: list[str] = []
    taken: list[tuple[int, int]] = []  # spans already matched, so KR doesn't re-read a US number
    for region in (default_region, "KR"):
        for m in phonenumbers.PhoneNumberMatcher(text, region):
            if any(m.start < e and s < m.end for s, e in taken):
                continue
            taken.append((m.start, m.end))
            e164 = phonenumbers.format_number(m.number, phonenumbers.PhoneNumberFormat.E164)
            if e164 not in out:
                out.append(e164)
    return out


def emails(text: str) -> list[str]:
    return list(dict.fromkeys(e.lower() for e in _EMAIL.findall(refang(text))))


def money(text: str) -> list[str]:
    return [m.group(0).strip() for m in _MONEY.finditer(text)]
