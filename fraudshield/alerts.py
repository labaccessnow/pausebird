"""Tell the family. The parent shouldn't have to decide alone.

Alerts never include account numbers, links or phone numbers from the scam —
just what happened and that someone should call.
"""
from __future__ import annotations

import os
from typing import Protocol

import httpx

from .models import Level, Verdict


class Notifier(Protocol):
    def send(self, title: str, body: str, urgent: bool) -> bool: ...


class ConsoleNotifier:
    def send(self, title, body, urgent):
        print(f"[{'URGENT' if urgent else 'info'}] {title}\n{body}")
        return True


class NtfyNotifier:
    """Push to a phone via an ntfy server (self-hosted or ntfy.sh)."""

    def __init__(self, server: str | None = None, topic: str | None = None, token: str | None = None):
        self.server = (server or os.environ.get("NTFY_SERVER", "https://ntfy.sh")).rstrip("/")
        self.topic = topic or os.environ["NTFY_TOPIC"]
        self.token = token or os.environ.get("NTFY_TOKEN")

    def send(self, title, body, urgent):
        h = {"Title": title.encode("ascii", "replace").decode(), "Priority": "urgent" if urgent else "default",
             "Tags": "rotating_light" if urgent else "warning"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        try:
            httpx.post(f"{self.server}/{self.topic}", content=body.encode(), headers=h, timeout=15).raise_for_status()
            return True
        except httpx.HTTPError:
            return False


def family_alert(who: str, verdict: Verdict, what: str) -> tuple[str, str]:
    """(title, body) for a family member. `what` = 'a text' / 'a voicemail' / 'their bank account'."""
    if verdict.level == Level.SCAM:
        title = f"{who} got a likely scam"
    else:
        title = f"{who}: something to double-check"
    reasons = [s.detail_en for s in sorted(verdict.signals, key=lambda s: -s.weight)[:2]]
    body = (f"Family Fraud Shield checked {what} for {who}.\n"
            + "\n".join(f"- {r}" for r in reasons)
            + f"\nPlease call {who} to check in.")
    return title, body


def notify(notifier: Notifier, who: str, verdict: Verdict, what: str) -> bool:
    if verdict.level == Level.SAFE:
        return False
    title, body = family_alert(who, verdict, what)
    return notifier.send(title, body, urgent=verdict.level == Level.SCAM)
