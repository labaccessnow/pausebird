"""Scam wording in English and Korean.

These are the classic pressure tricks: urgency, fear, family emergencies, odd
payment methods, "verify your account". One hit is a hint; several together
is the shape of a scam. The LLM gets these as evidence, it doesn't replace them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import Signal


@dataclass(frozen=True)
class Pattern:
    code: str
    weight: int
    regex: re.Pattern
    en: str
    ko: str


def _p(code, weight, rx, en, ko):
    return Pattern(code, weight, re.compile(rx, re.I), en, ko)


PATTERNS: list[Pattern] = [
    _p("msg.urgency", 10,
       r"\b(urgent|immediately|right away|within 24 hours|final (notice|warning)|act now|today only)\b"
       r"|긴급|즉시|오늘 안에|24시간|마지막 (경고|안내)",
       "It rushes you. Scammers want you to act before you think.",
       "서두르게 만듭니다. 사기꾼은 생각할 시간을 주지 않으려 합니다."),
    _p("msg.account_threat", 20,
       r"\b(account|card) (has been |is |was )?(suspended|locked|restricted|disabled|on hold)\b"
       r"|unusual (activity|sign-?in)|계좌.{0,6}(정지|중지|잠금)|이상 거래|해외 ?결제",
       "It says your account is locked or has strange activity — a common way to scare you.",
       "계좌가 정지되었거나 이상 거래가 있다고 겁을 줍니다 — 흔한 사기 수법입니다."),
    _p("msg.verify_identity", 20,
       r"\b(verify|confirm|update) (your )?(account|identity|information|details|payment)\b"
       r"|본인 ?인증|정보 ?(확인|입력)|인증번호",
       "It asks you to 'verify' your details. Real banks don't ask this by text.",
       "정보를 '확인'하라고 합니다. 진짜 은행은 문자로 이런 요청을 하지 않습니다."),
    _p("msg.odd_payment", 30,
       r"\b(gift ?cards?|bitcoin|crypto|wire transfer|western union|moneygram|zelle|cash ?app|venmo|"
       r"apple card|google play card|steam card)\b|상품권|기프트 ?카드|코인|가상화폐",
       "It asks for payment by gift card, crypto, wire or a payment app. Those can't be taken back.",
       "상품권, 코인, 송금 앱으로 돈을 보내라고 합니다. 이런 돈은 되돌릴 수 없습니다."),
    _p("msg.safe_account", 35,
       # 안정: speech-to-text often hears a phone-quality 안전 as 안정
       r"\bsafe (bank )?account\b|\bmove your money\b.{0,30}\b(protect|safe)|안[전정] ?계좌|보호 ?계좌",
       "It asks you to move money to a 'safe account'. No real bank or police ever asks this.",
       "'안전계좌'로 돈을 옮기라고 합니다. 진짜 은행이나 경찰은 절대 이런 요구를 하지 않습니다."),
    _p("msg.delivery", 15,
       r"\b(package|parcel|shipment|delivery)\b.{0,40}\b(failed|held|on hold|incomplete|unable|redeliver|"
       r"address)\b|택배|배송.{0,10}(실패|보류|주소)|주소지? ?(불일치|확인)",
       "It's a 'package problem' text — one of the most common scam texts.",
       "'택배 문제' 문자입니다 — 가장 흔한 사기 문자 중 하나입니다."),
    _p("msg.government", 25,
       r"\b(irs|social security|ssa|medicare|warrant|arrest(ed)?|lawsuit|court|police)\b"
       r"|검찰|검사|수사관|금융감독원|금감원|경찰청|사건에 연루|체포|영장",
       "It claims to be the government or police. They don't threaten people by text or phone.",
       "정부나 경찰이라고 주장합니다. 정부는 문자나 전화로 협박하지 않습니다."),
    _p("msg.family_emergency", 30,
       r"\b(mom|dad|grandma|grandpa)\b.{0,40}\b(new number|lost my phone|broke my phone|bail|accident|"
       r"hospital|in trouble)\b|new (phone )?number.{0,30}(mom|dad)"
       r"|(엄마|아빠).{0,20}(폰|핸드폰|휴대폰).{0,15}(고장|액정|깨|분실|수리)|이 번호로 (연락|문자)",
       "Someone says they're your child or grandchild on a new number. Call their OLD number first.",
       "자녀나 손주라며 새 번호로 연락했습니다. 먼저 원래 번호로 전화해 확인하세요."),
    _p("msg.prize", 20,
       r"\b(you('ve| have)? won|winner|prize|lottery|sweepstakes|claim your (reward|prize|refund))\b"
       r"|당첨|경품|환급금",
       "It says you won something or have money waiting. You can't win a contest you didn't enter.",
       "무언가에 당첨되었거나 돈을 받을 수 있다고 합니다. 응모하지 않은 행사에는 당첨될 수 없습니다."),
    _p("msg.toll", 20,
       r"\b(unpaid|outstanding) (toll|tolls|balance)\b|e-?z ?pass|toll (balance|notice|services)",
       "It's an 'unpaid toll' text — a very common scam right now.",
       "'미납 통행료' 문자입니다 — 요즘 매우 흔한 사기입니다."),
    _p("msg.remote_access", 35,
       r"\b(anydesk|teamviewer|remote (access|support|desktop)|install (this|the) app)\b"
       r"|원격|팀뷰어|애니데스크|앱을? 설치",
       "It asks you to install an app or give remote access. That lets them control your phone.",
       "앱 설치나 원격 접속을 요구합니다. 그러면 휴대폰을 마음대로 조종할 수 있습니다."),
    _p("msg.loan", 15,
       r"\b(pre-?approved|low interest|instant) loan\b|저금리|대출.{0,10}(승인|가능|지원)|정부 ?지원 ?대출",
       "It offers an easy loan. Loan scams ask for a 'fee' first.",
       "쉬운 대출을 제안합니다. 대출 사기는 먼저 '수수료'를 요구합니다."),
    _p("msg.secrecy", 20,
       r"\b(don'?t tell|keep (this|it) (secret|between us)|do not contact your bank)\b"
       r"|아무에게도 (말하지|알리지)|비밀로",
       "It tells you to keep it secret. Scammers don't want family or the bank to warn you.",
       "비밀로 하라고 합니다. 사기꾼은 가족이나 은행이 알려 주는 것을 막으려 합니다."),
]


def scan(text: str) -> list[Signal]:
    out = []
    for p in PATTERNS:
        m = p.regex.search(text)
        if m:
            out.append(Signal(code=p.code, weight=p.weight, evidence=m.group(0),
                              detail_en=p.en, detail_ko=p.ko))
    return out
