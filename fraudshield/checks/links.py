"""Judge a link WITHOUT opening it.

Offline checks look at the address itself (lookalike brands, punycode, shorteners,
raw IPs). The one optional network call asks RDAP — the public domain registry —
when the domain was registered. The suspicious site itself is never contacted.
"""
from __future__ import annotations

import difflib
import re
from datetime import datetime, timezone
from typing import Callable, Optional
from urllib.parse import urlsplit

import httpx

from ..models import Signal

# Two-part public suffixes we care about; anything else uses the last label.
_MULTI_SUFFIX = {"co.kr", "or.kr", "go.kr", "ne.kr", "re.kr", "ac.kr", "co.uk", "org.uk",
                 "gov.uk", "com.au", "co.jp", "com.cn", "com.br"}

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "is.gd", "buff.ly", "ow.ly", "rebrand.ly",
              "cutt.ly", "shorturl.at", "rb.gy", "t.ly", "tiny.cc", "me2.kr", "han.gl", "vo.la",
              "goo.su", "s.id"}

# TLDs that show up a lot in phishing texts. A hint, not proof — low weight.
OFTEN_ABUSED_TLDS = {"top", "xyz", "click", "icu", "buzz", "rest", "cyou", "sbs", "monster",
                     "cfd", "bond", "vip", "live", "shop", "lol", "mom", "info", "win"}

# Brand keyword -> registered domains that really belong to it.
BRANDS: dict[str, set[str]] = {
    "usps": {"usps.com"}, "ups": {"ups.com"}, "fedex": {"fedex.com"}, "dhl": {"dhl.com"},
    "irs": {"irs.gov"}, "ssa": {"ssa.gov"}, "medicare": {"medicare.gov"},
    "paypal": {"paypal.com"}, "chase": {"chase.com"}, "bankofamerica": {"bankofamerica.com"},
    "wellsfargo": {"wellsfargo.com"}, "citi": {"citi.com"}, "capitalone": {"capitalone.com"},
    "amazon": {"amazon.com"}, "apple": {"apple.com", "icloud.com"},
    "microsoft": {"microsoft.com", "live.com", "outlook.com"}, "netflix": {"netflix.com"},
    "zelle": {"zellepay.com"}, "venmo": {"venmo.com"}, "cashapp": {"cash.app"},
    "kakao": {"kakao.com", "kakaocorp.com", "kakaobank.com", "kakaopay.com"},
    "naver": {"naver.com", "navercorp.com"},
    "coupang": {"coupang.com"}, "epost": {"epost.go.kr"}, "toss": {"toss.im"},
}


# Words scammers glue onto a brand name: "usps-redelivery", "paypalverify".
_SCAM_AFFIXES = {"secure", "login", "verify", "support", "help", "track", "tracking", "delivery",
                 "redelivery", "update", "account", "service", "pay", "alert", "notice", "refund",
                 "center", "care", "id", "auth", "online", "info", "kr", "us", "check"}


def _brand_signals(host: str, label: str) -> list[Signal]:
    """The address names a brand (or nearly spells it) but isn't that brand's domain."""
    tokens = [t for t in re.split(r"[.-]", host) if t]
    for brand, official in BRANDS.items():
        offs = ", ".join(sorted(official))
        hit = brand in tokens or any(
            t.startswith(brand) and t[len(brand):] in _SCAM_AFFIXES or
            t.endswith(brand) and t[:-len(brand)] in _SCAM_AFFIXES for t in tokens)
        if hit:
            return [Signal(code="link.brand_not_official", weight=45, evidence=host, hard=True,
                           detail_en=f"It uses the name '{brand}' but is not {brand}'s real website ({offs}).",
                           detail_ko=f"'{brand}' 이름을 쓰지만 {brand}의 진짜 웹사이트({offs})가 아닙니다.")]
    if len(label) >= 5:  # typo-squats: paypa1.com, arnazon.com
        for brand, official in BRANDS.items():
            for off in official:
                base = off.split(".")[0]
                if len(base) >= 5 and difflib.SequenceMatcher(None, label, base).ratio() >= 0.83:
                    return [Signal(code="link.typosquat", weight=45, evidence=host, hard=True,
                                   detail_en=f"The address is spelled almost like {off}, but not exactly.",
                                   detail_ko=f"주소 철자가 {off}와 거의 같지만 똑같지 않습니다.")]
    return []


def registered_domain(host: str) -> str:
    host = host.lower().strip(".")
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in _MULTI_SUFFIX:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _host(url: str) -> str:
    if "://" not in url:
        url = "http://" + url
    return (urlsplit(url).hostname or "").lower()


def _is_ip(host: str) -> bool:
    return host.replace(".", "").isdigit() and host.count(".") == 3


def analyze_url(url: str, rdap: Optional[Callable[[str], Optional[int]]] = None) -> list[Signal]:
    """Signals for one URL. `rdap(domain)` returns the domain's age in days (or None)."""
    sig: list[Signal] = []
    host = _host(url)
    if not host:
        return sig
    reg = registered_domain(host)
    label = reg.split(".")[0]
    tld = host.rsplit(".", 1)[-1]

    if _is_ip(host):
        sig.append(Signal(code="link.raw_ip", weight=35, evidence=url,
                          detail_en="The link goes to a bare number address instead of a company website.",
                          detail_ko="링크가 회사 웹사이트가 아니라 숫자로 된 주소로 연결됩니다."))
    if "xn--" in host:
        sig.append(Signal(code="link.punycode", weight=40, evidence=host, hard=True,
                          detail_en="The web address uses look-alike letters to copy a real site.",
                          detail_ko="웹 주소에 진짜 사이트를 흉내 낸 비슷한 글자가 쓰였습니다."))
    if reg in SHORTENERS:
        sig.append(Signal(code="link.shortener", weight=15, evidence=url,
                          detail_en="The link is shortened, which hides where it really goes.",
                          detail_ko="짧게 줄인 링크라서 실제로 어디로 가는지 숨겨져 있습니다."))
    if tld in OFTEN_ABUSED_TLDS:
        sig.append(Signal(code="link.risky_tld", weight=10, evidence=host,
                          detail_en=f"The address ends in .{tld}, which scam texts use a lot.",
                          detail_ko=f"주소가 .{tld}로 끝나는데, 사기 문자에 자주 쓰입니다."))
    if "@" in url.split("://", 1)[-1].split("/", 1)[0]:
        sig.append(Signal(code="link.userinfo_trick", weight=35, evidence=url, hard=True,
                          detail_en="The link hides the real site after an @ sign.",
                          detail_ko="링크가 @ 기호 뒤에 진짜 사이트를 숨기고 있습니다."))

    if not any(reg in official for official in BRANDS.values()):
        sig.extend(_brand_signals(host, label))

    if host.count("-") >= 3 or host.count(".") >= 4:
        sig.append(Signal(code="link.messy_host", weight=10, evidence=host,
                          detail_en="The web address is long and messy, like a throwaway site.",
                          detail_ko="웹 주소가 길고 복잡해서 일회용 사이트처럼 보입니다."))
    if url.lower().startswith("http://"):
        sig.append(Signal(code="link.no_https", weight=5, evidence=url,
                          detail_en="The link is not secure (http, not https).",
                          detail_ko="링크가 보안 연결(https)이 아닙니다."))

    if rdap and not _is_ip(host) and reg not in SHORTENERS:
        age = rdap(reg)
        if age is not None and age < 0:
            sig.append(Signal(code="link.not_registered", weight=30, evidence=reg,
                              detail_en="This web address isn't registered to anyone — it may already be shut down.",
                              detail_ko="이 웹 주소는 등록되어 있지 않습니다 — 이미 차단되었을 수 있습니다."))
        elif age is not None and age <= 30:
            sig.append(Signal(code="link.new_domain", weight=40, evidence=f"{reg} ({age} days old)", hard=True,
                              detail_en=f"This website was created only {age} days ago. Real companies use old, known addresses.",
                              detail_ko=f"이 웹사이트는 겨우 {age}일 전에 만들어졌습니다. 진짜 회사는 오래된 주소를 씁니다."))
    return sig


def rdap_age_days(domain: str, timeout: float = 6.0) -> Optional[int]:
    """Days since registration via rdap.org. -1 = not registered. None = lookup failed."""
    try:
        r = httpx.get(f"https://rdap.org/domain/{domain}", timeout=timeout, follow_redirects=True,
                      headers={"Accept": "application/rdap+json"})
    except httpx.HTTPError:
        return None
    if r.status_code == 404:
        return -1
    if r.status_code != 200:
        return None
    for ev in r.json().get("events", []):
        if ev.get("eventAction") == "registration" and ev.get("eventDate"):
            when = datetime.fromisoformat(ev["eventDate"].replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - when).days
    return None
