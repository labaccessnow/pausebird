"""Phone-number hints. Caller ID can be faked, so these only add weight."""
from __future__ import annotations

from typing import Optional

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberType, number_type

from ..models import Signal


def analyze_number(e164: str, trusted_regions: frozenset[str] = frozenset({"US", "KR"}),
                   claimed_region: Optional[str] = None) -> list[Signal]:
    """`trusted_regions` = countries family normally calls from (a Korean-American home: US + KR).
    `claimed_region` = where the sender says they are (a 'US bank' calling from abroad is a red flag)."""
    sig: list[Signal] = []
    try:
        num = phonenumbers.parse(e164, None)
    except NumberParseException:
        return sig
    region = phonenumbers.region_code_for_number(num)
    kind = number_type(num)

    # Korean 070 numbers are internet (VoIP) lines — the usual tool of Korean phone scams.
    if region == "KR" and str(num.national_number).startswith("70"):
        sig.append(Signal(code="phone.kr_voip", weight=20, evidence=e164,
                          detail_en="It's a Korean 070 internet phone number, often used by phone scammers.",
                          detail_ko="070 인터넷 전화번호입니다. 보이스피싱에 자주 쓰입니다."))
    if kind == PhoneNumberType.VOIP and region != "KR":
        sig.append(Signal(code="phone.voip", weight=10, evidence=e164,
                          detail_en="It's an internet phone number, which is cheap and easy to fake.",
                          detail_ko="인터넷 전화번호라서 쉽게 만들고 속일 수 있습니다."))
    if region and (region not in trusted_regions or (claimed_region and region != claimed_region)):
        sig.append(Signal(code="phone.foreign", weight=15, evidence=e164,
                          detail_en=f"The number is from another country ({region}), not where they claim to be.",
                          detail_ko=f"번호가 다른 나라({region})의 번호로, 주장하는 곳과 다릅니다."))
    return sig
