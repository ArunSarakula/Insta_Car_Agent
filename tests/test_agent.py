import json
import subprocess
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


def test_reel_tries_jsdelivr_then_raw(monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "abc123")
    post = {"id": "r1", "caption": "c", "media_files": ["media/r1/reel.mp4"]}
    urls = cli.media_urls(post, "me/repo")
    assert cli.video_urls(post, urls, "me/repo") == [
        "https://cdn.jsdelivr.net/gh/me/repo@abc123/media/r1/reel.mp4", urls[0]]

    tried = []

    class IG:
        def publish_reel(self, url, caption, cover):
            tried.append(url)
            if "jsdelivr" in url:
                raise InstagramError("Media container is ERROR")
            return "m1"

    assert cli.publish_reel(IG(), post, urls, "me/repo") == "m1"
    assert len(tried) == 2


def test_publish_due_waits_for_posts_due_soon(tmp_path, monkeypatch):
    tz = ZoneInfo("Asia/Kolkata")
    soon = (datetime.now(tz) + timedelta(minutes=90)).isoformat()
    later = (datetime.now(tz) + timedelta(hours=6)).isoformat()
    store.save_post({"id": "s", "status": "approved", "scheduled_for": soon, "format": "image", "title": "t",
                     "caption": "c", "media_urls": ["https://x/s.jpg"]}, tmp_path)
    store.save_post({"id": "l", "status": "approved", "scheduled_for": later, "format": "image", "title": "t",
                     "caption": "c", "media_urls": ["https://x/l.jpg"]}, tmp_path)
    for fn in (store.load_posts, store.set_status, store.get_post, store.save_post, store.due_posts):
        monkeypatch.setattr(fn, "__defaults__", (tmp_path,))
    slept, posted = [], []
    monkeypatch.setattr(cli.time, "sleep", slept.append)
    monkeypatch.setattr(cli, "_instagram", lambda cfg: SimpleNamespace(
        publish_image=lambda url, caption: posted.append(url) or "m"))
    monkeypatch.setenv("PUBLISH_LOOKAHEAD_MIN", "240")
    cli.cmd_publish_due(cli.Config.load(), None)
    assert posted == ["https://x/s.jpg"]
    assert 85 * 60 < slept[0] <= 90 * 60


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


def test_online_followers_converted_to_ist():
    http = FakeHTTP({("GET", "42/insights"): {"data": [{"values": [
        {"value": {"6": 10, "7": 30}}]}]}})
    hours = Instagram("tok", "42", session=http).online_followers_ist()
    assert sum(hours.values()) == 40 and len(hours) == 2
    assert set(hours) <= {18, 19, 20, 21}  # Pacific morning is Indian evening


def test_online_followers_empty_when_not_available():
    http = FakeHTTP({("GET", "42/insights"): {"error": {"message": "Not enough followers"}}})
    assert Instagram("tok", "42", session=http).online_followers_ist() == {}


def test_missing_token_is_a_clear_error():
    with pytest.raises(InstagramError, match="IG_ACCESS_TOKEN"):
        Instagram("")


class FakeGoogle:
    def __init__(self):
        self.calls = []

    def post(self, url, data, timeout, headers=None):
        self.calls.append(("POST", url, headers))
        if "oauth2" in url:
            return SimpleNamespace(status_code=200, json=lambda: {"access_token": "at"}, text="")
        return SimpleNamespace(status_code=200, headers={"Location": "https://up/1"}, text="")

    def put(self, url, data, timeout, headers=None):
        self.calls.append(("PUT", url, len(data)))
        return SimpleNamespace(status_code=200, json=lambda: {"id": "yt1"}, text="")


def test_youtube_short_upload(tmp_path):
    from agent.youtube import YouTube
    video = tmp_path / "reel.mp4"
    video.write_bytes(b"12345")
    google = FakeGoogle()
    assert YouTube("id", "secret", "rt", session=google).upload_short(
        str(video), "AC vs DC #shorts", "desc", ["ev"]) == "yt1"
    assert google.calls[1][2]["Authorization"] == "Bearer at"
    assert google.calls[2] == ("PUT", "https://up/1", 5)


def test_youtube_title_and_hashtags():
    post = {"youtube_title": "AC vs DC charging explained", "title": "x", "caption": "Cap",
            "hashtags": ["#EV", "#Charging", "#CarTech", "#IndianCars"]}
    assert cli.youtube_title(post) == "AC vs DC charging explained"
    assert cli.youtube_hashtags(post) == ["#shorts", "#EV", "#Charging"]
    post["youtube_hashtags"] = ["#EVCharging", "#CarTech"]
    assert cli.youtube_description(post).endswith("instagram.com/decodethedrive\n\n#shorts #EVCharging #CarTech")
    post["slides"] = [{"heading": "Hook"}, {"heading": "AC is slow"}, {"heading": "Follow @decodethedrive"}]
    assert cli.youtube_description(post).startswith(
        "AC vs DC charging explained\n\nIn this Short:\n- AC is slow\n\nCap")


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
    Brain("cars", client=fake).weekly_plan(5, [], ideas=[{"id": "i9", "idea": "clutch tip"}])
    assert "- id i9: clutch tip" in fake.kwargs["messages"][0]["content"]


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


from agent import styles

VERSUS = {"id": "v1", "format": "reel", "reel_style": "versus", "versus_left": "CVT", "versus_right": "DCT",
          "slides": [{"heading": "Which automatic should you buy?", "body": ""},
                     {"heading": "City traffic", "body": "Smooth | Can judder"},
                     {"heading": "Highway", "body": "Fine | Quick shifts"}]}
QUIZ = {"id": "q1", "format": "reel", "reel_style": "quiz", "quiz_options": ["Engine hot", "Low tyre", "Brakes"],
        "quiz_answer": 1, "slides": [{"heading": "What does this light mean?", "body": ""},
                                     {"heading": "Low tyre pressure", "body": "Check all four tyres."}]}
MYTH = {"id": "m1", "format": "reel", "reel_style": "myth_fact",
        "slides": [{"heading": "Fast charging kills batteries", "body": "EV myth"},
                   {"heading": "Not really", "body": "The BMS slows charging to protect cells."},
                   {"heading": "Charge to 80% daily", "body": ""}]}


def test_reel_styles_fall_back_to_explainer_when_data_missing():
    assert [styles.usable(p) for p in (VERSUS, QUIZ, MYTH)] == ["versus", "quiz", "myth_fact"]
    assert styles.usable({**VERSUS, "versus_right": ""}) == "explainer"
    assert styles.usable({**QUIZ, "quiz_options": ["a", "b"]}) == "explainer"
    assert styles.usable({"slides": SLIDES}) == "explainer"


@pytest.mark.parametrize("post", [VERSUS, QUIZ, MYTH], ids=["versus", "quiz", "myth_fact"])
def test_each_reel_style_renders(tmp_path, post):
    design.render_post(dict(post), tmp_path / "media")
    assert (tmp_path / f"media/{post['id']}/reel.mp4").stat().st_size > 10_000
    assert Image.open(tmp_path / f"media/{post['id']}/cover.jpg").size == (1080, 1920)


def test_voiceover_sets_reel_length(tmp_path, monkeypatch):
    voice = tmp_path / "voice.mp3"
    subprocess.run([design.ffmpeg_exe(), "-loglevel", "error", "-f", "lavfi", "-i",
                    "sine=frequency=300:duration=12", str(voice)], check=True)

    class FakeTTS:
        def post(self, url, params, timeout, json):
            import base64
            assert params == {"key": "k"} and json["voice"]["languageCode"] == "en-IN"
            return SimpleNamespace(status_code=200, json=lambda: {"audioContent": base64.b64encode(voice.read_bytes())})

    from agent import voice as voice_mod
    real = voice_mod.synthesize
    monkeypatch.setattr(voice_mod, "synthesize", lambda text, path, key: real(text, path, key, FakeTTS()))
    post = {**MYTH, "voiceover": "Here is what most people get wrong."}
    design.render_post(post, tmp_path / "media", tts_key="k")
    assert post["voiced"] and post["reel_style"] == "myth_fact"
    assert 12.5 < design.media_seconds(tmp_path / "media/m1/reel.mp4") < 13.6
    assert not (tmp_path / "media/m1/voice.mp3").exists()


def test_pick_track_uses_mood_folder_and_falls_back(tmp_path):
    for name in ("phonk/a.mp3", "phonk/b.mp3", "chill/c.mp3"):
        (tmp_path / name).parent.mkdir(exist_ok=True)
        (tmp_path / name).write_bytes(b"x")
    assert design.pick_track("phonk", "post1", tmp_path).parent.name == "phonk"
    assert design.pick_track("epic", "post1", tmp_path) is not None  # empty mood: any track
    assert design.pick_track("phonk", "x", tmp_path / "none") is None


def test_reel_gets_music_trimmed_to_length(tmp_path):
    post = {"id": "p4", "format": "reel", "music": "phonk", "slides": SLIDES}
    design.render_post(post, tmp_path / "media")
    assert post["music_track"].endswith(".mp3")
    out = subprocess.run([design.ffmpeg_exe(), "-i", str(tmp_path / "media/p4/reel.mp4"),
                          "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    assert "Audio: aac" in out
    assert float(out.split("mean_volume: ")[1].split(" ")[0]) > -40  # not silent


# ---- plan end to end -------------------------------------------------------

class FakeBrain:
    def weekly_plan(self, n, recent, notes="", ideas=(), questions=()):
        self.ideas = ideas
        return {"theme": "Basics", "story_polls": [
            {"day": "Mon", "question": "EV next?", "option_a": "Yes", "option_b": "No"}],
            "posts": [{"format": "meme", "title": "Reboot", "hook": "h", "caption": "c",
                       "hashtags": ["#cars"], "day": "Fri", "time": "21:00", "idea_id": "i1",
                       "slides": [{"heading": "Screen froze", "body": "Turn it off and on"}]}]}


def test_plan_designs_media_and_approve_all(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(store, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(store.save_post, "__defaults__", (tmp_path / "queue",))
    monkeypatch.setattr(store.load_posts, "__defaults__", (tmp_path / "queue",))
    monkeypatch.setattr(store.get_post, "__defaults__", (tmp_path / "queue",))
    monkeypatch.setattr(store.set_status, "__defaults__", (tmp_path / "queue",))
    ideas_file = tmp_path / "ideas.json"
    monkeypatch.setattr(store.load_ideas, "__defaults__", (ideas_file,))
    monkeypatch.setattr(store.save_ideas, "__defaults__", (ideas_file,))
    store.save_ideas([{"id": "i1", "idea": "clutch tip", "status": "new"},
                      {"id": "i2", "idea": "wheel balancing", "status": "new"}])
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

    assert [i["status"] for i in store.load_ideas()] == ["used", "new"]

    cli.cmd_approve_all(cfg, None)
    assert store.load_posts()[0]["status"] == "approved"

    # The next plan starts after the posts already scheduled.
    cli.cmd_plan(cfg, None)
    first, second = store.load_posts()
    assert date.fromisoformat(second["scheduled_for"][:10]) - \
        date.fromisoformat(first["scheduled_for"][:10]) == timedelta(days=7)

    # A late duplicate run in the same week doesn't plan a third week.
    cli.cmd_plan(cfg, None)
    assert len(store.load_posts()) == 2


def test_hook_builds_word_by_word_and_tags_myths():
    from agent.styles import hook_frames
    frames, durations = hook_frames("Wiping fog with your hand fixes it", "MYTH OR FACT?")
    assert len(frames) == 3 and abs(sum(durations) - 1.45) < 0.01
    assert frames[0].getpixel((5, 5)) == frames[-1].getpixel((5, 5))  # amber background
    assert hook_frames("") == ([], [])


def test_caption_keeps_instagram_hashtag_limit():
    post = {"caption": "c", "hashtags": [f"#t{i}" for i in range(9)]}
    assert cli.caption_for(post).endswith("#t0 #t1 #t2 #t3 #t4")


def test_youtube_only_post_skips_instagram(tmp_path, monkeypatch):
    past = (datetime.now(ZoneInfo("Asia/Kolkata")) - timedelta(minutes=5)).isoformat()
    store.save_post({"id": "y", "status": "approved", "scheduled_for": past, "format": "reel", "title": "t",
                     "caption": "c", "youtube_only": True, "media_files": ["media/y/reel.mp4"]}, tmp_path)
    for fn in (store.load_posts, store.set_status, store.get_post, store.save_post, store.due_posts):
        monkeypatch.setattr(fn, "__defaults__", (tmp_path,))
    uploaded = []
    monkeypatch.setattr(cli, "_instagram", lambda cfg: SimpleNamespace())  # any Instagram call would fail
    monkeypatch.setattr(cli, "upload_to_youtube", lambda cfg, post: uploaded.append(post["id"]))
    cfg = SimpleNamespace(timezone="Asia/Kolkata", yt_refresh_token="rt", github_repository="me/repo")
    cli.cmd_publish_due(cfg, None)
    assert uploaded == ["y"] and store.get_post("y")["status"] == "published"
