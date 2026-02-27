# trello-post-scheduler

Posts Trello cards to Twitter/X, Bluesky, and Mastodon on a schedule. Supports image attachments.

## How it works

- Cards are pulled from a configurable Trello list
- Card title is used as post text
- If an image is attached to the card, the card description is used as alt text

## Install

Requires [pipx](https://pipx.pypa.io).

```
pipx install .
cp trello-post-scheduler.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable trello-post-scheduler
```

## Configuration

Copy the example config:

```
mkdir -p ~/.config/trello-post-scheduler
cp config.example.toml ~/.config/trello-post-scheduler/config.toml
```

Edit `~/.config/trello-post-scheduler/config.toml` before starting the service.

### Getting API keys

**Trello**

1. Get your API key at https://trello.com/power-ups/admin — click on an existing power-up or create one, then find the API key
2. On that same page, generate a token by clicking the "Token" link next to your API key
3. To get your board ID: open the board in a browser, add `.json` to the URL (e.g. `https://trello.com/b/XXXXX/board-name.json`), and copy the `"id"` field from the top of the JSON

**Twitter/X**

1. Create a project and app at https://developer.x.com/en/portal/dashboard
2. In your app settings, set up "User authentication" with Read and Write permissions
3. Under "Keys and tokens", generate API Key & Secret, Access Token & Secret, and Bearer Token

**Bluesky**

1. `handle` is your full handle, e.g. `yourname.bsky.social`
2. `password` is an app password — create one at https://bsky.app/settings/app-passwords

**Mastodon**

1. Go to your instance's settings > Development > New Application
2. Set scopes to `write:statuses` and `write:media`
3. Copy the access token after saving

### Config reference

```toml
[trello]
api_key = ""
api_token = ""
board_id = ""
source_list = "Post Queue"      # list name to pull cards from

[schedule]
post_times = ["09:00", "13:00", "18:30"]  # 24-hour format
post_time_randomization = 600             # +/- seconds

[platforms.twitter]
enabled = false
api_key = ""
api_secret = ""
access_token = ""
access_secret = ""
bearer_token = ""

[platforms.bluesky]
enabled = false
handle = ""
password = ""

[platforms.mastodon]
enabled = false
instance_url = "https://mastodon.social"
access_token = ""

[logging]
level = "INFO"
```

Set `enabled = true` on platforms you want to use after filling in credentials.

## Usage

### Running as a service

```
systemctl --user start trello-post-scheduler
```

### One-off and dry-run

```
# post one card and exit
trello-post-scheduler --config ~/.config/trello-post-scheduler/config.toml --once

# show what would be posted without actually posting
trello-post-scheduler --config ~/.config/trello-post-scheduler/config.toml --dry-run --once
```
