"""Command line: check a message, a screenshot, a voicemail, or a bank account.

    fraudshield message "text" [--sender +1...] [--online]
    fraudshield screenshot shot.png          (needs MODEL_API_KEY)
    fraudshield voicemail vm.m4a             (needs MODEL_API_KEY)
    fraudshield checks cleared.csv register.csv [--read-images]
    fraudshield demo
    fraudshield serve [--host 127.0.0.1] [--port 8000]   (the phone web page)
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from pathlib import Path

from . import agent
from .ledger import read_checks
from .llm import pick_brain
from .llm.base import Brain, OfflineBrain
from .models import Level, Message, Verdict

COLOR = {Level.SCAM: "\033[1;31m", Level.CAUTION: "\033[1;33m", Level.SAFE: "\033[1;32m"}
RESET = "\033[0m"
DEMO = Path(__file__).resolve().parent.parent / "demo"


def show(v: Verdict, lang: str) -> None:
    print(f"{COLOR[v.level]}{v.level.name}{RESET}  score {v.score}/100")
    print(v.summary_ko if lang == "ko" else v.summary_en)
    for s in sorted(v.signals, key=lambda s: -s.weight):
        print(f"  [{s.weight:>2}{'!' if s.hard else ' '}] {s.code:<26} {s.evidence}")
    if v.model_opinion:
        print(f"  model: {v.model_opinion}")
    for i, step in enumerate(v.next_steps, 1):
        print(f"  {i}. {step}")


def cmd_checks(cleared_csv: Path, register_csv: Path, b: Brain, read_images: bool, lang: str) -> Verdict:
    cleared, register = read_checks(cleared_csv), read_checks(register_csv)
    if read_images:
        cleared = agent.read_check_images(cleared, b)
    v, findings = agent.check_account(cleared, register)
    for f in findings:
        c = f.check
        print(f"{COLOR[f.level]}{f.level.name:<7}{RESET} #{c.number:<5} {str(c.date or ''):<10} "
              f"${c.amount:>9,.2f}  {c.payee}")
        for s in f.signals:
            print(f"           - {s.detail_ko if lang == 'ko' else s.detail_en}")
    print()
    show(v, lang)
    return v


def cmd_demo(b: Brain, lang: str) -> int:
    data = json.loads((DEMO / "messages.json").read_text(encoding="utf-8"))
    ages = data["rdap_fixture_days"]
    wrong = 0
    for m in data["messages"]:
        msg = Message(text=m["text"], sender=m["sender"], channel=m["channel"])
        v = agent.check_message(msg, brain=b, rdap=lambda d: ages.get(d))
        ok = v.level.name == m["expect"] or (m["expect"] == "SCAM" and v.level == Level.SCAM)
        wrong += not ok
        print(f"\n=== {m['id']} ({m['channel']}) expect {m['expect']} {'✓' if ok else '✗'}")
        print(f"    {m['text'][:110]}")
        show(v, lang)
    print("\n=== account watch (demo checkbook)")
    cmd_checks(DEMO / "cleared.csv", DEMO / "register.csv", b, read_images=not isinstance(b, OfflineBrain),
               lang=lang)
    print(f"\n{len(data['messages']) - wrong}/{len(data['messages'])} messages judged as expected")
    return 1 if wrong else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fraudshield")
    ap.add_argument("--lang", choices=["en", "ko"], default="en")
    ap.add_argument("--offline", action="store_true", help="rules only, no model calls")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("message"); m.add_argument("text"); m.add_argument("--sender")
    m.add_argument("--online", action="store_true", help="look up domain age (RDAP)")
    s = sub.add_parser("screenshot"); s.add_argument("image", type=Path)
    vm = sub.add_parser("voicemail"); vm.add_argument("audio", type=Path)
    c = sub.add_parser("checks"); c.add_argument("cleared", type=Path); c.add_argument("register", type=Path)
    c.add_argument("--read-images", action="store_true")
    sub.add_parser("demo")
    sv = sub.add_parser("serve"); sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000)
    sv.add_argument("--log", type=Path, help="append server output to this file (pythonw on Windows has no console)")
    a = ap.parse_args(argv)
    if a.cmd == "serve":
        import uvicorn
        from .web import create_app
        if a.log:
            a.log.parent.mkdir(parents=True, exist_ok=True)
            sys.stdout = sys.stderr = open(a.log, "a", encoding="utf-8", buffering=1)
        # No brain passed in: create_app picks it, and only then also builds the judges' own (capped) one.
        uvicorn.run(create_app(offline=a.offline), host=a.host, port=a.port)
        return 0
    b = pick_brain(a.offline)

    if a.cmd == "message":
        show(agent.check_message(Message(text=a.text, sender=a.sender), brain=b, online=a.online), a.lang)
    elif a.cmd in ("screenshot", "voicemail"):
        if isinstance(b, OfflineBrain):
            sys.exit("This needs the model: set MODEL_API_KEY.")
        raw, mime = a.__dict__["image" if a.cmd == "screenshot" else "audio"].read_bytes(), None
        mime = mimetypes.guess_type(str(a.image if a.cmd == "screenshot" else a.audio))[0] or "application/octet-stream"
        if a.cmd == "screenshot":
            msg = b.read_screenshot(raw, mime)
        else:
            msg = Message(text=b.transcribe(raw, mime) or "", channel="voicemail")
        print(f"read: {msg.text}\n")
        show(agent.check_message(msg, brain=b, online=True), a.lang)
    elif a.cmd == "checks":
        cmd_checks(a.cleared, a.register, b, a.read_images, a.lang)
    elif a.cmd == "demo":
        return cmd_demo(b, a.lang)
    return 0


if __name__ == "__main__":
    sys.exit(main())
