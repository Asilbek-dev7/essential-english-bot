# Essential English Words — Telegram Bot

A Telegram vocabulary quiz bot for the "Essential English Words" book series. Built with Python 3.12, aiogram 3, and SQLite.

## How to Run

The `Start application` workflow runs the bot:

```
python -m bot.main
```

The bot uses long polling (no webhook needed). It also starts a lightweight HTTP keep-alive server on port 8080 so uptime monitors can ping it.

## Required Secrets

| Secret | Description |
|--------|-------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_IDS` | *(empty)* | Comma-separated Telegram user IDs with admin access |
| `DB_PATH` | `data/bot.db` | Path to the SQLite database file |

**To enable the admin panel:** set `ADMIN_IDS` to your Telegram user ID (get it from @userinfobot). Without it, no one can access `/admin`.

## Stack

- **Python 3.12** + **aiogram 3.15** — Telegram bot framework
- **aiosqlite** — async SQLite database
- **pdfplumber** — PDF import for word lists
- **python-dotenv** — environment variable loading

## Project Structure

```
bot/
  config.py       — loads env vars
  database.py     — SQLite schema and queries (books/units/words/users)
  keyboards.py    — inline keyboard builders
  states.py       — admin FSM states
  main.py         — entry point (polling + keep-alive server)
  handlers/
    user.py       — /start, quiz flow
    admin.py      — /admin, CRUD, bulk import
import_wordlist.py  — standalone import script
seed_demo.py        — seed demo words for testing
data/bot.db         — SQLite file (auto-created on first run)
```

## User Preferences

- Keep the existing project structure and stack unchanged.
