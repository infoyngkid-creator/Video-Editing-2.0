"""Zentrale Einstellungen. Alles per Umgebungsvariable überschreibbar."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EDITS = ROOT / "edits"                      # versioniert: Kontext, Schnittplan, Specs, Transkripte
WORK = Path(os.environ.get("VEDIT_WORK", ROOT / "work"))  # nicht versioniert: Medien

# rclone-Remote. Konfiguration kommt aus Umgebungsvariablen (siehe scripts/setup.sh).
REMOTE = os.environ.get("VEDIT_REMOTE", "gdrive")
# Ordner "JOE X PSGOTRICH" in Drive
DRIVE_ROOT_ID = os.environ.get("VEDIT_DRIVE_ROOT_ID", "1gxp8zG5hgsyqUXvIrgD2KXqU7dCUrXn4")
EINGANG = "01_EINGANG"
# Ordnernamen kommen vom Mac in NFD-Unicode (u + Trema) – rclone vergleicht exakt
import unicodedata
ENTWUERFE = unicodedata.normalize("NFD", "02_Entwürfe")
ARCHIV = "03_Archiv"
MUSIK = "05_Musik"

VIDEO_EXT = {".mov", ".mp4", ".m4v", ".mkv"}

# Render-Ziele
REEL_W, REEL_H = 1080, 1920
YT_W, YT_H = 1920, 1080
FPS = 30
CRF = int(os.environ.get("VEDIT_CRF", "20"))
PRESET = os.environ.get("VEDIT_PRESET", "medium")
PROXY_H = 540   # Proxy-Höhe für Analyse/Vorschau

WHISPER_MODEL = os.environ.get("VEDIT_WHISPER_MODEL", "small")
