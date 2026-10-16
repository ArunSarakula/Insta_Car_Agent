# Insta Car Agent

A personal content agent for a car-tech Instagram account. Every week it:

1. **Plans** next week's posts (reels, carousels, memes) with hooks, captions,
   hashtags, reel scripts, carousel slide text and a story poll for every day.
2. **Waits for you to approve** each post. Nothing is ever posted without your OK.
3. **Publishes** approved posts at their scheduled time.
4. **Drafts replies** to new comments, which you approve before they are sent.
5. **Writes a weekly report**: followers, best and worst posts, what to do next.

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
`POSTS_PER_WEEK` (default `5`).

### 5. Turn on Actions
Repo → **Actions** tab → enable workflows if GitHub asks.

Done. To try it right away: **Actions → Instagram agent → Run workflow →
command: plan**.

---

## Your weekly routine (about 30 minutes)

**Sunday:** the agent plans next week automatically. New drafts appear in
the `queue/` folder, one file per post, and story poll ideas in `reports/`.

For each post in `queue/`:

1. Open the file on GitHub and read the caption and script. Click the ✏️ pencil
   to edit anything you don't like.
2. **Add the media.** Make the image or video described in `visual_brief`
   (Canva, CapCut, your phone), then either:
   - upload it to the `media/` folder and list it in the post, for example
     `"media_files": ["media/ev-battery-1.jpg"]` (this only works if the repo
     is **public**), or
   - put a public link in `"media_urls": ["https://..."]`.
   A carousel needs 2 to 10 images. A reel needs one `.mp4` video.
3. Change `"status": "draft"` to `"status": "approved"` and commit.

The agent checks every hour and publishes approved posts when their time comes.
To skip a post, set its status to `"rejected"`.

**Comments:** every 3 hours the agent drafts replies in
`replies/pending.json`. Edit any reply, set `"status": "approved"`, then run
**Actions → Instagram agent → Run workflow → send-replies**.

Comments flagged `needs_owner` (complaints, business offers) deserve your
personal attention. Comments flagged `spam` get no reply.

**Daily:** post that day's story poll from `reports/polls-*.md` (Instagram
does not let apps post story polls, so this one is manual).

---

## Running it on your own computer (optional)

```bash
pip install -r requirements.txt
cp .env.example .env      # then fill in your keys
python -m agent plan      # draft next week
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
| `agent/instagram.py` | Instagram API: publish, comments, insights |
| `agent/store.py` | The approval queue (JSON files) |
| `agent/cli.py` | The commands above |
| `.github/workflows/agent.yml` | The schedule that runs everything |
| `queue/` | Post drafts and their status |
| `replies/pending.json` | Comment reply drafts |
| `reports/` | Story polls and weekly reports |
