"""Settings, read from environment variables (or a local .env file)."""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass
class Config:
    ig_access_token: str
    ig_user_id: str
    ig_api_version: str
    timezone: str
    niche: str
    posts_per_week: int
    model: str
    github_repository: str
    handle: str
    auto_approve: bool
    yt_client_id: str = ""
    yt_client_secret: str = ""
    yt_refresh_token: str = ""

    @classmethod
    def load(cls) -> "Config":
        _load_dotenv()
        return cls(
            ig_access_token=os.environ.get("IG_ACCESS_TOKEN", ""),
            ig_user_id=os.environ.get("IG_USER_ID", ""),
            ig_api_version=os.environ.get("IG_API_VERSION", "v23.0"),
            timezone=os.environ.get("TIMEZONE", "Asia/Kolkata"),
            niche=os.environ.get(
                "NICHE",
                "Car tech explained simply: EVs, ADAS, infotainment, and which "
                "cars give the best tech for the money, mainly for Indian buyers",
            ),
            posts_per_week=int(os.environ.get("POSTS_PER_WEEK", "5")),
            model=os.environ.get("CLAUDE_MODEL", "claude-opus-5-5"),
            github_repository=os.environ.get("GITHUB_REPOSITORY", ""),
            handle=os.environ.get("HANDLE") or "@decodethedrive",
            auto_approve=os.environ.get("AUTO_APPROVE", "").lower() in ("1", "true", "yes"),
            yt_client_id=os.environ.get("YT_CLIENT_ID", ""),
            yt_client_secret=os.environ.get("YT_CLIENT_SECRET", ""),
            yt_refresh_token=os.environ.get("YT_REFRESH_TOKEN", ""),
        )
