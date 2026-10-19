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

# Drive-Remote "gdrive" rein über Umgebungsvariablen. Token kommt aus dem Environment-Secret GDRIVE_TOKEN.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export RCLONE_CONFIG_GDRIVE_TYPE=drive"
    echo "export RCLONE_CONFIG_GDRIVE_SCOPE=drive"
    if [ -n "${GDRIVE_TOKEN:-}" ]; then
      printf 'export RCLONE_CONFIG_GDRIVE_TOKEN=%q\n' "$GDRIVE_TOKEN"
    fi
  } >> "$CLAUDE_ENV_FILE"
fi

if [ -z "${GDRIVE_TOKEN:-}" ]; then
  echo "Hinweis: GDRIVE_TOKEN fehlt – Drive-Zugriff erst nach Einrichtung (README › Einrichtung)."
fi
