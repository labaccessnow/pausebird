"""The phone web page: paste or share a text, screenshot or voicemail and get a big
red / yellow / green answer — or check which paid checks you never wrote.

Nothing is stored. Uploads are read in memory and dropped. The last few verdicts stay
in memory only, so "Tell my family" and the phone's Share button can point at them.

Put on the internet with FRAUDSHIELD_PASSCODE set: everything but the page shell then
needs the passcode once per phone (a long-lived cookie), so strangers can't spend the AI budget.
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import mimetypes
import os
import re
import secrets
import time
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field

from . import agent, alerts, ledger, playbooks
from .checks import links
from .llm import pick_brain
from .llm.base import Brain, BudgetExceeded, FallbackBrain, OfflineBrain
from .models import CheckFinding, Level, Message, Signal, Verdict

STATIC = Path(__file__).parent / "static"
DEMO = Path(__file__).resolve().parent.parent / "demo"
MAX_IMAGE = 10 * 2**20
MAX_AUDIO = 32 * 2**20      # Muse Voice Transcribe's limit
MAX_CSV = 2**20
MAX_SIDE = 2000             # screenshots are shrunk to this before the model sees them (fewer tokens)
KEEP = 200                  # verdicts kept in memory for the alert and share buttons
COOKIE = "ffs_pass"
LOGIN_TRIES = 10            # wrong passcodes allowed per 10 minutes, across everyone
OPEN_PATHS = ("/manifest.webmanifest", "/sw.js", "/api/login")  # plus /static/: the shell, no data

mimetypes.add_type("audio/mp4", ".m4a")


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    sender: Optional[str] = Field(default=None, max_length=200)
    channel: str = Field(default="sms", max_length=20)


class AlertIn(BaseModel):
    id: str = Field(max_length=40)


class LoginIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)


def defang(s: str) -> str:
    """Show a scam link as text that can't be tapped by accident: hxxp://bad[.]top/x"""
    return re.sub(r"\.(?=[a-z0-9-])", "[.]", re.sub(r"^http", "hxxp", s, flags=re.I), flags=re.I)


def _signal(s: Signal) -> dict:
    ev = defang(s.evidence) if s.code.startswith("link.") or "://" in s.evidence else s.evidence
    return {"code": s.code, "weight": s.weight, "hard": s.hard, "evidence": ev,
            "en": s.detail_en, "ko": s.detail_ko}


def _steps(kind: Optional[str]) -> dict:
    if not kind:
        return {"en": [], "ko": []}
    return {"en": playbooks.steps(kind, "en"), "ko": playbooks.steps(kind, "ko")}


def _finding(f: CheckFinding) -> dict:
    c = f.check
    img = None
    if c.image and Path(c.image).resolve().parent == (DEMO / "checks").resolve():
        img = "/demo-checks/" + Path(c.image).name
    return {"number": c.number, "date": str(c.date) if c.date else None, "amount": c.amount,
            "payee": c.payee, "level": f.level.name, "micr": c.micr_number, "notes": c.notes, "image": img,
            "reasons": [{"en": s.detail_en, "ko": s.detail_ko, "hard": s.hard} for s in f.signals]}


def _read(f: UploadFile, limit: int) -> bytes:
    data = f.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, "too_big")
    if not data:
        raise HTTPException(400, "empty")
    return data


def _image(raw: bytes) -> tuple[bytes, str]:
    """Any picture the phone sends -> PNG/JPEG/WEBP the model accepts, at most MAX_SIDE pixels."""
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception:  # noqa: BLE001 - Pillow raises many types for "not an image"
        raise HTTPException(415, "wrong_type") from None
    if im.format in ("PNG", "JPEG", "WEBP") and max(im.size) <= MAX_SIDE:
        return raw, Image.MIME[im.format]
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=90)
    return buf.getvalue(), "image/jpeg"


def _audio_mime(f: UploadFile) -> str:
    mime = f.content_type or ""
    if not mime.startswith(("audio/", "video/")):
        mime = mimetypes.guess_type(f.filename or "")[0] or ""
    if not mime.startswith(("audio/", "video/")):
        raise HTTPException(415, "wrong_type")
    return mime


def _eyes(fn: Callable, *args):
    """Run a model reader; turn its failures into answers the page can show."""
    try:
        return fn(*args)
    except BudgetExceeded:
        raise HTTPException(503, "budget") from None
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 - network, API or ffmpeg trouble
        raise HTTPException(502, "model_error") from None


def create_app(brain: Optional[Brain] = None, notifier: Optional[alerts.Notifier] = None,
               rdap: Optional[Callable[[str], Optional[int]]] = None, demo: Optional[bool] = None,
               offline: Optional[bool] = None, parent: Optional[str] = None, lang: Optional[str] = None,
               passcode: Optional[str] = None) -> FastAPI:
    env = os.environ.get
    offline = offline if offline is not None else env("FRAUDSHIELD_OFFLINE") == "1"
    raw_brain = brain or pick_brain(offline)
    model_on = not isinstance(raw_brain, OfflineBrain)
    brain = FallbackBrain(raw_brain)
    notifier = notifier or (alerts.NtfyNotifier() if env("NTFY_TOPIC") else alerts.ConsoleNotifier())
    demo = demo if demo is not None else env("FRAUDSHIELD_DEMO", "1") == "1"
    parent = parent or env("FRAUDSHIELD_PARENT", "Dad")
    lang = lang or env("FRAUDSHIELD_LANG", "en")
    passcode = passcode if passcode is not None else env("FRAUDSHIELD_PASSCODE") or None
    demo_data = json.loads((DEMO / "messages.json").read_text(encoding="utf-8")) if demo else {}

    if rdap is None:
        ages = demo_data.get("rdap_fixture_days", {})

        @lru_cache(maxsize=1024)
        def rdap(domain: str) -> Optional[int]:
            # The demo domains are made up; their fixture ages stand in for a live registry lookup.
            if domain in ages:
                return ages[domain]
            return None if offline else links.rdap_age_days(domain)

    kept: OrderedDict[str, tuple[dict, Verdict, str]] = OrderedDict()

    def keep(payload: dict, verdict: Verdict, what: str) -> dict:
        payload["id"] = secrets.token_urlsafe(9)
        kept[payload["id"]] = (payload, verdict, what)
        while len(kept) > KEEP:
            kept.popitem(last=False)
        return payload

    def judge(msg: Message, what: str, read: Optional[dict] = None) -> dict:
        v = agent.check_message(msg, brain=brain, rdap=rdap)
        return keep({"kind": "message", "level": v.level.name, "score": v.score,
                     "summary": {"en": v.summary_en, "ko": v.summary_ko},
                     "signals": [_signal(s) for s in sorted(v.signals, key=lambda s: -s.weight)],
                     "steps": _steps("message" if v.level != Level.SAFE else None),
                     "clicked_steps": _steps("clicked"),
                     "model": v.model_opinion, "read": read}, v, what)

    def need_model() -> None:
        if not model_on:
            raise HTTPException(503, "needs_model")

    app = FastAPI(title="Family Fraud Shield", docs_url=None, redoc_url=None, openapi_url=None)
    if passcode:
        _lock(app, passcode)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    if demo:
        app.mount("/demo-checks", StaticFiles(directory=DEMO / "checks"), name="demo-checks")
        app.mount("/demo-media", StaticFiles(directory=DEMO / "media"), name="demo-media")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest():
        return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/sw.js", include_in_schema=False)
    def service_worker():
        return FileResponse(STATIC / "sw.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})

    @app.get("/api/status")
    def status():
        return {"model": model_on, "demo": demo, "parent": parent, "lang": lang,
                "alerts": "phone" if isinstance(notifier, alerts.NtfyNotifier) else "console"}

    @app.get("/api/demo/messages")
    def demo_messages():
        return [{k: m[k] for k in ("id", "channel", "sender", "text")} for m in demo_data.get("messages", [])]

    @app.get("/api/demo/screenshots")
    def demo_screenshots():
        return [{"id": s["id"], "url": "/demo-media/" + s["file"], "label": s["label"]}
                for s in demo_data.get("screenshots", [])]

    @app.post("/api/check/message")
    def check_message(m: MessageIn):
        return judge(Message(text=m.text, sender=m.sender or None, channel=m.channel), "a message")

    @app.post("/api/check/screenshot")
    def check_screenshot(file: UploadFile = File(...)):
        need_model()
        image, mime = _image(_read(file, MAX_IMAGE))
        msg = _eyes(brain.read_screenshot, image, mime)
        if not msg or not msg.text.strip():
            raise HTTPException(422, "unreadable")
        return judge(msg, "a screenshot", read={"text": msg.text, "sender": msg.sender})

    @app.post("/api/check/voicemail")
    def check_voicemail(file: UploadFile = File(...), lang: str = Form(lang)):
        need_model()
        audio, mime = _read(file, MAX_AUDIO), _audio_mime(file)
        text = _eyes(brain.transcribe, audio, mime, "ko" if lang == "ko" else "en")
        if not text or not text.strip():
            raise HTTPException(422, "unreadable")
        return judge(Message(text=text, channel="voicemail"), "a voicemail", read={"text": text, "sender": None})

    @app.post("/api/check/account")
    def check_account(paid: Optional[UploadFile] = File(None), wrote: Optional[UploadFile] = File(None),
                      use_demo: bool = Form(False), read_images: bool = Form(False)):
        if use_demo:
            if not demo:
                raise HTTPException(404, "no_demo")
            cleared, register = ledger.read_checks(DEMO / "cleared.csv"), ledger.read_checks(DEMO / "register.csv")
        else:
            if not (paid and wrote):
                raise HTTPException(400, "need_both_files")
            try:
                cleared = ledger.parse_checks(_read(paid, MAX_CSV).decode("utf-8-sig", "replace"))
                register = ledger.parse_checks(_read(wrote, MAX_CSV).decode("utf-8-sig", "replace"))
            except ValueError as e:
                raise HTTPException(400, f"bad_csv: {e}") from None
        if read_images and model_on:
            cleared = _eyes(agent.read_check_images, cleared, brain)
        v, findings = agent.check_account(cleared, register)
        return keep({"kind": "account", "level": v.level.name, "score": v.score,
                     "summary": {"en": v.summary_en, "ko": v.summary_ko},
                     "total_loss": round(sum(f.check.amount for f in findings if f.level == Level.SCAM), 2),
                     "findings": [_finding(f) for f in findings],
                     "steps": _steps("fake_checks" if v.level == Level.SCAM else None)},
                    v, "their bank account")

    @app.get("/api/result/{rid}")
    def result(rid: str):
        if rid not in kept:
            raise HTTPException(404, "expired")
        return kept[rid][0]

    @app.post("/api/alert")
    def alert(a: AlertIn):
        if a.id not in kept:
            raise HTTPException(404, "expired")
        _, v, what = kept[a.id]
        if v.level == Level.SAFE:
            return {"sent": False}
        title, body = alerts.family_alert(parent, v, what)
        return {"sent": notifier.send(title, body, urgent=v.level == Level.SCAM),
                "via": "phone" if isinstance(notifier, alerts.NtfyNotifier) else "console"}

    @app.post("/share", include_in_schema=False)
    def share(title: str = Form(""), text: str = Form(""), url: str = Form(""),
              media: list[UploadFile] = File(default=[])):
        """Android 'Share to Fraud Shield' lands here (manifest share_target)."""
        f = media[0] if media else None
        kind = (f.content_type or "") if f else ""
        try:
            if kind.startswith("image/"):
                r = check_screenshot(f)
            elif kind.startswith(("audio/", "video/")):
                r = check_voicemail(f, lang)
            else:
                body = "\n".join(x.strip() for x in (title, text, url) if x and x.strip())
                if not body:
                    raise HTTPException(400, "empty")
                r = judge(Message(text=body[:5000]), "a shared message")
        except HTTPException as e:
            return RedirectResponse(f"/#err={quote(str(e.detail))}", status_code=303)
        return RedirectResponse(f"/#r={r['id']}", status_code=303)

    return app


def _lock(app: FastAPI, passcode: str) -> None:
    """Ask for the passcode once per phone. The cookie holds an HMAC of the passcode, so
    changing the passcode signs everyone out. Wrong tries are counted for everyone together:
    simple, and enough to stop guessing (one person can lock it for 10 minutes, at worst)."""
    token = hmac.new(passcode.encode(), b"family-fraud-shield", hashlib.sha256).hexdigest().encode()
    fails: list[float] = []

    @app.middleware("http")
    async def need_passcode(request: Request, call_next):
        path = request.url.path
        if path.startswith("/static/") or path in OPEN_PATHS or \
                hmac.compare_digest(request.cookies.get(COOKIE, "").encode(), token):
            return await call_next(request)
        if path == "/":
            return FileResponse(STATIC / "login.html", headers={"Cache-Control": "no-cache"})
        if path == "/share":
            return RedirectResponse("/", status_code=303)
        return JSONResponse({"detail": "locked"}, status_code=401)

    @app.post("/api/login")
    def login(body: LoginIn, request: Request):
        now = time.monotonic()
        fails[:] = [t for t in fails if now - t < 600]
        if len(fails) >= LOGIN_TRIES:
            raise HTTPException(429, "slow_down")
        if not hmac.compare_digest(body.code.strip().encode(), passcode.encode()):
            fails.append(now)
            raise HTTPException(403, "wrong_code")
        r = JSONResponse({"ok": True})
        https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
        r.set_cookie(COOKIE, token.decode(), max_age=400 * 86400, httponly=True, secure=https, samesite="lax")
        return r
