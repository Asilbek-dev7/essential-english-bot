#!/usr/bin/env bash
# Pull the latest code from GitHub and restart the bot. Run as root on the server.
set -euo pipefail
APP_DIR="/opt/essential-english-bot"

git -C "$APP_DIR" pull --ff-only
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
chown -R bot:bot "$APP_DIR"
systemctl restart essential-bot
sleep 3
systemctl --no-pager --lines=10 status essential-bot || true
