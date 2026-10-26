"""The model interface. The rule engine works without it; the model adds eyes and ears.

- read_screenshot: a screenshot of a text / KakaoTalk / email -> the words and the sender
- transcribe: a voicemail -> words
- read_check: a check image -> number, amount, payee, MICR number, anything that looks altered
- judge: a second opinion on a message, given the rule evidence (it may add, never erase)
- explain: turn the evidence into a few calm sentences for a parent, in their language
"""
from __future__ import annotations

from typing import Optional, Protocol

from ..models import CheckItem, Message, Signal


class Brain(Protocol):
    def read_screenshot(self, image: bytes, mime: str) -> Optional[Message]: ...
    def transcribe(self, audio: bytes, mime: str, lang_hint: str = "ko") -> Optional[str]: ...
    def read_check(self, image: bytes, mime: str) -> Optional[CheckItem]: ...
    def judge(self, text: str, signals: list[Signal]) -> Optional[tuple[int, str]]: ...
    def explain(self, text: str, signals: list[Signal], lang: str) -> Optional[str]: ...


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

    def explain(self, text, signals, lang):
        return None
