"""Tell the family. The parent shouldn't have to decide alone.

Alerts never include account numbers, links or phone numbers from the scam —
just what happened and that someone should call.
"""
from __future__ import annotations

import os
import time
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
    """Push to a phone via an ntfy server (self-hosted or ntfy.sh).

    Published as JSON so Korean titles survive (ntfy's header form is ASCII-only).
    `call` = (button label, phone number) adds a one-tap "Call Dad" button to the push.
    """

    TRIES = 3  # a web shield in front of ntfy can 403 the first post from a new client

    def __init__(self, server: str | None = None, topic: str | None = None, token: str | None = None,
                 call: tuple[str, str] | None = None, client: httpx.Client | None = None,
                 retry_wait: float = 1.0):
        self.server = (server or os.environ.get("NTFY_SERVER", "https://ntfy.sh")).rstrip("/")
        self.topic = topic or os.environ["NTFY_TOPIC"]
        self.token = token or os.environ.get("NTFY_TOKEN")
        self.call = call if call and call[1] else None
        self.client = client or httpx.Client(timeout=10)
        self.retry_wait = retry_wait

    def send(self, title, body, urgent):
        msg = {"topic": self.topic, "title": title, "message": body, "priority": 5 if urgent else 4,
               "tags": ["rotating_light" if urgent else "warning"]}
        if self.call:
            label, number = self.call
            msg["actions"] = [{"action": "view", "label": label, "url": "tel:" + number, "clear": True}]
        h = {"User-Agent": "family-fraud-shield/0.1"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        for attempt in range(self.TRIES):
            if attempt:
                time.sleep(self.retry_wait * attempt)
            try:
                r = self.client.post(self.server, json=msg, headers=h)
            except httpx.HTTPError:
                continue
            if r.is_success:
                return True
            if r.status_code not in (403, 429) and r.status_code < 500:
                return False  # bad topic or token: trying again won't help
        return False


def family_alert(who: str, verdict: Verdict, what: str) -> tuple[str, str]:
    """(title, body) for a family member. `what` = 'a text' / 'a voicemail' / 'their bank account'."""
    if verdict.level == Level.SCAM:
        title = f"{who} got a likely scam"
    else:
        title = f"{who}: something to double-check"
    reasons = [s.detail_en for s in sorted(verdict.signals, key=lambda s: -s.weight)[:2]]
    body = (f"Pausebird checked {what} for {who}.\n"
            + "\n".join(f"- {r}" for r in reasons)
            + f"\nPlease call {who} to check in.")
    return title, body


def notify(notifier: Notifier, who: str, verdict: Verdict, what: str) -> bool:
    if verdict.level == Level.SAFE:
        return False
    title, body = family_alert(who, verdict, what)
    return notifier.send(title, body, urgent=verdict.level == Level.SCAM)
