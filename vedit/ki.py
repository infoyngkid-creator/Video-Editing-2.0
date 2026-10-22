"""KI-Shots (Higgsfield „AI LARP“): echten Archiv-Clip als Vorlage rausschneiden und das
KI-Ergebnis wie einen normalen Shot ins Event übernehmen (shots.json, Proxy, schnitt.json).

Die Generierung selbst macht Claude über den Higgsfield-Connector (MCP) – hier nur Vor- und Nacharbeit.
"""
import shutil
from datetime import datetime
from pathlib import Path

from . import config, drive, media
from .util import read_json, run, write_json

MAX_SEK = 10.0   # Higgsfield-Video-Modelle nehmen meist 5–10 s Referenz


def quelle(event_dir: Path, work_dir: Path, sid: str, von: float, bis: float) -> Path:
    """Schneidet die Vorlage für Higgsfield: SDR, kurze Seite 1080 px, max. 10 s, H.264 – lädt jedes Modell."""
    shots = read_json(event_dir / "shots.json")
    if sid not in shots:
        raise SystemExit(f"Shot {sid} gibt es in {event_dir.name} nicht.")
    meta = shots[sid]
    if bis - von > MAX_SEK:
        print(f"⚠ {bis - von:.1f} s ist lang – auf {MAX_SEK:.0f} s gekürzt (kostet sonst mehr Credits).")
        bis = von + MAX_SEK
    src = work_dir / "raw" / meta["datei"]
    if not src.exists() and meta.get("drive_id"):
        drive.link_download(meta["drive_id"], src)
    if not src.exists():
        src = work_dir / "proxy" / f"{sid}.mp4"
        if not src.exists():
            raise SystemExit(f"Quelle für {sid} fehlt – erst `vedit holen`/`neu` ausführen.")
        print("⚠ Nur Proxy (540p) vorhanden – Higgsfield-Ergebnis wird schlechter.")
    short = min(meta["breite"], meta["hoehe"], 1080)
    scale = f"scale=-2:{short}" if meta["breite"] >= meta["hoehe"] else f"scale={short}:-2"
    vf = ([media.TONEMAP] if meta.get("hdr") and src.suffix.lower() != ".mp4" else []) + \
         [scale + ":flags=lanczos", "format=yuv420p"]
    out = work_dir / "ki" / f"VORLAGE_{sid}_{von:.1f}-{bis:.1f}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{von:.3f}", "-to", f"{bis:.3f}", "-i", src,
         "-vf", ",".join(vf), "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out])
    return out


def _next_id(shots: dict, day: str) -> str:
    n = 1 + max([int(k.rsplit("-", 1)[1]) for k in shots if k.startswith(f"JP-{day}-KI-")] or [0])
    return f"JP-{day}-KI-{n:02d}"


def uebernehmen(event_dir: Path, work_dir: Path, datei: str, von_shot: str | None,
                prompt: str, modell: str, credits: float | None, drive_id: str | None) -> str:
    """Nimmt das Higgsfield-Ergebnis (lokale Datei oder URL) als Shot JP-YYMMDD-KI-NN auf."""
    shots = read_json(event_dir / "shots.json", {})
    day = datetime.strptime(read_json(event_dir / "event.json")["datum"], "%Y-%m-%d").strftime("%y%m%d")
    sid = _next_id(shots, day)
    dst = work_dir / "raw" / f"{sid}.mp4"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if datei.startswith("http"):
        run(["curl", "-sSL", "--fail", "--retry", "3", "-o", dst, datei])
    elif drive_id and not Path(datei).exists():
        drive.link_download(drive_id, dst)
    else:
        shutil.copy(datei, dst)
    meta = media.probe(dst)
    meta["hdr"] = False
    shots[sid] = {"datei": dst.name, **meta, "ki": {
        "tool": "Higgsfield", "modell": modell, "prompt": prompt, "vorlage": von_shot,
        "credits": credits, "quelle": datei if datei.startswith("http") else Path(datei).name,
        "erstellt": datetime.now().isoformat(timespec="minutes")}}
    if drive_id:
        shots[sid]["drive_id"] = drive_id
    write_json(event_dir / "shots.json", dict(sorted(shots.items())))
    media.make_proxies(work_dir / "raw", work_dir, {sid: shots[sid]})
    # Kein Transkript: KI-Ton ist meist Musik/Atmo. Für Untertitel den Text der Vorlage nutzen.
    return sid


def liste(event_dir: Path):
    shots = read_json(event_dir / "shots.json", {})
    ki = {k: v for k, v in shots.items() if v.get("ki")}
    if not ki:
        print("Noch keine KI-Shots.")
    total = 0.0
    for sid, s in ki.items():
        k = s["ki"]
        total += k.get("credits") or 0
        print(f"{sid}  {s['dauer']} s  {k['modell']}  Vorlage {k.get('vorlage') or '–'}  "
              f"{k.get('credits') or '?'} Credits  „{k['prompt'][:60]}“"
              f"{'' if s.get('drive_id') else '  ⚠ nicht in Drive'}")
    if ki:
        print(f"Summe: {total:g} Credits")
