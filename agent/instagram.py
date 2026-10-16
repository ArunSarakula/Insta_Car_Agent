"""Thin client for the official Instagram API (Instagram Login flavour,
graph.instagram.com). Works with Creator and Business accounts only."""

import time

import requests


class InstagramError(RuntimeError):
    pass


class Instagram:
    def __init__(self, access_token: str, user_id: str = "", api_version: str = "v23.0",
                 session: requests.Session | None = None):
        if not access_token:
            raise InstagramError("IG_ACCESS_TOKEN is not set. See README, step 3.")
        self.token = access_token
        self.base = f"https://graph.instagram.com/{api_version}"
        self.http = session or requests.Session()
        self._user_id = user_id

    # ---- low level ---------------------------------------------------------

    def _call(self, method: str, path: str, **params) -> dict:
        params["access_token"] = self.token
        if method == "GET":
            resp = self.http.get(f"{self.base}/{path}", params=params, timeout=60)
        else:
            resp = self.http.post(f"{self.base}/{path}", data=params, timeout=60)
        data = resp.json()
        if resp.status_code >= 400 or "error" in data:
            message = data.get("error", {}).get("message", resp.text)
            raise InstagramError(f"{method} {path} failed: {message}")
        return data

    @property
    def user_id(self) -> str:
        if not self._user_id:
            self._user_id = str(self._call("GET", "me", fields="user_id")["user_id"])
        return self._user_id

    # ---- account -----------------------------------------------------------

    def profile(self) -> dict:
        return self._call("GET", "me", fields="user_id,username,followers_count,media_count")

    # ---- publishing --------------------------------------------------------

    def _wait_until_ready(self, container_id: str, timeout_s: int = 300) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            status = self._call("GET", container_id, fields="status_code")["status_code"]
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise InstagramError(f"Media container {container_id} is {status}")
            time.sleep(5)
        raise InstagramError(f"Media container {container_id} not ready after {timeout_s}s")

    def _publish(self, container_id: str) -> str:
        self._wait_until_ready(container_id)
        return self._call("POST", f"{self.user_id}/media_publish", creation_id=container_id)["id"]

    def publish_image(self, image_url: str, caption: str) -> str:
        c = self._call("POST", f"{self.user_id}/media", image_url=image_url, caption=caption)
        return self._publish(c["id"])

    def publish_reel(self, video_url: str, caption: str) -> str:
        c = self._call("POST", f"{self.user_id}/media", media_type="REELS",
                       video_url=video_url, caption=caption)
        return self._publish(c["id"])

    def publish_reel_file(self, video_path: str, caption: str, cover_url: str = "") -> str:
        """Upload a local video straight to Instagram (resumable upload), so
        the video doesn't need a public URL."""
        params = {"media_type": "REELS", "upload_type": "resumable", "caption": caption}
        if cover_url:
            params["cover_url"] = cover_url
        c = self._call("POST", f"{self.user_id}/media", **params)
        with open(video_path, "rb") as f:
            data = f.read()
        upload_url = c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{self.base.rsplit('/', 1)[1]}/{c['id']}"
        resp = self.http.post(upload_url, data=data, timeout=300, headers={
            "Authorization": f"OAuth {self.token}", "offset": "0", "file_size": str(len(data))})
        if resp.status_code >= 400:
            raise InstagramError(f"Video upload failed: {resp.text}")
        return self._publish(c["id"])

    def publish_carousel(self, image_urls: list[str], caption: str) -> str:
        if not 2 <= len(image_urls) <= 10:
            raise InstagramError("A carousel needs 2 to 10 images")
        children = []
        for url in image_urls:
            child = self._call("POST", f"{self.user_id}/media", image_url=url,
                               is_carousel_item="true")
            self._wait_until_ready(child["id"])
            children.append(child["id"])
        c = self._call("POST", f"{self.user_id}/media", media_type="CAROUSEL",
                       children=",".join(children), caption=caption)
        return self._publish(c["id"])

    # ---- comments ----------------------------------------------------------

    def recent_media(self, limit: int = 10) -> list[dict]:
        fields = "id,caption,timestamp,permalink,like_count,comments_count,media_type"
        return self._call("GET", f"{self.user_id}/media", fields=fields, limit=limit)["data"]

    def comments(self, media_id: str) -> list[dict]:
        fields = "id,text,username,timestamp,replies{id,username}"
        return self._call("GET", f"{media_id}/comments", fields=fields)["data"]

    def reply_to_comment(self, comment_id: str, message: str) -> str:
        return self._call("POST", f"{comment_id}/replies", message=message)["id"]

    # ---- insights ----------------------------------------------------------

    def media_insights(self, media_id: str) -> dict:
        metrics = "reach,likes,comments,saved,shares"
        data = self._call("GET", f"{media_id}/insights", metric=metrics)["data"]
        return {m["name"]: m["values"][0]["value"] for m in data if m.get("values")}
