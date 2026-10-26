import json
from datetime import date
from pathlib import Path

from fraudshield import agent, extract
from fraudshield.checks import accounts, links, patterns, phones
from fraudshield.cli import read_checks
from fraudshield.models import CheckItem, Level, Message

DEMO = Path(__file__).resolve().parent.parent / "demo"


def codes(signals):
    return {s.code for s in signals}


# --- extract ---------------------------------------------------------------
def test_urls_scheme_bare_and_defanged():
    t = "go to https://a.example.com/x, or usps-help.top/track or hxxp://bad[.]xyz/p."
    assert set(extract.urls(t)) == {"https://a.example.com/x", "http://bad.xyz/p", "usps-help.top/track"}


def test_urls_skip_email_domains_and_files():
    assert extract.urls("mail me at bob@gmail.com about photo.jpg") == []


def test_phones_us_and_korean():
    got = extract.phones("call +1 (202) 555-0147 or 070-0000-1234")
    assert "+12025550147" in got and "+827000001234" in got


# --- links -----------------------------------------------------------------
def test_real_brand_domain_is_clean():
    assert not {"link.brand_not_official", "link.typosquat"} & codes(links.analyze_url("https://www.chase.com/login"))


def test_brand_on_wrong_domain():
    assert "link.brand_not_official" in codes(links.analyze_url("https://usps-redelivery.top/x"))


def test_brand_substring_in_unrelated_word_is_not_flagged():
    assert "link.brand_not_official" not in codes(links.analyze_url("https://applebees.com"))


def test_typosquat():
    assert "link.typosquat" in codes(links.analyze_url("https://paypa1.com/signin"))


def test_registered_domain_multi_suffix():
    assert links.registered_domain("a.b.example.co.kr") == "example.co.kr"


def test_rdap_age_is_used():
    sig = links.analyze_url("https://fresh-site.top/a", rdap=lambda d: 2)
    assert "link.new_domain" in codes(sig)


def test_punycode_and_raw_ip():
    assert "link.punycode" in codes(links.analyze_url("https://xn--pypal-4ve.com"))
    assert "link.raw_ip" in codes(links.analyze_url("http://192.0.2.10/login"))


# --- patterns / phones -----------------------------------------------------
def test_korean_patterns():
    c = codes(patterns.scan("안녕하세요 수사관입니다. 안전계좌로 이체하시고 아무에게도 말하지 마세요."))
    assert {"msg.government", "msg.safe_account", "msg.secrecy"} <= c


def test_korean_070_voip():
    assert "phone.kr_voip" in codes(phones.analyze_number("+827000001234"))


def test_korean_mobile_is_trusted_for_korean_family():
    assert not phones.analyze_number("+821000000101")


# --- account watch ---------------------------------------------------------
REG = [CheckItem(number=101, amount=50.0, payee="Water Co", date=date(2026, 10, 1)),
       CheckItem(number=102, amount=80.0, payee="Dentist", date=date(2026, 10, 2))]


def test_clean_account():
    f = accounts.review([CheckItem(number=101, amount=50.0, payee="Water Co.", date=date(2026, 10, 3))], REG)
    assert f[0].level == Level.SAFE


def test_washed_and_counterfeit_and_micr():
    cleared = [CheckItem(number=102, amount=980.0, payee="Cash Now", date=date(2026, 10, 5)),
               CheckItem(number=777, amount=1500.0, payee="X LLC", date=date(2026, 10, 6), micr_number=103)]
    f = accounts.review(cleared, REG)
    assert {"check.amount_changed", "check.payee_changed"} <= codes(f[0].signals)
    assert {"check.not_written", "check.micr_mismatch"} <= codes(f[1].signals)
    assert all(x.level == Level.SCAM for x in f)


# --- end to end on the demo data -------------------------------------------
def test_demo_messages_match_expectations():
    data = json.loads((DEMO / "messages.json").read_text())
    ages = data["rdap_fixture_days"]
    for m in data["messages"]:
        v = agent.check_message(Message(text=m["text"], sender=m["sender"]), rdap=lambda d: ages.get(d))
        assert v.level.name == m["expect"], (m["id"], v.level, [s.code for s in v.signals])


def test_demo_account():
    v, findings = agent.check_account(read_checks(DEMO / "cleared.csv"), read_checks(DEMO / "register.csv"))
    assert v.level == Level.SCAM
    assert sum(f.level == Level.SCAM for f in findings) == 3
    assert sum(f.level == Level.SAFE for f in findings) == 4
