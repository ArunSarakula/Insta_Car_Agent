"""The fixed weekly posting slots (IST) the owner asked for: YouTube gets a
reel most evenings, Instagram gets reels only Fri-Sun and carousels and
memes on weekdays."""

POST_SLOTS = [
    ("Mon", "20:00", "carousel"),
    ("Tue", "13:00", "meme"),
    ("Tue", "19:30", "reel"),
    ("Wed", "19:30", "reel"),
    ("Thu", "13:00", "meme"),
    ("Thu", "20:00", "carousel"),
    ("Fri", "19:30", "reel"),
    ("Sat", "19:30", "reel"),
    ("Sun", "10:30", "reel"),
]
INSTAGRAM_REEL_DAYS = ("Fri", "Sat", "Sun")


def youtube_only(post_format: str, day: str) -> bool:
    """Mon-Thu reels skip Instagram; the owner keeps Instagram reels for Fri-Sun."""
    return post_format == "reel" and day not in INSTAGRAM_REEL_DAYS
