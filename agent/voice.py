"""AI voiceover for reels, from Google Cloud Text-to-Speech (an Indian
English voice). Optional: without an API key reels just have music."""

import base64
from pathlib import Path

import requests

URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
VOICES = {"male": "en-IN-Neural2-B", "female": "en-IN-Neural2-A"}


def synthesize(text: str, path: Path, api_key: str, session=requests, voice: str = "male") -> Path:
    r = session.post(URL, params={"key": api_key}, timeout=60, json={
        "input": {"text": text},
        "voice": {"languageCode": "en-IN", "name": VOICES.get(voice, VOICES["male"])},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.1},
    })
    if r.status_code != 200:
        raise RuntimeError(f"Text-to-speech failed ({r.status_code}): {r.text[:300]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(r.json()["audioContent"]))
    return path
