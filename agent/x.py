"""Posts reels and memes to X (Twitter) through the X API v2.

Needs an X developer app with Read and write permission and its four
OAuth 1.0a keys (see README). Requests are signed here, so no extra
library is needed."""

import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import quote

import requests

API = "https://api.x.com/2"
CHUNK = 4 * 1024 * 1024


class XError(RuntimeError):
    pass


def _enc(s) -> str:
    return quote(str(s), safe="~-._")


def signature(method: str, url: str, params: dict, consumer_secret: str, token_secret: str) -> str:
    """OAuth 1.0a HMAC-SHA1 signature over the method, URL and query/oauth params."""
    pairs = "&".join(f"{k}={v}" for k, v in sorted((_enc(k), _enc(v)) for k, v in params.items()))
    base = "&".join([method.upper(), _enc(url), _enc(pairs)])
    key = f"{_enc(consumer_secret)}&{_enc(token_secret)}"
    return base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()


class X:
    def __init__(self, api_key: str, api_secret: str, access_token: str, access_secret: str,
                 session: requests.Session | None = None):
        if not (api_key and api_secret and access_token and access_secret):
            raise XError("X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN and X_ACCESS_SECRET must be set")
        self.key, self.secret, self.token, self.token_secret = api_key, api_secret, access_token, access_secret
        self.http = session or requests.Session()

    def _auth(self, method: str, url: str, query: dict | None = None) -> str:
        oauth = {"oauth_consumer_key": self.key, "oauth_nonce": secrets.token_hex(16),
                 "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(int(time.time())),
                 "oauth_token": self.token, "oauth_version": "1.0"}
        oauth["oauth_signature"] = signature(method, url, {**(query or {}), **oauth}, self.secret,
                                             self.token_secret)
        return "OAuth " + ", ".join(f'{_enc(k)}="{_enc(v)}"' for k, v in sorted(oauth.items()))

    def _call(self, method: str, path: str, query: dict | None = None, **kw) -> dict:
        url = f"{API}{path}"
        resp = self.http.request(method, url, params=query,
                                 headers={"Authorization": self._auth(method, url, query)}, timeout=120, **kw)
        if resp.status_code >= 400:
            raise XError(f"X {method} {path} failed ({resp.status_code}): {resp.text}")
        return resp.json() if resp.content else {}

    def me(self) -> dict:
        return self._call("GET", "/users/me")["data"]

    def upload(self, path: str) -> str:
        """Uploads an image or an MP4 in chunks and waits until X has processed it."""
        with open(path, "rb") as f:
            data = f.read()
        video = path.endswith(".mp4")
        init = self._call("POST", "/media/upload/initialize", json={
            "media_type": "video/mp4" if video else "image/jpeg", "total_bytes": len(data),
            "media_category": "tweet_video" if video else "tweet_image"})["data"]
        media_id = init["id"]
        for i in range(0, len(data), CHUNK):
            self._call("POST", f"/media/upload/{media_id}/append",
                       data={"segment_index": str(i // CHUNK)}, files={"media": data[i:i + CHUNK]})
        info = self._call("POST", f"/media/upload/{media_id}/finalize").get("data", {})
        for _ in range(60):
            state = (info.get("processing_info") or {}).get("state")
            if state in (None, "succeeded"):
                return media_id
            if state == "failed":
                raise XError(f"X could not process the media: {info['processing_info']}")
            time.sleep((info["processing_info"].get("check_after_secs") or 3))
            info = self._call("GET", "/media/upload", {"command": "STATUS", "media_id": media_id}).get("data", {})
        raise XError("X took too long to process the media")

    def post(self, text: str, media_path: str | None = None) -> str:
        body = {"text": text}
        if media_path:
            body["media"] = {"media_ids": [self.upload(media_path)]}
        return self._call("POST", "/tweets", json=body)["data"]["id"]
