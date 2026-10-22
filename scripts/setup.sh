#!/usr/bin/env bash
# Richtet eine (Cloud- oder lokale) Session ein: rclone + Python-Pakete + Drive-Remote.
# Idempotent – läuft bei jedem Session-Start über den SessionStart-Hook.
set -euo pipefail

if ! command -v rclone >/dev/null 2>&1; then
  tmp=$(mktemp -d)
  curl -fsSL -o "$tmp/rclone.zip" https://downloads.rclone.org/rclone-current-linux-amd64.zip
  (cd "$tmp" && unzip -q rclone.zip && install -m 755 rclone-*-linux-amd64/rclone /usr/local/bin/rclone)
  rm -rf "$tmp"
fi

python3 -c "import faster_whisper" 2>/dev/null || pip install -q faster-whisper >/dev/null 2>&1 || true
python3 -c "import cv2" 2>/dev/null || pip install -q opencv-python-headless >/dev/null 2>&1 || true
python3 -c "import fal_client" 2>/dev/null || pip install -q fal-client >/dev/null 2>&1 || true

# Drive-Remote "gdrive" rein über Umgebungsvariablen (Environment-Secrets der Cloud-Umgebung):
#   GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN  (eigener OAuth-Client, Handy-Setup, README)
#   oder GDRIVE_TOKEN  (kompletter JSON-Block aus `rclone authorize "drive"`)
if [ -n "${GDRIVE_REFRESH_TOKEN:-}" ] && [ -z "${GDRIVE_TOKEN:-}" ]; then
  # abgelaufener Access-Token erzwingt sofortigen Refresh über den Refresh-Token
  GDRIVE_TOKEN="{\"access_token\":\"\",\"token_type\":\"Bearer\",\"refresh_token\":\"${GDRIVE_REFRESH_TOKEN}\",\"expiry\":\"2000-01-01T00:00:00Z\"}"
fi
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export RCLONE_CONFIG_GDRIVE_TYPE=drive"
    echo "export RCLONE_CONFIG_GDRIVE_SCOPE=drive"
    [ -n "${GDRIVE_CLIENT_ID:-}" ] && printf 'export RCLONE_CONFIG_GDRIVE_CLIENT_ID=%q\n' "$GDRIVE_CLIENT_ID"
    [ -n "${GDRIVE_CLIENT_SECRET:-}" ] && printf 'export RCLONE_CONFIG_GDRIVE_CLIENT_SECRET=%q\n' "$GDRIVE_CLIENT_SECRET"
    [ -n "${GDRIVE_TOKEN:-}" ] && printf 'export RCLONE_CONFIG_GDRIVE_TOKEN=%q\n' "$GDRIVE_TOKEN"
    true
  } >> "$CLAUDE_ENV_FILE"
fi

if [ -z "${GDRIVE_TOKEN:-}" ]; then
  echo "Hinweis: Drive-Zugang fehlt – GDRIVE_CLIENT_ID/SECRET/REFRESH_TOKEN setzen (README › Einrichtung)."
fi
