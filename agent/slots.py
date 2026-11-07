"""The fixed weekly posting slots (IST) the owner asked for: YouTube gets a
reel five evenings a week, Instagram gets reels only Fri-Sun and carousels and
memes on weekdays."""

# Reels go out Mon, Thu, Fri, Sat and Sun (owner's choice, Nov 2026). Mon and
# Thu reels are YouTube only, at the YouTube time. Fri-Sun reels hit Instagram
# at 18:00 and go public on YouTube later, at YOUTUBE_REEL_TIME.
YOUTUBE_REEL_TIME = "21:00"  # trial from 7 Nov 2026: 18:00 Shorts were getting few views

POST_SLOTS = [
    ("Mon", "20:00", "carousel"),
    ("Mon", YOUTUBE_REEL_TIME, "reel"),
    ("Tue", "13:00", "meme"),
    ("Thu", "13:00", "meme"),
    ("Thu", "20:00", "carousel"),
    ("Thu", YOUTUBE_REEL_TIME, "reel"),
    ("Fri", "18:00", "reel"),  # Instagram insights: followers peak 6-9 PM Fri-Sun
    ("Sat", "18:00", "reel"),
    ("Sun", "18:00", "reel"),
]
INSTAGRAM_REEL_DAYS = ("Fri", "Sat", "Sun")


def youtube_only(post_format: str, day: str) -> bool:
    """Mon-Thu reels skip Instagram; the owner keeps Instagram reels for Fri-Sun."""
    return post_format == "reel" and day not in INSTAGRAM_REEL_DAYS
