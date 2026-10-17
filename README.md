# Insta Car Agent

A personal content agent for a car-tech Instagram account. Every week it:

1. **Plans** next week's posts (reels, carousels, memes) with hooks, captions,
   hashtags and a story poll for every day.
2. **Designs the media itself**: branded text slides for images, memes and
   carousels, and short slide-show videos for reels. No photos or editing needed.
3. **Waits for you to approve** the week (one click). Nothing is posted without
   your OK, unless you turn on auto-approve.
4. **Publishes** approved posts at their scheduled time.
5. **Drafts replies** to new comments, which you approve before they are sent.
6. **Writes a weekly report**: followers, best and worst posts, what to do next.

It uses the official Instagram API (no bots, no password sharing), so it is
safe for your account. Claude writes the content.

Everything runs for free on GitHub Actions. You never need to keep your
computer on.

---

## One-time setup

### 1. Switch Instagram to a Creator account
Instagram app → Settings → *Account type and tools* → *Switch to professional
account* → **Creator**.

### 2. Get an Instagram access token
1. Go to <https://developers.facebook.com>, log in, click **My Apps → Create App**.
2. Choose **Other** → **Business**, give it a name (e.g. "Insta Car Agent").
3. On the app dashboard, add the **Instagram** product, then open
   **API setup with Instagram login**.
4. Under *Generate access tokens*, click **Add account** and log in to your
   Instagram account. Allow all permissions it asks for
   (basic, content publish, manage comments, manage insights).
5. Click **Generate token** and copy it. Keep it secret.

> The token lasts about 60 days. Repeat step 5 to get a new one and update the
> secret below when it expires.

### 3. Get a Claude API key
Create a key at <https://console.anthropic.com> → *API Keys*. Add a few dollars
of credit; a week of planning costs only cents.

### 4. Add both keys to this GitHub repo
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Claude API key |
| `IG_ACCESS_TOKEN` | your Instagram token |

Optional, under the **Variables** tab: `TIMEZONE` (default `Asia/Kolkata`),
`POSTS_PER_WEEK` (default `5`), `HANDLE` (default `@decodethedrive`),
`AUTO_APPROVE` (default `false`).

### 5. Turn on Actions
Repo → **Actions** tab → enable workflows if GitHub asks.

Done. To try it right away: **Actions → Instagram agent → Run workflow →
command: plan**.

---

## Your weekly routine (about 2 minutes)

**Sunday:** the agent plans and designs next week automatically.

1. Open `reports/preview-<date>.md` on GitHub. It shows every post's images,
   caption and hashtags, plus the week's story polls.
2. If it all looks good: **Actions → Instagram agent → Run workflow →
   approve-all**. Done.

To change something first, open the post's file in `queue/`, edit the caption
or hashtags with the ✏️ pencil and commit, then approve. To drop a post, run
**reject** with its post id.

The agent checks every hour and publishes approved posts when their time comes.
The repository must be **public** so Instagram can fetch the images.

Prefer not to approve at all? Add a repository variable `AUTO_APPROVE` =
`true` (Settings → Secrets and variables → Actions → Variables) and posts go
out without waiting.

Want to post your own photo or video instead? Put it in `media/` and list it
in the post's `media_files`, or put a public link in `media_urls`.

**Comments:** every 3 hours the agent drafts replies in
`replies/pending.json`. Edit any reply, set `"status": "approved"`, then run
**Actions → Instagram agent → Run workflow → send-replies**.

Comments flagged `needs_owner` (complaints, business offers) deserve your
personal attention. Comments flagged `spam` get no reply.

**Daily:** post that day's story poll from the preview page (Instagram
does not let apps post story polls, so this one is manual).

**Reel music:** every reel gets a royalty-free track from `assets/music/`,
picked by mood (upbeat, tech, chill, epic, phonk), trimmed to the reel and
faded in and out. To add tracks, download MP3s from pixabay.com/music
(instrumental, 30 seconds or longer) and drop them into the matching folder.

---

## Running it on your own computer (optional)

```bash
pip install -r requirements.txt
cp .env.example .env      # then fill in your keys
python -m agent plan      # draft and design next week
python -m agent approve-all
python -m agent list      # see the queue
python -m agent approve <id>
python -m agent publish-due
python -m agent comments
python -m agent send-replies
python -m agent report
```

Run the tests with `pip install -r requirements-dev.txt && python -m pytest`.

## Project layout

| Path | What it is |
|---|---|
| `agent/brain.py` | Claude prompts: weekly plan, comment replies, report |
| `agent/design.py` | Draws the slides and builds reel videos |
| `agent/instagram.py` | Instagram API: publish, comments, insights |
| `agent/youtube.py` | Uploads reels to YouTube as Shorts |
| `agent/store.py` | The approval queue (JSON files) |
| `agent/cli.py` | The commands above |
| `.github/workflows/agent.yml` | The schedule that runs everything |
| `queue/` | Post drafts and their status |
| `replies/pending.json` | Comment reply drafts |
| `media/` | The designed images and videos |
| `reports/` | Weekly previews and reports |
| `docs/posting-times.md` | Best posting times for Indian followers |
| `assets/fonts/` | Inter font (SIL Open Font License) |
| `assets/music/` | Royalty-free reel music (Pixabay Content License), one folder per mood |
