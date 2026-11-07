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
    ("Fri", "18:00", "reel"),  # Instagram insights: followers peak 6-9 PM Fri-Sun
    ("Sat", "18:00", "reel"),
    ("Sun", "18:00", "reel"),
]
INSTAGRAM_REEL_DAYS = ("Fri", "Sat", "Sun")


def youtube_only(post_format: str, day: str) -> bool:
    """Mon-Thu reels skip Instagram; the owner keeps Instagram reels for Fri-Sun."""
    return post_format == "reel" and day not in INSTAGRAM_REEL_DAYS


# When each day's reel goes public on YouTube: the schedule YouTube started on
# (22 Oct 2026), which the owner keeps fixed. Instagram keeps its own times
# above; on Fri-Sun the Short is uploaded with the Instagram post and goes
# public at this time, or, when this is earlier (Sunday), is posted on its own.
YOUTUBE_TIMES = {"Tue": "19:30", "Wed": "19:30", "Fri": "19:30", "Sat": "19:30", "Sun": "10:30"}
