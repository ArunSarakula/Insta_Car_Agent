"""The fixed weekly posting slots (IST) the owner asked for: YouTube gets a
reel every weekday evening, Instagram gets carousels on weekdays and reels
and memes only at the weekend."""

POST_SLOTS = [
    ("Mon", "20:00", "carousel"),
    ("Tue", "19:30", "reel"),
    ("Wed", "19:30", "reel"),
    ("Thu", "20:00", "carousel"),
    ("Fri", "19:30", "reel"),
    ("Sat", "11:00", "reel"),
    ("Sat", "20:30", "meme"),
    ("Sun", "11:30", "reel"),
    ("Sun", "20:30", "meme"),
]
WEEKEND = ("Sat", "Sun")


def youtube_only(post_format: str, day: str) -> bool:
    """Weekday reels skip Instagram; the owner keeps Instagram reels for the weekend."""
    return post_format == "reel" and day not in WEEKEND
