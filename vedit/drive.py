"""Google-Drive-Zugriff über rclone.

Der Remote wird komplett über Umgebungsvariablen konfiguriert (kein rclone.conf nötig):
  RCLONE_CONFIG_GDRIVE_TYPE=drive
  RCLONE_CONFIG_GDRIVE_SCOPE=drive
  RCLONE_CONFIG_GDRIVE_TOKEN=<JSON aus `rclone authorize "drive"`>
scripts/setup.sh setzt TYPE/SCOPE und übernimmt GDRIVE_TOKEN aus dem Environment-Secret.
Alle Pfade sind relativ zum Ordner "JOE X PSGOTRICH" (config.DRIVE_ROOT_ID).
"""
import json
import os
import shutil
from pathlib import Path

from . import config
from .util import run


def _base():
    if not shutil.which("rclone"):
        raise SystemExit("rclone fehlt – erst `bash scripts/setup.sh` ausführen.")
    env_token = os.environ.get(f"RCLONE_CONFIG_{config.REMOTE.upper()}_TOKEN")
    if not env_token:
        raise SystemExit(
            "Kein Drive-Zugang. GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN als "
            "Environment-Variablen hinterlegen "
            "(siehe README › Einrichtung) und neue Session starten.")
    return ["rclone", "--drive-root-folder-id", config.DRIVE_ROOT_ID]


def remote(path: str = "") -> str:
    return f"{config.REMOTE}:{path}"


def ls(path: str = "", dirs_only=False, recursive=False):
    cmd = _base() + ["lsjson", remote(path)]
    if dirs_only:
        cmd.append("--dirs-only")
    if recursive:
        cmd.append("-R")
    out = run(cmd, capture=True).stdout
    return json.loads(out or "[]")


def download(path: str, dest: Path):
    """Lädt Datei oder Ordner herunter. Überspringt, was schon vollständig da ist."""
    dest.mkdir(parents=True, exist_ok=True)
    run(_base() + ["copy", remote(path), str(dest), "--transfers", "4",
                   "--include", "*.{mov,MOV,mp4,MP4,m4v,mkv,wav,mp3,m4a}",
                   "--progress", "--stats-one-line"])


def download_file(path: str, dest_dir: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)
    run(_base() + ["copy", remote(path), str(dest_dir), "--progress", "--stats-one-line"])


def upload(src: Path, path: str):
    """Datei oder Ordnerinhalt nach Drive kopieren (überschreibt nur Geändertes)."""
    if src.is_dir():
        run(_base() + ["copy", str(src), remote(path), "--transfers", "4",
                       "--progress", "--stats-one-line"])
    else:
        run(_base() + ["copyto", str(src), remote(f"{path}/{src.name}"),
                       "--progress", "--stats-one-line"])


def is_upload_finished(path: str) -> tuple[bool, list]:
    """Heuristik: Upload gilt als fertig, wenn sich der Ordner zwischen zwei Abfragen nicht ändert."""
    import time
    a = {f["Path"]: f["Size"] for f in ls(path) if not f["IsDir"]}
    time.sleep(20)
    b_list = ls(path)
    b = {f["Path"]: f["Size"] for f in b_list if not f["IsDir"]}
    return a == b and bool(b), b_list


def link_download(file_id: str, dest: Path):
    """Download ohne Token: funktioniert, solange der Ordner per Link freigegeben ist
    ("Jeder mit dem Link"). Datei-IDs liefert der Google-Drive-Connector in Claude."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
    run(["curl", "-sSL", "--fail", "--retry", "3", "-o", dest, url])
    with open(dest, "rb") as f:
        if f.read(15).lstrip().startswith(b"<"):
            dest.unlink()
            raise SystemExit(f"{dest.name}: kein Zugriff – Ordner in Drive auf "
                             "'Jeder mit dem Link' stellen.")
