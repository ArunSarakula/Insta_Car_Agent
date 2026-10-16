"""Command line for the agent.

    python -m agent plan            draft next week's posts (status: draft)
    python -m agent list            show the queue
    python -m agent approve ID      approve a post so it can be published
    python -m agent reject ID       drop a post
    python -m agent publish-due     publish approved posts whose time has come
    python -m agent comments        draft replies to new comments
    python -m agent send-replies    post the replies you approved
    python -m agent report          write this week's growth report
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import store
from .config import ROOT, Config

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


def cmd_plan(cfg: Config, args) -> None:
    tz = ZoneInfo(cfg.timezone)
    today = datetime.now(tz).date()
    plan = _brain(cfg).weekly_plan(cfg.posts_per_week, store.load_posts())
    for post in plan["posts"]:
        post["scheduled_for"] = next_occurrence(post.pop("day"), post.pop("time"), today, tz).isoformat()
        post["media_files"] = []
        saved = store.save_post(post)
        print(f"  draft {saved['id']}  {saved['scheduled_for'][:16]}  [{saved['format']}] {saved['title']}")

    polls = [f"# Story polls, week of {today}\n", f"Theme: {plan['theme']}\n"]
    for p in plan["story_polls"]:
        polls.append(f"- **{p['day']}**: {p['question']}  ({p['option_a']} / {p['option_b']})")
    out = ROOT / "reports" / f"polls-{today}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(polls) + "\n")
    print(f"Planned {len(plan['posts'])} posts. Story polls in {out.relative_to(ROOT)}.")
    print("Review the files in queue/, add media, then set status to approved.")


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


def cmd_reject(cfg: Config, args) -> None:
    post = store.set_status(args.id, "rejected")
    print(f"Rejected {post['id']}: {post['title']}")


def caption_for(post: dict) -> str:
    tags = " ".join(post.get("hashtags", []))
    return f"{post['caption']}\n.\n.\n{tags}".strip()


def cmd_publish_due(cfg: Config, args) -> None:
    now = datetime.now(ZoneInfo(cfg.timezone))
    due = store.due_posts(now)
    if not due:
        print("Nothing due.")
        return
    ig = _instagram(cfg)
    for post in due:
        urls = media_urls(post, cfg.github_repository)
        if not urls:
            print(f"Skipping {post['id']} ({post['title']}): no media attached yet.")
            continue
        try:
            if post["format"] == "reel":
                media_id = ig.publish_reel(urls[0], caption_for(post))
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
    posts = []
    for media in ig.recent_media(limit=10):
        try:
            media["insights"] = ig.media_insights(media["id"])
        except Exception:
            media["insights"] = {}
        posts.append(media)
    report = _brain(cfg).weekly_report(profile, posts)
    today = datetime.now(ZoneInfo(cfg.timezone)).date()
    out = ROOT / "reports" / f"report-{today}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(report + "\n")
    print(report)


COMMANDS = {
    "plan": cmd_plan, "list": cmd_list, "approve": cmd_approve, "reject": cmd_reject,
    "publish-due": cmd_publish_due, "comments": cmd_comments,
    "send-replies": cmd_send_replies, "report": cmd_report,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        p = sub.add_parser(name)
        if name in ("approve", "reject"):
            p.add_argument("id")
    args = parser.parse_args(argv)
    cfg = Config.load()
    try:
        COMMANDS[args.command](cfg, args)
    except KeyError as e:
        print(e, file=sys.stderr)
        return 1
    return 0
