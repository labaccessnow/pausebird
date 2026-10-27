# Family Fraud Shield

Catches scam messages and fake checks before an older parent loses money — and tells the family.

Built for the **Meta Global AI Developer Hackathon** (Oct 26 – Nov 4, 2026), Build for Your World track.
All code in this repository was written during the hackathon.

## Why

Two things happened to people close to me:

- My real estate agent clicked a link in a text, and the scammers emptied his bank accounts.
- Someone printed fake checks using my dad's account numbers and drew money out of his checking account.
  The bank paid them. The bank gave some of it back.

Both were stoppable. The text had every classic sign of a scam. The checks didn't match anything my dad
actually wrote. Nobody was looking.

## What it does

**1. Scam Shield — "should I trust this message?"**
Forward a text, a KakaoTalk screenshot, an email, or a voicemail. It:

- reads screenshots and transcribes voicemails (Muse Spark, Muse Voice Transcribe — Korean included)
- checks every link **without opening it**: look-alike brands, typo-squats, punycode, shorteners, and how
  many days ago the domain was registered (public RDAP registry)
- checks phone numbers (e.g. Korean 070 internet lines used by voice-phishing rings)
- spots the pressure tricks in English and Korean: urgency, "safe account", fake prosecutors,
  "Mom, my phone broke", gift cards, secrecy
- answers in plain Korean or English, with steps that are fixed and checked — never invented

**2. Account Watch — "did I write this check?"**
Compares the checks the bank paid with the checks the person actually wrote, and reads each check image:

- check never written / number outside the checkbook (counterfeit)
- amount or payee changed (check washing)
- the same check number paid twice (copied check)
- the printed number doesn't match the bank line at the bottom (fake check stock)
- several bad checks within a week (someone has the account numbers)

**3. Family alert** — when something is wrong, a family member gets a push alert: what happened and
"please call". No links, numbers or account details in the alert.

## Design: rules you can verify, a model that adds eyes and ears

Every verdict is built from **signals** — each with the exact evidence that triggered it. Rules run first;
Muse Spark reads images and audio, gives a second opinion, and writes the plain-language explanation.
The model can raise the risk but can never erase a hard rule hit, so a persuasive scam can't talk its way
past the checks.

Privacy: standard Meta Model API tier only — `-contributor` models (which train on inputs) are refused in
code. Meta's billing "spend limit" is an email alert, not a cap, so the client keeps its own budget.

## The phone page

One page, big buttons, English and 한국어. Paste a message, pick a screenshot or a voicemail, and get a
red, yellow or green answer with fixed next steps. If it's a scam there are two more buttons:
**Tell my family** (a push alert) and **I already clicked, called, or paid** (the urgent steps).
The second tab compares the checks the bank paid with the checkbook.

On Android, install the page (browser menu → *Add to Home screen*) and it appears in the **Share**
sheet: share a text or a screenshot straight from Messages or KakaoTalk.

Safety details: scam links are shown as `hxxps://bad[.]top` so they can't be tapped, phone numbers are
not turned into links, nothing is saved, and the service worker caches nothing.

## Run it

```bash
uv venv && uv pip install -e ".[dev]"
python demo/make_demo_data.py          # fake checkbook + check images
python -m fraudshield.cli --offline demo   # rules only, no API key needed
pytest -q

python -m fraudshield.cli --offline serve --port 8000   # the phone page at http://127.0.0.1:8000

export MODEL_API_KEY=...               # Meta Model API key
python -m fraudshield.cli demo         # adds check-image reading, second opinions, plain-language replies
python -m fraudshield.cli screenshot shot.png
python -m fraudshield.cli voicemail vm.m4a --lang ko
python -m fraudshield.cli serve        # page with screenshots and voicemails turned on
```

Settings (environment variables):

| Variable | What it does | Default |
|---|---|---|
| `MODEL_API_KEY` | Meta Model API key; without it the page runs on rules only | — |
| `FRAUDSHIELD_BUDGET_USD` | stop calling the model after this much spend | `140` |
| `NTFY_SERVER`, `NTFY_TOPIC`, `NTFY_TOKEN` | where "Tell my family" sends the push alert | console only |
| `FRAUDSHIELD_PARENT_PHONE` | adds a one-tap "Call Dad" button to the push alert | no button |
| `FRAUDSHIELD_PARENT` | what alerts and English answers call the parent | `Dad` |
| `FRAUDSHIELD_PARENT_KO` | what Korean answers call the parent | `아버지` |
| `FRAUDSHIELD_LANG` | page language when the phone isn't set to Korean | `en` |
| `FRAUDSHIELD_DEMO` | show the example messages and demo checkbook | `1` |
| `FRAUDSHIELD_OFFLINE` | no model and no registry lookups | `0` |
| `FRAUDSHIELD_PASSCODE` | ask for this passcode once per phone (set it when the page is on the internet) | none |

Installing the page and the Share button need HTTPS, except on `localhost`.

## Demo data

Everything in `demo/` is made up: names, bank, account and routing numbers, links and phone numbers. The
messages are modeled on common real scams. The app never opens a link from a message.

## License

MIT
