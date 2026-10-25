"""Command line for the agent.

    python -m agent plan            draft next week's posts and design their media
    python -m agent list            show the queue
    python -m agent approve ID      approve a post so it can be published
    python -m agent approve-all     approve every draft that has media
    python -m agent reject ID       drop a post
    python -m agent publish-due     publish approved posts whose time has come
    python -m agent comments        draft replies to new comments
    python -m agent send-replies    post the replies you approved
    python -m agent report          write this week's growth report
    python -m agent youtube-check   test the YouTube connection (no upload)
    python -m agent x-check         test the X (Twitter) connection (no post)
    python -m agent voice-test ID   render a reel in both AI voices to compare
    python -m agent revoice         add the AI voice to every queued reel
    python -m agent voice-samples   save a short sample of every Indian English voice
    python -m agent voice-usage     this month's AI voice characters and cost
"""

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import store
from .config import ROOT, Config
from .slots import youtube_only

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def next_occurrence(day: str, hhmm: str, today: date, tz: ZoneInfo) -> datetime:
    """The first `day` strictly after `today`, at `hhmm` local time."""
    ahead = (DAYS.index(day) - today.weekday()) % 7 or 7
    hour, minute = (int(x) for x in hhmm.split(":"))
    d = today + timedelta(days=ahead)
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=tz)


def media_urls(post: dict, github_repository: str) -> list[str]:
    """Public URLs for a post's media. Instagram downloads media from a URL,
    so either put full URLs in media_urls, or put files in media/ of a public
    repo and list them in media_files."""
    if post.get("media_urls"):
        return post["media_urls"]
    files = post.get("media_files") or []
    if files and github_repository:
        return [f"https://raw.githubusercontent.com/{github_repository}/main/{f}" for f in files]
    return []


def _brain(cfg: Config):
    from .brain import Brain
    return Brain(cfg.niche, cfg.model)


def _instagram(cfg: Config):
    from .instagram import Instagram
    return Instagram(cfg.ig_access_token, cfg.ig_user_id, cfg.ig_api_version)


def audience_questions() -> list[str]:
    """Car questions Indian buyers search on Google and YouTube."""
    path = ROOT / "ideas" / "questions.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [q for group in data["questions"].values() for q in group]


def latest_report() -> str:
    """The newest weekly report, so the plan learns from what worked."""
    reports = sorted((ROOT / "reports").glob("report-*.md"))
    return reports[-1].read_text()[:4000] if reports else ""


def cmd_plan(cfg: Config, args) -> None:
    from .design import render_post

    tz = ZoneInfo(cfg.timezone)
    today = datetime.now(tz).date()
    posts = store.load_posts()
    # Start after the last post already scheduled, so weeks don't overlap.
    start = max([today] + [date.fromisoformat(p["scheduled_for"][:10]) for p in posts
                           if p.get("scheduled_for") and p["status"] in ("draft", "approved")])
    if (start - today).days > 7:
        # Next week is already planned (a late cron run after a manual one).
        print(f"Already planned up to {start}; skipping.")
        return
    ideas = store.load_ideas()
    plan = _brain(cfg).weekly_plan(cfg.posts_per_week, posts, latest_report(),
                                   ideas=[i for i in ideas if i["status"] == "new"],
                                   questions=audience_questions())
    used = set()
    status = "approved" if cfg.auto_approve else "draft"
    saved_posts = []
    for post in plan["posts"]:
        day = post.pop("day")
        post["scheduled_for"] = next_occurrence(day, post.pop("time"), start, tz).isoformat()
        if youtube_only(post["format"], day):
            post["youtube_only"] = True
        used.add(post.get("idea_id", ""))
        post = store.save_post({**post, "status": status})
        post["media_files"] = render_post(post, ROOT / "media", cfg.handle, cfg.tts_api_key, cfg.voice)
        store.save_post(post)
        saved_posts.append(post)
        print(f"  {status} {post['id']}  {post['scheduled_for'][:16]}  [{post['format']}] {post['title']}")

    for idea in ideas:
        if idea["id"] in used:
            idea["status"] = "used"
    if used & {i["id"] for i in ideas}:
        store.save_ideas(ideas)

    out = ROOT / "reports" / f"preview-{today}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(preview(plan, saved_posts, today))
    print(f"Planned {len(saved_posts)} posts. Preview: {out.relative_to(ROOT)}")
    if status == "draft":
        print("Check the preview, then run approve-all (or approve ID).")


def preview(plan: dict, posts: list[dict], today: date) -> str:
    """A page that shows the whole week, images included, when opened on GitHub."""
    lines = [f"# Week of {today}: {plan['theme']}", "",
             "Check the posts below. If they look good, run **approve-all** from the Actions tab.", ""]
    for p in posts:
        lines += [f"## {p['scheduled_for'][:16].replace('T', ' ')} · {p['format']} · {p['title']}",
                  f"Post id: `{p['id']}`", ""]
        for f in p["media_files"]:
            if f.endswith(".mp4"):
                cover = f.rsplit("/", 1)[0] + "/cover.jpg"
                lines.append(f'<a href="../{f}"><img src="../{cover}" width="220"></a> (tap for the video)')
            else:
                lines.append(f'<img src="../{f}" width="220">')
        if p.get("music_track"):
            lines += ["", f"Music: {p['music_track']} ({p.get('music')})"]
        if p["format"] == "reel":
            lines += ["", f"YouTube Shorts title: **{youtube_title(p)}**",
                      f"YouTube hashtags: {' '.join(youtube_hashtags(p))}"]
        lines += ["", "**Caption:**", "", p["caption"], "", " ".join(p.get("hashtags", [])[:INSTAGRAM_HASHTAGS]), ""]
    lines += ["## Story polls (post these yourself)", ""]
    for poll in plan["story_polls"]:
        lines.append(f"- **{poll['day']}**: {poll['question']}  ({poll['option_a']} / {poll['option_b']})")
    return "\n".join(lines) + "\n"


def cmd_list(cfg: Config, args) -> None:
    posts = store.load_posts()
    if not posts:
        print("Queue is empty. Run: python -m agent plan")
    for p in posts:
        has_media = "media ok" if media_urls(p, cfg.github_repository) else "NEEDS MEDIA"
        print(f"{p['id']}  {p['status']:<9} {p.get('scheduled_for', '')[:16]}  "
              f"[{p['format']}] {p['title']}  ({has_media})")


def cmd_approve(cfg: Config, args) -> None:
    post = store.set_status(args.id, "approved")
    print(f"Approved {post['id']}: {post['title']}")


def cmd_approve_all(cfg: Config, args) -> None:
    count = 0
    for post in store.load_posts():
        if post["status"] == "draft" and (post.get("media_files") or post.get("media_urls")):
            store.set_status(post["id"], "approved")
            print(f"Approved {post['id']}: {post['title']}")
            count += 1
    print(f"Approved {count} posts." if count else "No drafts with media to approve.")


def cmd_reject(cfg: Config, args) -> None:
    post = store.set_status(args.id, "rejected")
    print(f"Rejected {post['id']}: {post['title']}")


INSTAGRAM_HASHTAGS = 5  # Instagram's per-post limit


def caption_for(post: dict) -> str:
    tags = " ".join(post.get("hashtags", [])[:INSTAGRAM_HASHTAGS])
    return f"{post['caption']}\n.\n.\n{tags}".strip()


def video_urls(post: dict, urls: list[str], github_repository: str) -> list[str]:
    """Where Instagram can fetch a reel from. Instagram Login accounts can't
    upload video directly, so it is fetched by URL: jsDelivr first (serves
    it as video/mp4), then GitHub raw as a fallback."""
    if post.get("media_urls") or not github_repository:
        return urls[:1]
    ref = os.environ.get("GITHUB_SHA") or "main"
    return [f"https://cdn.jsdelivr.net/gh/{github_repository}@{ref}/{post['media_files'][0]}", urls[0]]


def publish_reel(ig, post: dict, urls: list[str], github_repository: str) -> str:
    cover = urls[0].rsplit("/", 1)[0] + "/cover.jpg" if not post.get("media_urls") else ""
    error = None
    for url in video_urls(post, urls, github_repository):
        try:
            return ig.publish_reel(url, caption_for(post), cover)
        except Exception as e:
            print(f"  reel from {url} failed: {e}")
            error = e
    raise error


def cmd_publish_due(cfg: Config, args) -> None:
    tz = ZoneInfo(cfg.timezone)
    # GitHub's scheduled runs can be hours late, so a run also picks up posts
    # due soon and waits for their exact time instead of hoping the next run
    # comes on time.
    retry_thumbnails(cfg)
    lookahead = int(os.environ.get("PUBLISH_LOOKAHEAD_MIN") or 0)
    due = store.due_posts(datetime.now(tz) + timedelta(minutes=lookahead))
    if not due:
        print("Nothing due.")
        return
    ig = _instagram(cfg)
    for post in due:
        wait = (datetime.fromisoformat(post["scheduled_for"]) - datetime.now(tz)).total_seconds()
        if wait > 0:
            print(f"Waiting {wait / 60:.0f} min to post {post['id']} at {post['scheduled_for'][11:16]}")
            time.sleep(wait)
        now = datetime.now(tz)
        if post.get("youtube_only"):  # e.g. a carousel already on Instagram, remade as a Short
            if not cfg.yt_refresh_token:
                print(f"Skipping {post['id']} ({post['title']}): YouTube is not connected.")
                continue
            store.set_status(post["id"], "published", published_at=now.isoformat())
            print(f"Published {post['id']} to YouTube only: {post['title']}")
            upload_to_youtube(cfg, post)
            post_to_x(cfg, post)
            continue
        urls = media_urls(post, cfg.github_repository)
        if not urls:
            print(f"Skipping {post['id']} ({post['title']}): no media attached yet.")
            continue
        try:
            if post["format"] == "reel":
                media_id = publish_reel(ig, post, urls, cfg.github_repository)
            elif post["format"] == "carousel":
                media_id = ig.publish_carousel(urls, caption_for(post))
            else:
                media_id = ig.publish_image(urls[0], caption_for(post))
        except Exception as e:  # keep going with the other posts
            store.set_status(post["id"], "failed", error=str(e))
            print(f"FAILED {post['id']}: {e}")
            continue
        store.set_status(post["id"], "published", media_id=media_id,
                         published_at=now.isoformat())
        print(f"Published {post['id']}: {post['title']}")
        if post["format"] == "reel" and cfg.yt_refresh_token:
            upload_to_youtube(cfg, post)
        post_to_x(cfg, post)



def retry_thumbnails(cfg: Config) -> None:
    """Set thumbnails YouTube refused earlier, e.g. before the channel was
    phone-verified. Runs on every publish check; one try per post per run."""
    pending = [p for p in store.load_posts() if p.get("youtube_id") and p.get("thumbnail_error")]
    if not pending or not cfg.yt_refresh_token:
        return
    from .youtube import YouTube
    yt = YouTube(cfg.yt_client_id, cfg.yt_client_secret, cfg.yt_refresh_token)
    for post in pending:
        folder = (ROOT / post["media_files"][0]).parent
        image = folder / "thumbnail.jpg" if (folder / "thumbnail.jpg").exists() else folder / "cover.jpg"
        if not image.exists():
            continue
        try:
            yt.set_thumbnail(post["youtube_id"], str(image))
        except Exception as e:
            store.set_status(post["id"], post["status"], thumbnail_error=str(e))
            print(f"  Thumbnail still not set for {post['id']}: {e}")
            continue
        post.pop("thumbnail_error", None)
        store.save_post(post)
        print(f"  Thumbnail set for {post['id']} (https://youtube.com/shorts/{post['youtube_id']})")

def youtube_title(post: dict) -> str:
    # No hashtags in the title: YouTube then shows the description's
    # first 3 hashtags above it instead. Vertical videos under 3 minutes
    # become Shorts on their own.
    return (post.get("youtube_title") or post.get("hook") or post["title"])[:100]


def youtube_hashtags(post: dict) -> list[str]:
    """#shorts plus 2 topic tags. Instagram gets 8-15 tags, YouTube only
    shows 3 and treats long tag lists as spam."""
    topic = post.get("youtube_hashtags") or post.get("hashtags", [])
    tags = ["#shorts"] + [t for t in topic if t.lower() != "#shorts"]
    return tags[:3]


def youtube_description(post: dict) -> str:
    """Search is our biggest YouTube source, so the description opens with the
    searched question and the slide points, which carry the key terms."""
    points = "\n".join(f"- {s['heading']}" for s in post.get("slides", [])[1:]
                       if "@decodethedrive" not in s["heading"])
    head = youtube_title(post) + (f"\n\nIn this Short:\n{points}" if points else "")
    return (f"{head}\n\n{post['caption']}\n\nMore car tech on Instagram: https://instagram.com/decodethedrive"
            f"\n\n{' '.join(youtube_hashtags(post))}").strip()[:4900]


def upload_to_youtube(cfg: Config, post: dict) -> None:
    """Same reel as a YouTube Short. A failure here never undoes the
    Instagram post; it is recorded on the post instead."""
    from .youtube import YouTube
    try:
        yt = YouTube(cfg.yt_client_id, cfg.yt_client_secret, cfg.yt_refresh_token)
        video_id = yt.upload_short(str(ROOT / post["media_files"][0]), youtube_title(post),
                                   youtube_description(post),
                                   [t.lstrip("#") for t in post.get("hashtags", [])])
        store.set_status(post["id"], "published", youtube_id=video_id)
        print(f"  Also on YouTube: https://youtube.com/shorts/{video_id}")
        folder = (ROOT / post["media_files"][0]).parent
        cover = folder / "thumbnail.jpg" if (folder / "thumbnail.jpg").exists() else folder / "cover.jpg"
        if cover.exists():
            try:
                yt.set_thumbnail(video_id, str(cover))
            except Exception as e:  # the Short is up either way
                store.set_status(post["id"], "published", thumbnail_error=str(e))
                print(f"  Thumbnail not set: {e}")
    except Exception as e:
        store.set_status(post["id"], "published", youtube_error=str(e))
        print(f"  YouTube upload failed: {e}")


X_FORMATS = ("reel", "meme")
X_HASHTAGS = 2


def x_text(post: dict) -> str:
    """The searched question plus two hashtags, inside X's 280 characters."""
    tags = " ".join(post.get("hashtags", [])[:X_HASHTAGS])
    room = 270 - len(tags) - 2
    head = post.get("hook") or post["title"]
    if post["format"] == "meme":
        head = post["caption"].split("\n")[0]
    if len(head) > room:
        head = head[:room - 1].rstrip() + "…"
    return f"{head}\n\n{tags}".strip()


def post_to_x(cfg: Config, post: dict) -> None:
    """Same reel or meme on X. A failure here never undoes the other posts;
    it is recorded on the post instead."""
    if not cfg.x_connected or post["format"] not in X_FORMATS or not post.get("media_files"):
        return
    from .x import X
    try:
        x = X(cfg.x_api_key, cfg.x_api_secret, cfg.x_access_token, cfg.x_access_secret)
        tweet_id = x.post(x_text(post), str(ROOT / post["media_files"][0]))
        store.set_status(post["id"], "published", x_id=tweet_id)
        print(f"  Also on X: https://x.com/i/status/{tweet_id}")
    except Exception as e:
        store.set_status(post["id"], "published", x_error=str(e))
        print(f"  X post failed: {e}")


def _voiced_reel(cfg: Config, post: dict, voice: str) -> Path:
    """Renders the post's reel with the AI voice in a scratch folder."""
    import tempfile
    from .design import render_post
    if not cfg.tts_api_key:
        raise KeyError("TTS_API_KEY is not set, so there is no voice to add.")
    out = Path(tempfile.mkdtemp())
    trial = {**post, "id": "reel"}
    render_post(trial, out, cfg.handle, cfg.tts_api_key, voice)
    if not trial.get("voiced"):
        raise KeyError(f"The voice could not be made for {post['id']}; see the log above.")
    return out / "reel" / "reel.mp4"


def cmd_voice_test(cfg: Config, args) -> None:
    """The same reel in several voices, saved under media/voice-test/ to
    compare: TEST_VOICES (comma-separated names, e.g. Charon,Kore), or a male
    and a female voice."""
    post = store.get_post(args.id)
    suffix = ""
    if os.environ.get("TEST_NO_TEXT", "").lower() == "true":  # voice and animation only
        post, suffix = {**post, "hide_text": True}, "-notext"
    if os.environ.get("TEST_LAYOUT"):  # e.g. big3d: the 3D part with short captions
        post, suffix = {**post, "layout": os.environ["TEST_LAYOUT"]}, suffix + "-" + os.environ["TEST_LAYOUT"]
    names = [v.strip() for v in os.environ.get("TEST_VOICES", "").split(",") if v.strip()] or ["male", "female"]
    for voice in names:
        if voice not in ("male", "female") and not voice.startswith("en-IN-"):
            voice = f"en-IN-Chirp3-HD-{voice}"
        target = ROOT / "media" / "voice-test" / f"{post['id']}-{voice.split('-')[-1].lower()}{suffix}.mp4"
        target.parent.mkdir(parents=True, exist_ok=True)
        _voiced_reel(cfg, post, voice).replace(target)
        print(f"  {voice}: {target.relative_to(ROOT)}")


def cmd_voice_samples(cfg: Config, args) -> None:
    """One spoken line in every Indian English Google voice, under
    media/voice-test/samples/, with a list of names and genders."""
    from .voice import list_voices, synthesize
    if not cfg.tts_api_key:
        raise KeyError("TTS_API_KEY is not set, so there is no voice to sample.")
    text = ("Are you using your clutch wrong? If your foot rests on the pedal, "
            "even light pressure slips it and wears the plate.")
    folder = ROOT / "media" / "voice-test" / "samples"
    made = []
    for v in list_voices(cfg.tts_api_key):
        try:
            synthesize(text, folder / f"{v['name']}.mp3", cfg.tts_api_key, voice=v["name"])
        except RuntimeError as e:
            print(f"  skipped {v['name']}: {e}")
            continue
        made.append(v)
        print(f"  {v['gender']:7} {v['name']}")
    (folder / "voices.json").write_text(json.dumps(made, indent=2) + "\n")


def cmd_voice_usage(cfg: Config, args) -> None:
    from .voice import USAGE_FILE, usage_summary
    print(usage_summary(USAGE_FILE))


def cmd_revoice(cfg: Config, args) -> None:
    """Gives queued reels the current voice (VOICE) if they don't have it. Only the video
    is replaced; thumbnails and covers chosen by hand stay as they are."""
    for post in store.load_posts():
        if post["status"] not in ("draft", "approved") or post["format"] != "reel" or post.get("voice") == cfg.voice:
            continue
        if not post.get("media_files"):
            continue
        try:
            _voiced_reel(cfg, post, cfg.voice).replace(ROOT / post["media_files"][0])
        except KeyError as e:
            print(f"  skipped {post['id']}: {e}")
            continue
        store.set_status(post["id"], post["status"], voiced=True, voice=cfg.voice)
        print(f"  voiced {post['id']}: {post['title']}")


def cmd_x_check(cfg: Config, args) -> None:
    """Checks the X keys work, without posting anything."""
    from .x import X
    me = X(cfg.x_api_key, cfg.x_api_secret, cfg.x_access_token, cfg.x_access_secret).me()
    print(f"X connection OK as @{me['username']}: reels and memes will be posted there too.")


def cmd_youtube_check(cfg: Config, args) -> None:
    """Checks the YouTube sign-in works, without uploading anything."""
    from .youtube import YouTube
    YouTube(cfg.yt_client_id, cfg.yt_client_secret, cfg.yt_refresh_token)._token()
    print("YouTube connection OK: reels will be uploaded as Shorts.")


def cmd_comments(cfg: Config, args) -> None:
    ig = _instagram(cfg)
    me = ig.profile()["username"]
    pending = store.load_replies()
    known = {r["comment_id"] for r in pending}
    new = []
    for media in ig.recent_media(limit=10):
        for c in ig.comments(media["id"]):
            replied = any(r.get("username") == me for r in c.get("replies", {}).get("data", []))
            if c["id"] in known or replied or c.get("username") == me:
                continue
            c["post_caption"] = media.get("caption", "")
            new.append(c)
    by_id = {c["id"]: c for c in new}
    for draft in _brain(cfg).draft_replies(new):
        c = by_id.get(draft["comment_id"])
        if not c:
            continue
        pending.append({"comment_id": c["id"], "username": c.get("username"),
                        "comment": c["text"], "reply": draft["reply"],
                        "flag": draft["flag"], "status": "draft"})
    store.save_replies(pending)
    print(f"Drafted replies for {len(new)} new comments in replies/pending.json.")
    print('Edit any reply you like, set "status": "approved", then run send-replies.')


def cmd_send_replies(cfg: Config, args) -> None:
    pending = store.load_replies()
    approved = [r for r in pending if r["status"] == "approved" and r["reply"]]
    if not approved:
        print("No approved replies to send.")
        return
    ig = _instagram(cfg)
    for r in approved:
        try:
            ig.reply_to_comment(r["comment_id"], r["reply"])
            r["status"] = "sent"
            print(f"Replied to @{r['username']}")
        except Exception as e:
            r["status"] = "failed"
            r["error"] = str(e)
            print(f"FAILED reply to @{r['username']}: {e}")
    store.save_replies(pending)


def cmd_report(cfg: Config, args) -> None:
    ig = _instagram(cfg)
    profile = ig.profile()
    online = ig.online_followers_ist()
    if online:
        profile["followers_online_by_ist_hour"] = online
    by_media = {p["media_id"]: p for p in store.load_posts() if p.get("media_id")}
    posts = []
    for media in ig.recent_media(limit=10):
        try:
            media["insights"] = ig.media_insights(media["id"])
        except Exception:
            media["insights"] = {}
        ours = by_media.get(media["id"])
        if ours:  # what each post tested, so the report can compare hook types
            media["hook_type"] = ours.get("hook_type", "")
            media["hook"] = ours.get("hook", "")
        posts.append(media)
    report = _brain(cfg).weekly_report(profile, posts)
    today = datetime.now(ZoneInfo(cfg.timezone)).date()
    out = ROOT / "reports" / f"report-{today}.md"
    out.parent.mkdir(exist_ok=True)
    from .voice import USAGE_FILE, usage_summary
    report += "\n\n" + usage_summary(USAGE_FILE)
    out.write_text(report + "\n")
    print(report)


COMMANDS = {
    "plan": cmd_plan, "list": cmd_list, "approve": cmd_approve, "approve-all": cmd_approve_all, "reject": cmd_reject,
    "publish-due": cmd_publish_due, "comments": cmd_comments,
    "send-replies": cmd_send_replies, "report": cmd_report, "youtube-check": cmd_youtube_check,
    "x-check": cmd_x_check, "voice-test": cmd_voice_test, "revoice": cmd_revoice,
    "voice-samples": cmd_voice_samples, "voice-usage": cmd_voice_usage,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        p = sub.add_parser(name)
        if name in ("approve", "reject", "voice-test"):
            p.add_argument("id")
    args = parser.parse_args(argv)
    cfg = Config.load()
    from . import voice
    voice.USAGE_FILE = ROOT / "reports" / "tts-usage.json"
    try:
        COMMANDS[args.command](cfg, args)
    except KeyError as e:
        print(e, file=sys.stderr)
        return 1
    return 0
