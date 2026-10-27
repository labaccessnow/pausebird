import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from fraudshield.llm.base import BudgetExceeded, OfflineBrain
from fraudshield.models import Message
from fraudshield.web import create_app, defang


class Recorder:
    def __init__(self):
        self.sent = []

    def send(self, title, body, urgent):
        self.sent.append((title, body, urgent))
        return True


class FakeEyes:
    """A brain that 'reads' screenshots and voicemails without calling any model."""

    def __init__(self, text="USPS: package on hold. Update: https://usps-redelivery-help.top/x", fail=None):
        self.text, self.fail = text, fail

    def read_screenshot(self, image, mime):
        if self.fail:
            raise self.fail
        return Message(text=self.text, sender="+1 202 555 0147")

    def transcribe(self, audio, mime, lang_hint="ko"):
        return self.text

    def read_check(self, image, mime):
        return None

    def judge(self, text, signals):
        return None

    def explain(self, msg, signals, level):
        return None


def client(brain=None, **kw):
    rec = Recorder()
    app = create_app(brain=brain or OfflineBrain(), notifier=rec, offline=True, **kw)
    return TestClient(app), rec


def png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), "white").save(buf, "PNG")
    return buf.getvalue()


def test_page_and_status():
    c, _ = client()
    assert "Family Fraud Shield" in c.get("/").text
    assert c.get("/manifest.webmanifest").json()["share_target"]["action"] == "/share"
    assert c.get("/api/status").json() == {"model": False, "demo": True, "parent": "Dad", "lang": "en",
                                           "alerts": "console"}


def test_example_screenshots_are_served_and_checked():
    c, _ = client(FakeEyes())
    shots = c.get("/api/demo/screenshots").json()
    assert [x["id"] for x in shots] == ["shot-ko-delivery", "shot-en-toll"] and shots[0]["label"]["ko"]
    img = c.get(shots[0]["url"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    r = c.post("/api/check/screenshot", files={"file": ("x.png", img.content, "image/png")}).json()
    assert r["level"] == "SCAM"


def test_scam_message_then_family_alert():
    c, rec = client()
    r = c.post("/api/check/message", json={"text": "Chase Alert: Your account has been suspended due to "
               "unusual activity. Verify your identity: http://chase-secure-login.com.verify-acct.xyz/login"}).json()
    assert r["level"] == "SCAM" and r["steps"]["ko"] and r["clicked_steps"]["en"]
    links = [s["evidence"] for s in r["signals"] if s["code"].startswith("link.")]
    assert links and all("http://" not in e and "[.]" in e for e in links)  # shown defanged, not tappable
    assert c.post("/api/alert", json={"id": r["id"]}).json() == {"sent": True, "via": "console"}
    title, body, urgent = rec.sent[0]
    assert urgent and "Dad" in title and "verify-acct" not in body  # no scam links in the family alert


def test_safe_message_sends_no_alert():
    c, rec = client()
    r = c.post("/api/check/message", json={"text": "Hi Dad, dinner at 6 on Sunday?"}).json()
    assert r["level"] == "SAFE" and r["steps"] == {"en": [], "ko": []}
    assert c.post("/api/alert", json={"id": r["id"]}).json() == {"sent": False}
    assert not rec.sent


def test_demo_account():
    c, _ = client()
    r = c.post("/api/check/account", data={"use_demo": "true"}).json()
    assert r["level"] == "SCAM" and r["total_loss"] == 5475.0
    bad = [f for f in r["findings"] if f["level"] == "SCAM"]
    assert len(bad) == 3 and all(f["image"].startswith("/demo-checks/") for f in bad)
    assert c.get(bad[0]["image"]).headers["content-type"] == "image/png"


def test_uploaded_csvs_and_bad_csv():
    c, _ = client()
    paid = "number,amount,payee\n101,50,Water Co\n999,700,Cash Now\n"
    wrote = "number,amount,payee\n101,50,Water Co\n"
    r = c.post("/api/check/account", files={"paid": ("paid.csv", paid), "wrote": ("wrote.csv", wrote)}).json()
    assert r["level"] == "SCAM" and r["total_loss"] == 700.0
    bad = c.post("/api/check/account", files={"paid": ("p.csv", "x,y\n1,2\n"), "wrote": ("w.csv", wrote)})
    assert bad.status_code == 400 and bad.json()["detail"].startswith("bad_csv: missing column")
    assert c.post("/api/check/account", data={}).json()["detail"] == "need_both_files"


def test_screenshot_needs_the_model():
    c, _ = client()
    r = c.post("/api/check/screenshot", files={"file": ("s.png", png(), "image/png")})
    assert r.status_code == 503 and r.json()["detail"] == "needs_model"


def test_screenshot_with_eyes():
    c, _ = client(FakeEyes())
    r = c.post("/api/check/screenshot", files={"file": ("s.png", png(), "image/png")}).json()
    assert r["level"] == "SCAM" and r["read"]["sender"] == "+1 202 555 0147"


@pytest.mark.parametrize("fail,code", [(BudgetExceeded("cap"), "budget"), (RuntimeError("down"), "model_error")])
def test_model_failures_become_messages(fail, code):
    c, _ = client(FakeEyes(fail=fail))
    r = c.post("/api/check/screenshot", files={"file": ("s.png", png(), "image/png")})
    assert r.json()["detail"] == code


def test_not_an_image():
    c, _ = client(FakeEyes())
    r = c.post("/api/check/screenshot", files={"file": ("s.png", b"not an image", "image/png")})
    assert r.status_code == 415


def test_share_target_text_and_errors():
    c, _ = client()
    r = c.post("/share", data={"text": "E-ZPass: unpaid toll balance. Pay now: https://ezpass-tolls-pay.vip/pay"},
               follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/#r=")
    rid = r.headers["location"].split("=", 1)[1]
    assert c.get(f"/api/result/{rid}").json()["level"] == "SCAM"
    r = c.post("/share", files={"media": ("s.png", png(), "image/png")}, follow_redirects=False)
    assert r.headers["location"] == "/#err=needs_model"
    assert c.get("/api/result/nope").status_code == 404


def test_voicemail_with_ears():
    c, _ = client(FakeEyes(text="안녕하세요 수사관입니다. 안전계좌로 이체하세요."))
    r = c.post("/api/check/voicemail", files={"file": ("vm.m4a", b"\0" * 10, "audio/mp4")}, data={"lang": "ko"})
    assert r.json()["level"] == "SCAM" and r.json()["read"]["text"].startswith("안녕하세요")


def test_defang():
    assert defang("https://bad.example.top/x") == "hxxps://bad[.]example[.]top/x"
