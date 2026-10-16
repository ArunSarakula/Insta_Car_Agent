import json
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from agent import cli, store
from agent.brain import Brain
from agent.instagram import Instagram, InstagramError

IST = ZoneInfo("Asia/Kolkata")


# ---- scheduling ------------------------------------------------------------

def test_next_occurrence_is_always_in_the_future():
    thursday = date(2026, 10, 15)
    assert next_iso("Fri", thursday) == "2026-10-16T19:30:00+05:30"
    assert next_iso("Thu", thursday) == "2026-10-22T19:30:00+05:30"  # a week later, not today
    assert next_iso("Mon", thursday) == "2026-10-19T19:30:00+05:30"


def next_iso(day, today):
    return cli.next_occurrence(day, "19:30", today, IST).isoformat()


# ---- queue -----------------------------------------------------------------

def test_only_approved_and_due_posts_are_published(tmp_path):
    now = datetime(2026, 10, 16, 20, 0, tzinfo=IST)
    past = (now - timedelta(hours=1)).isoformat()
    future = (now + timedelta(hours=1)).isoformat()
    store.save_post({"id": "a", "status": "approved", "scheduled_for": past}, tmp_path)
    store.save_post({"id": "b", "status": "draft", "scheduled_for": past}, tmp_path)
    store.save_post({"id": "c", "status": "approved", "scheduled_for": future}, tmp_path)
    store.save_post({"id": "d", "status": "published", "scheduled_for": past}, tmp_path)
    assert [p["id"] for p in store.due_posts(now, tmp_path)] == ["a"]


def test_set_status_rejects_unknown_status(tmp_path):
    store.save_post({"id": "a"}, tmp_path)
    with pytest.raises(ValueError):
        store.set_status("a", "posted", tmp_path)


def test_media_urls_from_repo_files():
    post = {"media_files": ["media/one.jpg"]}
    assert cli.media_urls(post, "me/repo") == [
        "https://raw.githubusercontent.com/me/repo/main/media/one.jpg"]
    assert cli.media_urls({"media_urls": ["https://x/y.jpg"]}, "me/repo") == ["https://x/y.jpg"]
    assert cli.media_urls(post, "") == []


def test_caption_appends_hashtags():
    post = {"caption": "EVs explained", "hashtags": ["#ev", "#cars"]}
    assert cli.caption_for(post) == "EVs explained\n.\n.\n#ev #cars"


# ---- instagram client ------------------------------------------------------

class FakeHTTP:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def _respond(self, method, url, params):
        path = url.split("/v23.0/")[1]
        self.calls.append((method, path, params))
        body = self.responses[(method, path)]
        return SimpleNamespace(status_code=400 if "error" in body else 200,
                               json=lambda: body, text=json.dumps(body))

    def get(self, url, params, timeout):
        return self._respond("GET", url, params)

    def post(self, url, data, timeout, headers=None):
        if url.startswith("https://rupload"):
            self.calls.append(("UPLOAD", url, headers))
            return SimpleNamespace(status_code=200, text="ok")
        return self._respond("POST", url, data)


def test_publish_image_creates_container_then_publishes():
    http = FakeHTTP({
        ("POST", "42/media"): {"id": "c1"},
        ("GET", "c1"): {"status_code": "FINISHED"},
        ("POST", "42/media_publish"): {"id": "m1"},
    })
    ig = Instagram("tok", "42", session=http)
    assert ig.publish_image("https://x/y.jpg", "hi") == "m1"
    assert http.calls[0][2]["image_url"] == "https://x/y.jpg"
    assert http.calls[2][2]["creation_id"] == "c1"


def test_api_errors_are_raised():
    http = FakeHTTP({("POST", "42/media"): {"error": {"message": "Invalid token"}}})
    ig = Instagram("tok", "42", session=http)
    with pytest.raises(InstagramError, match="Invalid token"):
        ig.publish_image("https://x/y.jpg", "hi")


def test_missing_token_is_a_clear_error():
    with pytest.raises(InstagramError, match="IG_ACCESS_TOKEN"):
        Instagram("")


# ---- brain -----------------------------------------------------------------

class FakeClaude:
    def __init__(self, payload, stop_reason="end_turn"):
        self.kwargs = None
        msg = SimpleNamespace(stop_reason=stop_reason,
                              content=[SimpleNamespace(type="text", text=json.dumps(payload))])

        def create(**kwargs):
            self.kwargs = kwargs
            return msg

        self.beta = SimpleNamespace(messages=SimpleNamespace(create=create))


def test_weekly_plan_requests_structured_output():
    plan = {"theme": "EV myths", "posts": [], "story_polls": []}
    fake = FakeClaude(plan)
    assert Brain("cars", client=fake).weekly_plan(5, []) == plan
    assert fake.kwargs["model"] == "claude-opus-5-5"
    assert fake.kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "exactly 5 feed posts" in fake.kwargs["messages"][0]["content"]


def test_refusal_raises():
    with pytest.raises(RuntimeError):
        Brain("cars", client=FakeClaude({}, stop_reason="refusal")).weekly_plan(5, [])


def test_reel_is_uploaded_from_local_file(tmp_path):
    video = tmp_path / "reel.mp4"
    video.write_bytes(b"0123456789")
    http = FakeHTTP({
        ("POST", "42/media"): {"id": "c9", "uri": "https://rupload.facebook.com/ig-api-upload/v23.0/c9"},
        ("GET", "c9"): {"status_code": "FINISHED"},
        ("POST", "42/media_publish"): {"id": "m9"},
    })
    assert Instagram("tok", "42", session=http).publish_reel_file(str(video), "hi") == "m9"
    assert http.calls[0][2]["upload_type"] == "resumable"
    upload = http.calls[1]
    assert upload[0] == "UPLOAD" and upload[2]["file_size"] == "10"


# ---- design ----------------------------------------------------------------

from PIL import Image

from agent import design

SLIDES = [{"heading": "Your Level 2 ADAS car is NOT self-driving 🚗", "body": ""},
          {"heading": "What it does", "body": "Keeps you in lane and keeps distance from the car ahead."},
          {"heading": "Follow @decodethedrive", "body": "Car tech, explained like a friend in IT would."}]


def test_clean_strips_emoji():
    assert design.clean("EVs 🔋 explained ⚡️") == "EVs explained"


def test_carousel_renders_one_portrait_jpg_per_slide(tmp_path):
    files = design.render_post({"id": "p1", "format": "carousel", "slides": SLIDES}, tmp_path / "media")
    assert files == [f"media/p1/slide-{i}.jpg" for i in (1, 2, 3)]
    assert Image.open(tmp_path / files[0]).size == (1080, 1350)


def test_single_slide_carousel_falls_back_to_image(tmp_path):
    files = design.render_post({"id": "p2", "format": "carousel", "slides": SLIDES[:1]}, tmp_path / "media")
    assert files == ["media/p2/post.jpg"]


def test_reel_renders_vertical_video_with_cover(tmp_path):
    files = design.render_post({"id": "p3", "format": "reel", "slides": SLIDES}, tmp_path / "media")
    assert files == ["media/p3/reel.mp4"]
    assert (tmp_path / "media/p3/reel.mp4").stat().st_size > 10_000
    assert Image.open(tmp_path / "media/p3/cover.jpg").size == (1080, 1920)


# ---- plan end to end -------------------------------------------------------

class FakeBrain:
    def weekly_plan(self, n, recent):
        return {"theme": "Basics", "story_polls": [
            {"day": "Mon", "question": "EV next?", "option_a": "Yes", "option_b": "No"}],
            "posts": [{"format": "meme", "title": "Reboot", "hook": "h", "caption": "c",
                       "hashtags": ["#cars"], "day": "Fri", "time": "21:00",
                       "slides": [{"heading": "Screen froze", "body": "Turn it off and on"}]}]}


def test_plan_designs_media_and_approve_all(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(store, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(store.save_post, "__defaults__", (tmp_path / "queue",))
    monkeypatch.setattr(store.load_posts, "__defaults__", (tmp_path / "queue",))
    monkeypatch.setattr(store.get_post, "__defaults__", (tmp_path / "queue",))
    monkeypatch.setattr(store.set_status, "__defaults__", (tmp_path / "queue",))
    monkeypatch.setattr(cli, "_brain", lambda cfg: FakeBrain())
    cfg = cli.Config.load()
    cfg.auto_approve = False

    cli.cmd_plan(cfg, None)
    [post] = store.load_posts()
    assert post["status"] == "draft"
    assert post["media_files"] == [f"media/{post['id']}/post.jpg"]
    assert (tmp_path / post["media_files"][0]).exists()
    preview = next((tmp_path / "reports").glob("preview-*.md")).read_text()
    assert f"../media/{post['id']}/post.jpg" in preview and "EV next?" in preview

    cli.cmd_approve_all(cfg, None)
    assert store.load_posts()[0]["status"] == "approved"
