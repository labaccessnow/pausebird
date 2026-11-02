"""Meta Model API brain (Muse Spark + Muse Voice Transcribe).

Docs: https://dev.meta.ai/docs — OpenAI-compatible at https://api.meta.ai/v1.
Standard model IDs only: '-contributor' IDs let Meta train on the inputs, and
family messages and checks are personal data, so they are refused here.

Meta's billing "spend limit" is an email alert, not a cap — so this client keeps
its own running cost and stops at FRAUDSHIELD_BUDGET_USD.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

import httpx

from ..models import CheckItem, Level, Message, Signal
from .base import BudgetExceeded

BASE_URL = "https://api.meta.ai/v1"
CHAT_MODEL = os.environ.get("FRAUDSHIELD_MODEL", "muse-spark-1.3")
ASR_MODEL = "muse-voice-transcribe-1.0"
# USD per 1M tokens (input, output) and per audio hour — dev.meta.ai/docs/pricing-rate-limits
PRICE_IN, PRICE_OUT, PRICE_AUDIO_HR = 1.25, 4.25, 0.18
USAGE_FILE = Path(os.environ.get("FRAUDSHIELD_USAGE", Path.home() / ".fraudshield" / "usage.json"))


def _schema(name: str, props: dict) -> dict:
    return {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": {
        "type": "object", "additionalProperties": False, "required": list(props), "properties": props}}}


SCREENSHOT = _schema("message_screenshot", {
    "text": {"type": "string", "description": "Every word of the message, exactly as shown, original language."},
    "sender": {"type": "string", "description": "Sender number, email or name as shown; empty if not visible."},
    "channel": {"type": "string", "enum": ["sms", "kakaotalk", "email", "other"]},
})
CHECK = _schema("check_image", {
    "number": {"type": "integer", "description": "Check number printed top-right; -1 if unreadable."},
    "amount": {"type": "number", "description": "Amount in dollars from the numeric box; -1 if unreadable."},
    "payee": {"type": "string", "description": "Name on the 'Pay to the order of' line."},
    "date": {"type": "string", "description": "Date on the check as YYYY-MM-DD; empty if unreadable."},
    "micr_number": {"type": "integer",
                    "description": "Check number inside the MICR line at the bottom; -1 if unreadable."},
    "altered_signs": {"type": "string",
                      "description": "Visible signs of tampering (smudged/overwritten payee or amount, words and "
                                     "numbers disagree, mismatched fonts). Empty if none."},
})
JUDGE = _schema("scam_judgement", {
    "scam_likelihood": {"type": "integer", "description": "0-100"},
    "reason": {"type": "string", "description": "One plain sentence."},
})
EXPLAIN = _schema("plain_explanation", {
    "en": {"type": "string", "description": "The explanation in plain English."},
    "ko": {"type": "string", "description": "The same explanation in simple, polite Korean."},
})
# What the explanation should tell the parent to do, by verdict.
TODO = {
    Level.SCAM: "Tell them not to reply, click, call back or pay, to delete it, and to tell their family.",
    Level.CAUTION: "Tell them to check it first by calling the company or person on a number they already "
                   "know, never one from the message.",
    Level.SAFE: "Tell them it looks fine, and that real family and companies never need codes, passwords "
                "or gift cards by text.",
}
# What to call the message in each language, so a voicemail isn't called a text.
KIND = {"sms": ("text message", "문자"), "kakaotalk": ("KakaoTalk message", "카카오톡 메시지"),
        "email": ("email", "이메일"), "voicemail": ("voicemail", "음성 메시지")}


class MetaBrain:
    def __init__(self, api_key: Optional[str] = None, budget_usd: Optional[float] = None,
                 usage_file: Optional[Path] = None):
        self.key = api_key or os.environ.get("MODEL_API_KEY")
        if not self.key:
            raise RuntimeError("MODEL_API_KEY is not set")
        if "contributor" in CHAT_MODEL:
            raise RuntimeError("Contributor models train on inputs — not allowed for family data")
        # Plain HTTP, not the OpenAI SDK: Windows Smart App Control blocks the SDK's compiled jiter module.
        self.http = httpx.Client(base_url=BASE_URL, timeout=120, headers={"Authorization": f"Bearer {self.key}"})
        self.budget = budget_usd if budget_usd is not None else float(os.environ.get("FRAUDSHIELD_BUDGET_USD", "140"))
        self.usage_file = Path(usage_file) if usage_file else USAGE_FILE  # judges get their own count
        # How the explanations address the parent, so the Korean doesn't guess a title.
        self.parent_en = os.environ.get("FRAUDSHIELD_PARENT", "Dad")
        self.parent_ko = os.environ.get("FRAUDSHIELD_PARENT_KO", "아버지")
        self._lock = threading.Lock()  # check images are read in parallel; keep the spend count exact

    # --- cost guard -----------------------------------------------------
    def _spent(self) -> float:
        try:
            return json.loads(self.usage_file.read_text(encoding="utf-8"))["usd"]
        except (OSError, ValueError, KeyError):
            return 0.0

    def _add(self, usd: float) -> None:
        with self._lock:
            self.usage_file.parent.mkdir(parents=True, exist_ok=True)
            self.usage_file.write_text(json.dumps({"usd": round(self._spent() + usd, 6)}), encoding="utf-8")

    def _guard(self) -> None:
        if self._spent() >= self.budget:
            raise BudgetExceeded(f"budget ${self.budget:.2f} reached (spent ${self._spent():.2f})")

    # --- plumbing -------------------------------------------------------
    def _chat(self, content: list | str, fmt: Optional[dict] = None, system: Optional[str] = None,
              effort: str = "low") -> str:
        """Muse Spark thinks before it answers, and the thinking is billed and slow. Reading and judging
        get "low"; writing the plain explanation needs no thinking, so it uses "minimal"."""
        self._guard()
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": content}]
        body = {"model": CHAT_MODEL, "messages": msgs, "temperature": 0.1, "reasoning_effort": effort}
        if fmt:
            body["response_format"] = fmt
        r = self._post("/chat/completions", body)
        if usage := r.get("usage"):
            self._add(usage["prompt_tokens"] / 1e6 * PRICE_IN + usage["completion_tokens"] / 1e6 * PRICE_OUT)
        return r["choices"][0]["message"].get("content") or ""

    def _post(self, path: str, body: dict, tries: int = 3) -> dict:
        """POST JSON, retrying a dropped connection, 429 or 5xx twice (what the OpenAI SDK used to do)."""
        for n in range(1, tries + 1):
            try:
                r = self.http.post(path, json=body)
                if (r.status_code in (408, 409, 429) or r.status_code >= 500) and n < tries:
                    raise httpx.HTTPStatusError(f"HTTP {r.status_code}", request=r.request, response=r)
            except (httpx.TransportError, httpx.HTTPStatusError):
                if n == tries:
                    raise
                time.sleep(0.5 * 2 ** n)
                continue
            r.raise_for_status()
            return r.json()
        raise AssertionError("unreachable")

    @staticmethod
    def _image_part(image: bytes, mime: str) -> dict:
        return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(image).decode()}"}}

    # --- Brain ----------------------------------------------------------
    def read_screenshot(self, image: bytes, mime: str) -> Optional[Message]:
        out = json.loads(self._chat([
            {"type": "text", "text": "This is a phone screenshot of a text message, KakaoTalk chat or email "
                                     "that someone received. Copy the received message exactly."},
            self._image_part(image, mime)], SCREENSHOT))
        return Message(text=out["text"], sender=out["sender"] or None, channel=out["channel"])

    def read_check(self, image: bytes, mime: str) -> Optional[CheckItem]:
        out = json.loads(self._chat([
            {"type": "text", "text": "This is the image of a paid bank check. Read its fields. Report only what "
                                     "you can see; use -1 or empty when unreadable."},
            self._image_part(image, mime)], CHECK))
        if out["number"] < 0 or out["amount"] < 0:
            return None
        return CheckItem(number=out["number"], amount=out["amount"], payee=out["payee"],
                         date=out["date"] or None,
                         micr_number=out["micr_number"] if out["micr_number"] >= 0 else None,
                         notes=out["altered_signs"] or None)

    def judge(self, text: str, signals: list[Signal]) -> Optional[tuple[int, str]]:
        ev = "\n".join(f"- {s.code}: {s.evidence}" for s in signals) or "- none"
        out = json.loads(self._chat(
            f"A parent received this message:\n---\n{text}\n---\nRule checks found:\n{ev}\n\n"
            "How likely is this a scam? Consider ordinary explanations too (a real friend, a real "
            "appointment reminder). Answer in English.", JUDGE,
            system="You are a careful fraud analyst protecting older family members."))
        return round(out["scam_likelihood"] * 0.3), out["reason"]

    def explain(self, msg: Message, signals: list[Signal], level: Level) -> Optional[dict[str, str]]:
        if not signals:
            return None
        ev = "\n".join(f"- {s.detail_en}" for s in sorted(signals, key=lambda s: -s.weight)[:4])
        kind_en, kind_ko = KIND.get(msg.channel, ("message", "메시지"))
        out = json.loads(self._chat(
            f"A parent received this {kind_en}:\n---\n{msg.text}\n---\nVerdict: {level.name}. Why:\n{ev}\n\n"
            f"Write 2-3 short, calm sentences for an older parent: what this is and what to do. {TODO[level]} "
            f"Never tell them to call or click anything in the message. No jargon.\n"
            f"en: plain English. Call them \"{self.parent_en}\" and call it a {kind_en}.\n"
            f"ko: simple Korean in polite 존댓말. Call them \"{self.parent_ko}\" and never by any other title; "
            f"call it {kind_ko}.\n"
            "Speak as a helper, not as a family member: say \"tell your family\", not \"tell me\".",
            EXPLAIN, system="You explain scams kindly and simply to older adults.", effort="minimal"))
        return {"en": out["en"].strip(), "ko": out["ko"].strip()}

    def transcribe(self, audio: bytes, mime: str, lang_hint: str = "ko") -> Optional[str]:
        """Voicemail -> words. Muse Voice Transcribe wants mono 16-bit PCM WAV."""
        self._guard()
        with tempfile.TemporaryDirectory() as d:
            src, wav = Path(d) / "in", Path(d) / "in.wav"
            src.write_bytes(audio)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "16000",
                            "-sample_fmt", "s16", str(wav)], check=True)
            req = {"model": ASR_MODEL, "mode": "PUSH_TO_TALK", "audioEncoding": "WAV"}
            if lang_hint == "ko":
                req["languageBias"] = ["Korean"]
            r = httpx.post(f"{BASE_URL}/asr/transcribe", timeout=120,
                           headers={"Authorization": f"Bearer {self.key}", "Accept": "application/json"},
                           files={"request": (None, json.dumps(req), "application/json"),
                                  "audio": ("in.wav", wav.read_bytes(), "audio/wav")})
        r.raise_for_status()
        out = r.json()
        self._add(out.get("audioDurationMs", 0) / 3.6e6 * PRICE_AUDIO_HR)
        return out.get("transcript")
