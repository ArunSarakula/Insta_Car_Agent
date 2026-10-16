"""Post queue and reply drafts, kept as JSON files in the repo so you can
review and approve them right on GitHub.

Every post goes through: draft -> approved -> published (or failed).
Nothing is published unless its status is "approved".
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from .config import ROOT

QUEUE_DIR = ROOT / "queue"
REPLIES_FILE = ROOT / "replies" / "pending.json"

STATUSES = ("draft", "approved", "published", "failed", "rejected")


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# ---- posts -----------------------------------------------------------------

def save_post(post: dict, queue_dir: Path = QUEUE_DIR) -> dict:
    post.setdefault("id", uuid.uuid4().hex[:8])
    post.setdefault("status", "draft")
    _write(queue_dir / f"{post['id']}.json", post)
    return post


def load_posts(queue_dir: Path = QUEUE_DIR) -> list[dict]:
    if not queue_dir.exists():
        return []
    posts = [json.loads(p.read_text()) for p in sorted(queue_dir.glob("*.json"))]
    return sorted(posts, key=lambda p: p.get("scheduled_for", ""))


def get_post(post_id: str, queue_dir: Path = QUEUE_DIR) -> dict:
    path = queue_dir / f"{post_id}.json"
    if not path.exists():
        raise KeyError(f"No post with id {post_id}")
    return json.loads(path.read_text())


def set_status(post_id: str, status: str, queue_dir: Path = QUEUE_DIR, **extra) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    post = get_post(post_id, queue_dir)
    post["status"] = status
    post.update(extra)
    return save_post(post, queue_dir)


def due_posts(now: datetime, queue_dir: Path = QUEUE_DIR) -> list[dict]:
    """Approved posts whose scheduled time has passed."""
    due = []
    for post in load_posts(queue_dir):
        if post.get("status") != "approved" or not post.get("scheduled_for"):
            continue
        if datetime.fromisoformat(post["scheduled_for"]) <= now:
            due.append(post)
    return due


# ---- comment replies -------------------------------------------------------

def load_replies(path: Path = REPLIES_FILE) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text())


def save_replies(replies: list[dict], path: Path = REPLIES_FILE) -> None:
    _write(path, replies)
