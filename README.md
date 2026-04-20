# Newsletter Subscription Manager

Consolidate, search, and summarize all your newsletter subscriptions in one place. Sends a daily digest to your inbox every morning at 7 AM via Gmail + Claude.

## Features

| Goal | How it works |
|------|-------------|
| **Consolidate subscriptions** | Discovers newsletters via Gmail's `has:unsubscribe` filter _and_ by your `+subs` address |
| **Search** | Full-text search across stored newsletter content, or pass `--gmail` to query Gmail live |
| **Daily 7 AM digest** | Scheduler syncs Gmail, summarises each newsletter with Claude, and emails a styled digest |
| **Manage from Gmail** | Apply the `Newsletters/Unsubscribe` label to any thread in Gmail; the next sync deactivates it |

---

## Prerequisites

1. **Python 3.9+**
2. **Google Cloud project** with the Gmail API enabled and an OAuth 2.0 Desktop client ID  
   → download `credentials.json` to this folder  
   (Console → APIs & Services → Credentials → Create Credentials → OAuth client ID → Desktop app)
3. **Anthropic API key** for newsletter summarisation

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and fill in the config
cp .env.example .env
$EDITOR .env          # set ANTHROPIC_API_KEY, DIGEST_RECIPIENT, etc.

# 3. Authenticate with Gmail (opens a browser window once)
python main.py sync --days 1

# 4. (Optional) Create Gmail label structure
python main.py setup-gmail
```

---

## Usage

### One-time import

```bash
# Import the last 30 days of newsletters
python main.py sync --days 30
```

### Daily commands

```bash
python main.py list                      # all active subscriptions
python main.py search "AI news"          # local full-text search
python main.py search "AI news" --gmail  # live Gmail search
python main.py digest                    # send today's digest now
python main.py digest --dry-run          # preview without sending
python main.py stats                     # quick statistics
```

### Manage subscriptions

```bash
# Deactivate from the CLI (fuzzy match on email address)
python main.py unsubscribe substack

# Or in Gmail: apply the "Newsletters/Unsubscribe" label to any newsletter thread.
# The next `sync` picks it up and deactivates that subscription automatically.
```

### Run the daemon (automatic sync + 7 AM digest)

```bash
python main.py start
```

The daemon syncs Gmail every 2 hours and sends the digest at the time set by `DIGEST_TIME`.

---

## Newsletter discovery

Two methods run in parallel during every sync:

1. **`has:unsubscribe`** — Gmail's built-in filter that matches emails with an unsubscribe mechanism (covers the vast majority of newsletters).
2. **`to:annejin2021+subs@gmail.com`** — catches newsletters directed to your subscription address.

Results are deduplicated before being stored.

---

## Gmail label structure

After running `setup-gmail` you'll see:

```
Newsletters/
├── <Sender Name>   ← auto-created and applied to each newsletter as it is synced
└── Unsubscribe     ← apply this label in Gmail to deactivate a subscription
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GMAIL_CREDENTIALS_FILE` | `credentials.json` | OAuth2 client secrets |
| `GMAIL_TOKEN_FILE` | `token.json` | Auto-generated auth token |
| `ANTHROPIC_API_KEY` | — | Claude API key |
| `DIGEST_RECIPIENT` | — | Email address to receive the daily digest |
| `DIGEST_TIME` | `07:00` | Time to send the daily digest (24-hour) |
| `TIMEZONE` | `America/New_York` | pytz timezone for scheduling |
| `DATABASE_PATH` | `newsletters.db` | SQLite database file |
| `SUBSCRIPTION_EMAIL` | `annejin2021+subs@gmail.com` | Your newsletter subscription address |
| `GMAIL_LABEL_PREFIX` | `Newsletters` | Top-level Gmail label |
