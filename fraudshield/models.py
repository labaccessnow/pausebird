"""Core data types shared by the checks, the agent and the UI."""
from __future__ import annotations

import datetime as dt
from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, Field


class Level(IntEnum):
    SAFE = 0
    CAUTION = 1
    SCAM = 2


class Signal(BaseModel):
    """One piece of evidence. Every verdict must be traceable to signals."""
    code: str                      # stable id, e.g. "link.lookalike_brand"
    weight: int                    # contribution to the 0-100 risk score
    evidence: str                  # the exact text/value that triggered it
    detail_en: str                 # plain-English reason, one sentence
    detail_ko: str                 # plain-Korean reason, one sentence
    hard: bool = False             # a hard signal alone is enough for SCAM


class Message(BaseModel):
    text: str
    sender: Optional[str] = None   # phone number, email or display name
    channel: str = "sms"           # sms | kakaotalk | email | voicemail | other
    claimed_from: Optional[str] = None  # who it says it is from, if known


class Verdict(BaseModel):
    level: Level
    score: int = Field(ge=0, le=100)
    signals: list[Signal]
    summary_en: str
    summary_ko: str
    next_steps: list[str] = []
    model_opinion: Optional[str] = None  # what the LLM added, kept separate from rule evidence
    model_opinion_ko: Optional[str] = None  # the same, in Korean


class CheckItem(BaseModel):
    """A check: either one the customer wrote (register) or one that cleared (bank)."""
    number: int
    amount: float
    payee: str
    date: Optional[dt.date] = None  # dt.date: a bare `date` here would be shadowed by the field
    micr_number: Optional[int] = None    # check number printed in the MICR line, if read
    image: Optional[str] = None          # path to the check image, if any
    notes: Optional[str] = None          # anything the vision model noticed


class CheckFinding(BaseModel):
    check: CheckItem
    level: Level
    signals: list[Signal]
