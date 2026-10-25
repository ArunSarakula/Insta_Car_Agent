"""AI voiceover for reels, from Google Cloud Text-to-Speech (an Indian
English voice). Optional: without an API key reels just have music."""

import base64
import json
from datetime import date
from pathlib import Path

import requests

URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
VOICES_URL = "https://texttospeech.googleapis.com/v1/voices"
VOICES = {"male": "en-IN-Neural2-B", "female": "en-IN-Neural2-A"}
# Voice families worth hearing; Standard ones sound robotic.
SAMPLE_FAMILIES = ("Neural2", "Wavenet", "Chirp3-HD", "Chirp-HD", "Studio")
# Characters free each month and US$ per million after that, by voice family
# (cloud.google.com/text-to-speech/pricing, checked 25 Oct 2026).
PRICING = {"Chirp3-HD": (1_000_000, 30), "Chirp-HD": (1_000_000, 30), "Neural2": (1_000_000, 16),
           "Studio": (1_000_000, 160), "Wavenet": (4_000_000, 4), "Standard": (4_000_000, 4)}
INR_PER_USD = 88  # rough, for the monthly estimate
USAGE_FILE: Path | None = None  # set by the CLI; characters used per month and voice family


def voice_name(voice: str) -> str:
    """"male", "female" or a full Google voice name such as en-IN-Chirp3-HD-Charon."""
    return VOICES.get(voice) or (voice if voice.startswith("en-IN-") else VOICES["male"])


def synthesize(text: str, path: Path, api_key: str, session=requests, voice: str = "male") -> Path:
    name = voice_name(voice)
    audio = {"audioEncoding": "MP3"}
    if "Chirp" not in name:  # Chirp voices pace themselves
        audio["speakingRate"] = 1.1
    r = session.post(URL, params={"key": api_key}, timeout=60, json={
        "input": {"text": text},
        "voice": {"languageCode": "en-IN", "name": name},
        "audioConfig": audio,
    })
    if r.status_code != 200:
        raise RuntimeError(f"Text-to-speech failed ({r.status_code}): {r.text[:300]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(r.json()["audioContent"]))
    if USAGE_FILE:
        record_usage(USAGE_FILE, name, len(text))
    return path


def family(name: str) -> str:
    return next((f for f in PRICING if f"-{f}-" in name), "Standard")


def record_usage(path: Path, name: str, chars: int, month: str | None = None) -> None:
    usage = json.loads(path.read_text()) if path.exists() else {}
    m = usage.setdefault(month or date.today().strftime("%Y-%m"), {})
    m[family(name)] = m.get(family(name), 0) + chars
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(usage, indent=2, sort_keys=True) + "\n")


def usage_summary(path: Path, month: str | None = None) -> str:
    """One month's characters per voice family, the free share used and the cost."""
    month = month or date.today().strftime("%Y-%m")
    used = (json.loads(path.read_text()) if path.exists() else {}).get(month, {})
    if not used:
        return f"AI voice, {month}: nothing used yet. Cost: free."
    lines, cost = [f"AI voice, {month}:"], 0.0
    for fam, chars in sorted(used.items()):
        free, per_million = PRICING.get(fam, PRICING["Standard"])
        paid = max(0, chars - free) * per_million / 1_000_000
        cost += paid
        lines.append(f"- {fam}: {chars:,} characters of {free:,} free ({chars / free:.1%})"
                     + (f", US${paid:.2f} over the free amount" if paid else ""))
    lines.append(f"Cost: about ₹{cost * INR_PER_USD:,.0f}." if cost else "Cost: free (inside Google's free amount).")
    return "\n".join(lines)


def list_voices(api_key: str, session=requests) -> list[dict]:
    """Indian English voices worth sampling: [{"name", "gender"}], sorted."""
    r = session.get(VOICES_URL, params={"key": api_key, "languageCode": "en-IN"}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Listing voices failed ({r.status_code}): {r.text[:300]}")
    voices = [{"name": v["name"], "gender": v.get("ssmlGender", "").lower()} for v in r.json().get("voices", [])
              if v["name"].startswith("en-IN-") and any(f"-{f}-" in v["name"] for f in SAMPLE_FAMILIES)]
    return sorted(voices, key=lambda v: v["name"])
