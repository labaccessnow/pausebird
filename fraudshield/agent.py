"""Ties the checks together into one verdict a parent can act on.

Order matters: rules first (fast, explainable, can't be talked out of a hit),
then the model's opinion on top. The model can raise the risk, never lower a
hard rule hit — that's what keeps the verdict verifiable.
"""
from __future__ import annotations

import mimetypes
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

from . import extract, playbooks
from .checks import accounts, links, patterns, phones
from .llm.base import Brain, OfflineBrain
from .models import CheckFinding, CheckItem, Level, Message, Signal, Verdict

SCAM_SCORE = 60
CAUTION_SCORE = 25
MODEL_MAX_WEIGHT = 30


def _dedupe(signals: list[Signal]) -> list[Signal]:
    seen, out = set(), []
    for s in signals:
        key = (s.code, s.evidence.lower())
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def _level(score: int, signals: list[Signal]) -> Level:
    if any(s.hard for s in signals) or score >= SCAM_SCORE:
        return Level.SCAM
    return Level.CAUTION if score >= CAUTION_SCORE else Level.SAFE


_HEAD = {
    Level.SCAM: ("This looks like a SCAM.", "사기로 보입니다."),
    Level.CAUTION: ("Be careful — some signs of a scam.", "조심하세요 — 사기 징후가 있습니다."),
    Level.SAFE: ("No scam signs found.", "사기 징후가 보이지 않습니다."),
}


def _summary(level: Level, signals: list[Signal]) -> tuple[str, str]:
    top = sorted(signals, key=lambda s: -s.weight)[:3]
    en, ko = _HEAD[level]
    if top:
        en += " " + " ".join(s.detail_en for s in top)
        ko += " " + " ".join(s.detail_ko for s in top)
    return en, ko


def message_signals(msg: Message, rdap: Optional[Callable[[str], Optional[int]]] = None) -> list[Signal]:
    text = msg.text
    sig = patterns.scan(text)
    for url in extract.urls(text):
        sig += links.analyze_url(url, rdap)
    nums = extract.phones(text)
    if msg.sender:
        nums += [n for n in extract.phones(msg.sender) if n not in nums]
    for n in nums:
        sig += phones.analyze_number(n)
    senders = extract.emails(text) + extract.emails(msg.sender or "")
    for e in senders:
        # A sender address is just a domain to judge, like a link.
        sig += [s for s in links.analyze_url(e.split("@", 1)[1], rdap) if s.code.startswith("link.")]
    return _dedupe(sig)


def check_message(msg: Message, brain: Optional[Brain] = None, online: bool = False,
                  rdap: Optional[Callable[[str], Optional[int]]] = None) -> Verdict:
    brain = brain or OfflineBrain()
    if online and rdap is None:
        rdap = links.rdap_age_days
    sig = message_signals(msg, rdap if online or rdap else None)

    opinion = brain.judge(msg.text, sig)
    if opinion:
        weight, why = opinion
        weight = max(0, min(MODEL_MAX_WEIGHT, weight))
        if weight:
            sig.append(Signal(code="model.judgement", weight=weight, evidence=why[:200],
                              detail_en=why, detail_ko=why))

    score = min(100, sum(s.weight for s in sig))
    level = _level(score, sig)
    en, ko = _summary(level, sig)
    plain = brain.explain(msg, sig, level) or {}
    return Verdict(level=level, score=score, signals=sig,
                   summary_en=plain.get("en") or en, summary_ko=plain.get("ko") or ko,
                   next_steps=playbooks.steps("message") if level != Level.SAFE else [],
                   model_opinion=opinion[1] if opinion else None)


def read_check_images(cleared: list[CheckItem], brain: Brain) -> list[CheckItem]:
    """Let the model look at each paid check. The bank's number, amount and payee stay as the
    bank reported them; the eyes add the MICR number and any signs of tampering."""
    def look(c: CheckItem) -> CheckItem:
        if not c.image:
            return c
        mime = mimetypes.guess_type(c.image)[0] or "image/png"
        seen = brain.read_check(Path(c.image).read_bytes(), mime)
        return c.model_copy(update={"micr_number": seen.micr_number, "notes": seen.notes}) if seen else c

    # One model call per check; four at a time instead of one after another.
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(look, cleared))


def check_account(cleared: list[CheckItem], register: list[CheckItem]) -> tuple[Verdict, list[CheckFinding]]:
    findings = accounts.review(cleared, register)
    bad = [f for f in findings if f.level != Level.SAFE]
    sig = _dedupe([s for f in bad for s in f.signals])
    level = max((f.level for f in findings), default=Level.SAFE)
    score = min(100, sum(s.weight for s in sig))
    n_bad = sum(f.level == Level.SCAM for f in findings)
    if n_bad:
        total = sum(f.check.amount for f in findings if f.level == Level.SCAM)
        en = f"{n_bad} check(s) you didn't write were paid, ${total:,.2f} in total. Call your bank today."
        ko = f"직접 쓰지 않은 수표 {n_bad}장이 지급되었습니다. 합계 ${total:,.2f}. 오늘 은행에 전화하세요."
    else:
        en, ko = _summary(level, sig)
    return (Verdict(level=level, score=score, signals=sig, summary_en=en, summary_ko=ko,
                    next_steps=playbooks.steps("fake_checks") if level == Level.SCAM else []),
            findings)
