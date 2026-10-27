"""The model interface. The rule engine works without it; the model adds eyes and ears.

- read_screenshot: a screenshot of a text / KakaoTalk / email -> the words and the sender
- transcribe: a voicemail -> words
- read_check: a check image -> number, amount, payee, MICR number, anything that looks altered
- judge: a second opinion on a message, given the rule evidence (it may add, never erase)
- explain: turn the verdict and evidence into a few calm sentences for a parent, in English and Korean
"""
from __future__ import annotations

import logging
from typing import Optional, Protocol

from ..models import CheckItem, Level, Message, Signal

log = logging.getLogger("fraudshield.llm")


class BudgetExceeded(RuntimeError):
    """Our own spending cap was reached (Meta's 'spend limit' only sends an email)."""


class Brain(Protocol):
    def read_screenshot(self, image: bytes, mime: str) -> Optional[Message]: ...
    def transcribe(self, audio: bytes, mime: str, lang_hint: str = "ko") -> Optional[str]: ...
    def read_check(self, image: bytes, mime: str) -> Optional[CheckItem]: ...
    def judge(self, text: str, signals: list[Signal]) -> Optional[tuple[int, str]]: ...
    def explain(self, msg: Message, signals: list[Signal], level: Level) -> Optional[dict[str, str]]: ...


class OfflineBrain:
    """No model: everything falls back to the rules and templates."""

    def read_screenshot(self, image, mime):
        return None

    def transcribe(self, audio, mime, lang_hint="ko"):
        return None

    def read_check(self, image, mime):
        return None

    def judge(self, text, signals):
        return None

    def explain(self, msg, signals, level):
        return None


class FallbackBrain:
    """Wraps a brain so a model outage or the budget stop never blocks a verdict.

    judge/explain are extras on top of the rules: if they fail, the rules still answer.
    The eyes and ears (screenshot, voicemail, check image) pass errors through, because
    without them there is nothing to judge and the caller should say so.
    """

    def __init__(self, inner: Brain):
        self.inner = inner

    def read_screenshot(self, image, mime):
        return self.inner.read_screenshot(image, mime)

    def transcribe(self, audio, mime, lang_hint="ko"):
        return self.inner.transcribe(audio, mime, lang_hint)

    def read_check(self, image, mime):
        return self.inner.read_check(image, mime)

    def judge(self, text, signals):
        try:
            return self.inner.judge(text, signals)
        except Exception as e:  # noqa: BLE001 - any model failure falls back to rules only
            log.warning("judge failed, rules only: %s", e)
            return None

    def explain(self, msg, signals, level):
        try:
            return self.inner.explain(msg, signals, level)
        except Exception as e:  # noqa: BLE001
            log.warning("explain failed, using the template: %s", e)
            return None
