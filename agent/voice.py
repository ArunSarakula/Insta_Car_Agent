"""AI voiceover for reels, from Google Cloud Text-to-Speech (an Indian
English voice). Optional: without an API key reels just have music."""

import base64
from pathlib import Path

import requests

URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
VOICES_URL = "https://texttospeech.googleapis.com/v1/voices"
VOICES = {"male": "en-IN-Neural2-B", "female": "en-IN-Neural2-A"}
# Voice families worth hearing; Standard ones sound robotic.
SAMPLE_FAMILIES = ("Neural2", "Wavenet", "Chirp3-HD", "Chirp-HD", "Studio")


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
    return path


def list_voices(api_key: str, session=requests) -> list[dict]:
    """Indian English voices worth sampling: [{"name", "gender"}], sorted."""
    r = session.get(VOICES_URL, params={"key": api_key, "languageCode": "en-IN"}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Listing voices failed ({r.status_code}): {r.text[:300]}")
    voices = [{"name": v["name"], "gender": v.get("ssmlGender", "").lower()} for v in r.json().get("voices", [])
              if v["name"].startswith("en-IN-") and any(f"-{f}-" in v["name"] for f in SAMPLE_FAMILIES)]
    return sorted(voices, key=lambda v: v["name"])
