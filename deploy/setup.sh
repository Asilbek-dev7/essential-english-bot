#!/usr/bin/env bash
# Essential English Bot — one-shot installer for a fresh Ubuntu 22.04/24.04 (or Debian 12) VPS.
# Run as root:  bash setup.sh
set -euo pipefail

REPO_URL="https://github.com/Asilbek-dev7/essential-english-bot.git"
APP_DIR="/opt/essential-english-bot"
APP_USER="bot"

if [ "$(id -u)" -ne 0 ]; then
  echo "root sifatida ishga tushiring: sudo bash setup.sh"; exit 1
fi

read -rp "BOT_TOKEN: " BOT_TOKEN
read -rp "ADMIN_IDS (vergul bilan, bo'shliqsiz): " ADMIN_IDS
[ -n "$BOT_TOKEN" ] || { echo "BOT_TOKEN bo'sh bo'lmasligi kerak"; exit 1; }

echo "==> Paketlar o'rnatilmoqda"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git sqlite3

echo "==> Foydalanuvchi va kod"
id "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$APP_DIR"
fi
# the DB file is tracked (seed data) but changes at runtime: never let `git pull` fight over it
git -C "$APP_DIR" update-index --skip-worktree data/bot.db || true

echo "==> Python muhiti"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> .env"
cat > "$APP_DIR/.env" <<EOF
BOT_TOKEN=$BOT_TOKEN
ADMIN_IDS=$ADMIN_IDS
DB_PATH=data/bot.db
EOF
chmod 600 "$APP_DIR/.env"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

echo "==> systemd xizmati"
cat > /etc/systemd/system/essential-bot.service <<EOF
[Unit]
Description=Essential English Words Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python -m bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "==> Kunlik zaxira nusxa (7 kun saqlanadi)"
mkdir -p /var/backups/essential-bot
cat > /etc/cron.daily/essential-bot-backup <<EOF
#!/bin/sh
sqlite3 $APP_DIR/data/bot.db ".backup '/var/backups/essential-bot/bot-\$(date +%F).db'"
find /var/backups/essential-bot -name 'bot-*.db' -mtime +7 -delete
EOF
chmod +x /etc/cron.daily/essential-bot-backup

systemctl daemon-reload
systemctl enable --now essential-bot
sleep 3
systemctl --no-pager --lines=15 status essential-bot || true

echo
echo "Tayyor. Loglar:      journalctl -u essential-bot -f"
echo "Yangilash:           bash $APP_DIR/deploy/update.sh"
