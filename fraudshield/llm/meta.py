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
from pathlib import Path
from typing import Optional

import httpx
from openai import OpenAI

from ..models import CheckItem, Message, Signal
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


class MetaBrain:
    def __init__(self, api_key: Optional[str] = None, budget_usd: Optional[float] = None):
        self.key = api_key or os.environ.get("MODEL_API_KEY")
        if not self.key:
            raise RuntimeError("MODEL_API_KEY is not set")
        if "contributor" in CHAT_MODEL:
            raise RuntimeError("Contributor models train on inputs — not allowed for family data")
        self.client = OpenAI(api_key=self.key, base_url=BASE_URL)
        self.budget = budget_usd if budget_usd is not None else float(os.environ.get("FRAUDSHIELD_BUDGET_USD", "140"))

    # --- cost guard -----------------------------------------------------
    def _spent(self) -> float:
        try:
            return json.loads(USAGE_FILE.read_text())["usd"]
        except (OSError, ValueError, KeyError):
            return 0.0

    def _add(self, usd: float) -> None:
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        USAGE_FILE.write_text(json.dumps({"usd": round(self._spent() + usd, 6)}))

    def _guard(self) -> None:
        if self._spent() >= self.budget:
            raise BudgetExceeded(f"budget ${self.budget:.2f} reached (spent ${self._spent():.2f})")

    # --- plumbing -------------------------------------------------------
    def _chat(self, content: list | str, fmt: Optional[dict] = None, system: Optional[str] = None) -> str:
        self._guard()
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": content}]
        kw = {"response_format": fmt} if fmt else {}
        r = self.client.chat.completions.create(model=CHAT_MODEL, messages=msgs, temperature=0.1, **kw)
        if r.usage:
            self._add(r.usage.prompt_tokens / 1e6 * PRICE_IN + r.usage.completion_tokens / 1e6 * PRICE_OUT)
        return r.choices[0].message.content or ""

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

    def explain(self, text: str, signals: list[Signal], lang: str) -> Optional[str]:
        if not signals:
            return None
        ev = "\n".join(f"- {s.detail_en}" for s in sorted(signals, key=lambda s: -s.weight)[:4])
        language = "Korean (polite 존댓말, simple words)" if lang == "ko" else "plain English"
        return self._chat(
            f"Message:\n---\n{text}\n---\nWhy it looks like a scam:\n{ev}\n\n"
            f"Write 2-3 short, calm sentences in {language} for an older parent: what this is and what to do. "
            "Never tell them to call or click anything in the message. No jargon.",
            system="You explain scams kindly and simply to older adults.").strip()

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
