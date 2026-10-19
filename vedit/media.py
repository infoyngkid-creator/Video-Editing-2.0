"""Ingest: Archiv-IDs vergeben, Metadaten lesen, Proxys + Audio erzeugen."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from . import config
from .util import read_json, run, write_json


def probe(path: Path) -> dict:
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
               "-show_streams", path], capture=True).stdout
    data = json.loads(out)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), {})
    tags = {**data["format"].get("tags", {}), **v.get("tags", {})}
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    rot = 0
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) in (90, 270):
        w, h = h, w
    created = (tags.get("com.apple.quicktime.creationdate")
               or tags.get("creation_time") or "")
    num, den = (v.get("avg_frame_rate", "0/1").split("/") + ["1"])[:2]
    return {
        "dauer": round(float(data["format"].get("duration", 0)), 2),
        "breite": w, "hoehe": h,
        "fps": round(float(num) / float(den), 2) if float(den) else 0,
        "hdr": v.get("color_transfer") in ("arib-std-b67", "smpte2084"),
        "aufgenommen": created,
        "audio": any(s["codec_type"] == "audio" for s in data["streams"]),
    }


def _date(created: str):
    try:
        return datetime.fromisoformat(created.replace("Z", "+00:00"))
    except ValueError:
        return None


def assign_ids(event_dir: Path, raw_dir: Path) -> dict:
    """Vergibt Archiv-IDs JP-YYMMDD-NN nach Aufnahmezeit. Bestehende IDs bleiben stabil."""
    shots_file = event_dir / "shots.json"
    shots = read_json(shots_file, {})
    known = {s["datei"] for s in shots.values()}
    new = []
    for f in sorted(raw_dir.iterdir()):
        if f.suffix.lower() in config.VIDEO_EXT and f.name not in known and not f.name.startswith("."):
            meta = probe(f)
            new.append((meta, f))
    new.sort(key=lambda mf: (_date(mf[0]["aufgenommen"]) or datetime.max.astimezone(), mf[1].name))
    for meta, f in new:
        d = _date(meta["aufgenommen"])
        day = d.strftime("%y%m%d") if d else "000000"
        n = 1 + max([int(k.rsplit("-", 1)[1]) for k in shots if k.startswith(f"JP-{day}-")] or [0])
        sid = f"JP-{day}-{n:02d}"
        shots[sid] = {"datei": f.name, **meta}
    write_json(shots_file, dict(sorted(shots.items())))
    return shots


def _proxy(src: Path, dst: Path, wav: Path):
    if not dst.exists():
        # Proxy: 540p, schnell, SDR-Tonemapping für HDR-iPhone-Footage
        run(["ffmpeg", "-y", "-v", "error", "-i", src,
             "-vf", f"scale=-2:{config.PROXY_H},format=yuv420p",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
             "-c:a", "aac", "-b:a", "96k", dst])
    if not wav.exists():
        run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav])


def make_proxies(raw_dir: Path, work_dir: Path, shots: dict, workers=3):
    pdir = work_dir / "proxy"
    pdir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(lambda kv: _proxy(raw_dir / kv[1]["datei"], pdir / f"{kv[0]}.mp4",
                                      pdir / f"{kv[0]}.wav"), shots.items()))


def slugify(text: str) -> str:
    text = (text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
            .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue").replace("ß", "ss"))
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
