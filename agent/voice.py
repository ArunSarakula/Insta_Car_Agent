"""AI voiceover for reels, from Google Cloud Text-to-Speech (an Indian
English voice). Optional: without an API key reels just have music."""

import base64
from pathlib import Path

import requests

URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
VOICE = {"languageCode": "en-IN", "name": "en-IN-Neural2-B"}


def synthesize(text: str, path: Path, api_key: str, session=requests) -> Path:
    r = session.post(URL, params={"key": api_key}, timeout=60, json={
        "input": {"text": text},
        "voice": VOICE,
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.1},
    })
    if r.status_code != 200:
        raise RuntimeError(f"Text-to-speech failed ({r.status_code}): {r.text[:300]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(r.json()["audioContent"]))
    return path
