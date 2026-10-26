"""Account Watch: compare checks that CLEARED the bank with checks the person WROTE.

Counterfeit checks reuse the real account and routing numbers, so the bank's own
systems often pay them. The person is the only one who knows which checks are
theirs — this does that comparison for them, every time new checks clear.
"""
from __future__ import annotations

import difflib
import re
from datetime import date, timedelta

from ..models import CheckFinding, CheckItem, Level, Signal

BIG_AMOUNT = 500.0      # first-time payee above this is worth a look
BURST_DAYS = 7          # several unknown checks this close together = a fraud run
BURST_COUNT = 3


def _norm(name: str) -> str:
    name = re.sub(r"[^a-z0-9 ]", " ", name.lower())
    name = re.sub(r"\b(llc|inc|co|corp|company|the)\b", " ", name)
    return " ".join(name.split())


def same_payee(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    return a == b or a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


def _sig(code, weight, evidence, en, ko, hard=False):
    return Signal(code=code, weight=weight, evidence=evidence, detail_en=en, detail_ko=ko, hard=hard)


def review(cleared: list[CheckItem], register: list[CheckItem]) -> list[CheckFinding]:
    """One finding per cleared check (SAFE ones included, so the UI can show a full list)."""
    by_num = {c.number: c for c in register}
    known_payees = [c.payee for c in register]
    nums = sorted(by_num)
    lo, hi = (nums[0], nums[-1]) if nums else (0, 0)
    seen: dict[int, int] = {}
    findings: list[CheckFinding] = []

    for c in sorted(cleared, key=lambda x: (x.date or date.min, x.number)):
        sig: list[Signal] = []
        seen[c.number] = seen.get(c.number, 0) + 1
        mine = by_num.get(c.number)
        money = f"${c.amount:,.2f}"

        if seen[c.number] > 1:
            sig.append(_sig("check.duplicate_number", 60, f"#{c.number}",
                            f"Check #{c.number} was paid twice. One of them is a copy.",
                            f"{c.number}번 수표가 두 번 지급되었습니다. 하나는 위조입니다.", hard=True))
        if mine is None:
            far = nums and (c.number < lo - 25 or c.number > hi + 25)
            sig.append(_sig("check.not_written", 60, f"#{c.number} {money} to {c.payee}",
                            f"You have no record of writing check #{c.number} ({money} to {c.payee})."
                            + (" Its number doesn't even fit your checkbook." if far else ""),
                            f"{c.number}번 수표({c.payee}, {money})를 쓴 기록이 없습니다."
                            + (" 번호도 수표책 번호와 맞지 않습니다." if far else ""), hard=True))
        else:
            if abs(mine.amount - c.amount) >= 0.01:
                sig.append(_sig("check.amount_changed", 60, f"#{c.number}: wrote ${mine.amount:,.2f}, paid {money}",
                                f"You wrote check #{c.number} for ${mine.amount:,.2f}, but the bank paid {money}. "
                                "The amount was changed (check washing).",
                                f"{c.number}번 수표를 ${mine.amount:,.2f}로 썼는데 은행은 {money}를 지급했습니다. "
                                "금액이 바뀌었습니다(수표 세탁).", hard=True))
            if not same_payee(mine.payee, c.payee):
                sig.append(_sig("check.payee_changed", 60, f"#{c.number}: wrote '{mine.payee}', paid '{c.payee}'",
                                f"You made check #{c.number} out to {mine.payee}, but it was cashed by {c.payee}. "
                                "The name was changed (check washing).",
                                f"{c.number}번 수표를 {mine.payee}에게 썼는데 {c.payee}가 받았습니다. "
                                "이름이 바뀌었습니다(수표 세탁).", hard=True))
        if c.micr_number is not None and c.micr_number != c.number:
            sig.append(_sig("check.micr_mismatch", 50, f"printed #{c.number}, bottom line #{c.micr_number}",
                            "The check number printed at the top doesn't match the number in the bank line "
                            "at the bottom — a sign of a fake check.",
                            "수표 위쪽 번호와 아래쪽 은행 번호가 다릅니다 — 위조 수표의 흔적입니다.", hard=True))
        if c.notes:
            sig.append(_sig("check.image_notes", 15, c.notes,
                            f"The check image looks off: {c.notes}",
                            f"수표 이미지가 이상해 보입니다: {c.notes}"))
        if mine is None and c.amount >= BIG_AMOUNT and not any(same_payee(c.payee, p) for p in known_payees):
            sig.append(_sig("check.new_payee_big", 15, f"{c.payee} {money}",
                            f"{c.payee} has never been paid before, and {money} is a large amount.",
                            f"{c.payee}에게는 처음 지급되었고, {money}은 큰 금액입니다."))

        level = Level.SCAM if any(s.hard for s in sig) else (Level.CAUTION if sig else Level.SAFE)
        findings.append(CheckFinding(check=c, level=level, signals=sig))

    # Several unknown checks inside a week = someone is working the account.
    bad = [f for f in findings if f.level == Level.SCAM and f.check.date]
    for f in bad:
        near = [g for g in bad if abs(g.check.date - f.check.date) <= timedelta(days=BURST_DAYS)]
        if len(near) >= BURST_COUNT and not any(s.code == "check.burst" for s in f.signals):
            f.signals.append(_sig("check.burst", 20, f"{len(near)} bad checks within {BURST_DAYS} days",
                                  f"{len(near)} bad checks cleared within {BURST_DAYS} days. "
                                  "Someone has your account numbers — call the bank today.",
                                  f"{BURST_DAYS}일 안에 이상한 수표 {len(near)}장이 지급되었습니다. "
                                  "누군가 계좌 번호를 가지고 있습니다 — 오늘 은행에 전화하세요.", hard=True))
    return findings
