"""Uploads reels to YouTube as Shorts (YouTube Data API v3).

Needs a Google Cloud OAuth client and a refresh token for the channel (see
README). Note: YouTube keeps videos uploaded through an API project private
until the project passes YouTube's free API audit."""

import json

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
AUTOS_AND_VEHICLES = "2"


class YouTubeError(RuntimeError):
    pass


class YouTube:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str,
                 session: requests.Session | None = None):
        if not (client_id and client_secret and refresh_token):
            raise YouTubeError("YT_CLIENT_ID, YT_CLIENT_SECRET and YT_REFRESH_TOKEN must be set")
        self.creds = {"client_id": client_id, "client_secret": client_secret,
                      "refresh_token": refresh_token, "grant_type": "refresh_token"}
        self.http = session or requests.Session()

    def _token(self) -> str:
        resp = self.http.post(TOKEN_URL, data=self.creds, timeout=60)
        if resp.status_code >= 400:
            raise YouTubeError(f"Google sign-in failed: {resp.text}")
        return resp.json()["access_token"]

    def upload_short(self, video_path: str, title: str, description: str,
                     tags: list[str], privacy: str = "public") -> str:
        with open(video_path, "rb") as f:
            data = f.read()
        token = self._token()
        meta = {"snippet": {"title": title[:100], "description": description[:5000],
                            "tags": tags[:15], "categoryId": AUTOS_AND_VEHICLES},
                "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
        start = self.http.post(
            f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status", data=json.dumps(meta),
            timeout=60, headers={"Authorization": f"Bearer {token}",
                                 "Content-Type": "application/json; charset=UTF-8",
                                 "X-Upload-Content-Type": "video/mp4",
                                 "X-Upload-Content-Length": str(len(data))})
        if start.status_code >= 400 or "Location" not in start.headers:
            raise YouTubeError(f"Upload could not start: {start.text}")
        done = self.http.put(start.headers["Location"], data=data, timeout=600,
                             headers={"Content-Type": "video/mp4"})
        if done.status_code >= 400:
            raise YouTubeError(f"Upload failed: {done.text}")
        return done.json()["id"]
