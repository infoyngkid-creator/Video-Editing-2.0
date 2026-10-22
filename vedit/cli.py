"""Kommandozeile: python -m vedit <befehl> …

Ablauf für ein neues Event:
  status                          Drive-Überblick: Eingang, Entwürfe, laufende Uploads
  neu <drive-ordner> <datum> <name>   Event anlegen, Footage holen, IDs, Proxys, Transkript
  vorschau <event> [nr …]         schnelle 540p-Vorschau aus Proxys
  render <event> [nr …]           finale Videos aus Originalen
  ki-vorlage / ki-shot / ki-liste   KI-Shots (Higgsfield, siehe Skill ai-larp)
  hochladen <event>               Exporte + Kontext.md + Schnittplan.txt nach 02_Entwürfe
"""
import argparse
import json
import os
import sys
from pathlib import Path

from . import config, drive, media, render, transcribe
from .util import read_json, write_json


def _event_dirs(event: str):
    ed = config.EDITS / event
    if not ed.exists():
        matches = [p for p in config.EDITS.iterdir() if event.lower() in p.name.lower()]
        if len(matches) != 1:
            raise SystemExit(f"Event '{event}' nicht eindeutig: {[m.name for m in matches]}")
        ed = matches[0]
    return ed, config.WORK / ed.name


def cmd_status(a):
    for name in (config.EINGANG, config.ENTWUERFE):
        print(f"\n== {name}")
        for f in drive.ls(name, dirs_only=True):
            print(f"  {f['Name']}/")
    print("\n== Wurzel (lose Ordner = meist neue Uploads)")
    for f in drive.ls(""):
        if f["IsDir"] and not f["Name"][:2].isdigit():
            files = [x for x in drive.ls(f["Name"]) if not x["IsDir"]]
            gb = sum(x["Size"] for x in files) / 1e9
            print(f"  {f['Name']}/  {len(files)} Dateien, {gb:.2f} GB, zuletzt {f['ModTime'][:16]}")


def cmd_neu(a):
    event = f"{a.datum}_{media.slugify(a.name)}"
    ed, wd = config.EDITS / event, config.WORK / event
    ed.mkdir(parents=True, exist_ok=True)
    meta = read_json(ed / "event.json", {})
    meta.update({"datum": a.datum, "name": a.name, "quelle": a.ordner})
    write_json(ed / "event.json", meta)
    if not a.skip_check:
        done, files = drive.is_upload_finished(a.ordner)
        if not done:
            print(f"⚠ Upload in '{a.ordner}' läuft noch ({len(files)} Dateien). "
                  "Hole, was schon da ist – später `vedit neu` erneut ausführen für den Rest.")
    drive.download(a.ordner, wd / "raw")
    cmd_ingest(argparse.Namespace(event=event))


def cmd_holen(a):
    """Lädt Dateien per Datei-ID (Zeilen 'ID Dateiname' in einer Liste) – ohne Drive-Token."""
    from concurrent.futures import ThreadPoolExecutor
    event = f"{a.datum}_{media.slugify(a.name)}"
    ed, wd = config.EDITS / event, config.WORK / event
    ed.mkdir(parents=True, exist_ok=True)
    meta = read_json(ed / "event.json", {})
    meta.update({"datum": a.datum, "name": a.name, "quelle": a.quelle})
    rows = [l.split(None, 1) for l in Path(a.liste).read_text().splitlines() if l.strip()]
    meta["drive_ids"] = {name.strip(): fid for fid, name in rows}
    write_json(ed / "event.json", meta)
    todo = [(fid, wd / "raw" / name.strip()) for fid, name in rows
            if not (wd / "raw" / name.strip()).exists()]
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda t: drive.link_download(*t), todo))
    cmd_ingest(argparse.Namespace(event=event))


def cmd_ingest(a):
    ed, wd = _event_dirs(a.event)
    shots = media.assign_ids(ed, wd / "raw")
    print(f"{len(shots)} Shots: " + ", ".join(f"{k} ({v['dauer']} s)" for k, v in shots.items()))
    media.make_proxies(wd / "raw", wd, shots)
    transcribe.transcribe_event(ed, wd, shots)
    if not (ed / "schnitt.json").exists():
        write_json(ed / "schnitt.json", {"datum": read_json(ed / "event.json")["datum"],
                                         "videos": []})
    print(f"\nFertig. Transkript: {ed / 'transkript.txt'}")


def _select(ed, nrs):
    spec = read_json(ed / "schnitt.json")
    vids = [v for v in spec["videos"] if not nrs or v["nr"] in nrs]
    if not vids:
        raise SystemExit("Keine passenden Videos in schnitt.json.")
    return vids


def _music(wd, v):
    if not v.get("musik"):
        return None
    path = v["musik"]["datei"]
    local = wd / "musik" / Path(path).name
    if not local.exists():
        drive.download_file(path, wd / "musik")
    return local


def cmd_render(a, preview=False):
    ed, wd = _event_dirs(a.event)
    if not preview:
        # Nur die Originale holen, die wirklich gebraucht werden
        shots = read_json(ed / "shots.json")
        quelle = read_json(ed / "event.json")["quelle"]
        need = {c["shot"] for v in _select(ed, a.nr) for c in v["clips"]}
        ids = read_json(ed / "event.json").get("drive_ids", {})
        for sid in sorted(need):
            datei = shots[sid]["datei"]
            fid = shots[sid].get("drive_id") or ids.get(datei)
            if not (wd / "raw" / datei).exists():
                ki_url = (shots[sid].get("ki") or {}).get("quelle", "")
                if not fid and ki_url.startswith("http"):
                    from .util import run
                    (wd / "raw").mkdir(parents=True, exist_ok=True)
                    run(["curl", "-sSL", "--fail", "--retry", "3", "-o", wd / "raw" / datei, ki_url])
                elif not fid and shots[sid].get("ki"):
                    raise SystemExit(f"{sid} (KI-Shot) fehlt lokal und ist nicht in Drive – "
                                     "Datei nach 03_Archiv/<event>/ legen und drive_id in shots.json eintragen.")
                elif fid:
                    drive.link_download(fid, wd / "raw" / datei)
                else:
                    drive.download_file(f"{quelle}/{datei}", wd / "raw")
    for v in _select(ed, a.nr):
        mus = _music(wd, v)
        if mus:
            print(render.render_video(ed, wd, v, preview, mus, "_PREVIEW" if not preview else ""))
            print(render.render_video(ed, wd, v, preview, None, "_OHNE-MUSIK"))
        else:
            print(render.render_video(ed, wd, v, preview))


def cmd_archiv(a):
    """Archiv-Index über alle Events – damit alte Shots jederzeit wieder auffindbar sind."""
    for ed in sorted(p for p in config.EDITS.iterdir() if (p / "shots.json").exists()):
        ev = read_json(ed / "event.json", {})
        shots = read_json(ed / "shots.json")
        mins = sum(s["dauer"] for s in shots.values()) / 60
        print(f"{ed.name}  ({len(shots)} Shots, {mins:.1f} min, Drive-Ordner {ev.get('archiv_ordner_id', '–')})")
        if a.lang:
            for sid, s in shots.items():
                print(f"  {sid}  {s['dauer']:>7.1f} s  {s['breite']}x{s['hoehe']}  "
                      f"{s.get('original', s['datei'])}  {s.get('drive_id', '')}")


def cmd_archiv_plan(a):
    """Gibt aus, wie die Eingangs-Dateien im Drive umbenannt/verschoben werden (für den Drive-Connector)
    und trägt Drive-IDs + Archivnamen in shots.json ein."""
    ed, _ = _event_dirs(a.event)
    ev = read_json(ed / "event.json")
    ids = ev.get("drive_ids", {})
    shots = read_json(ed / "shots.json")
    plan = []
    for sid, s in shots.items():
        orig = s.get("original", s["datei"])
        fid = s.get("drive_id") or ids.get(orig)
        if not fid:
            print(f"! {sid}: keine Drive-ID für {orig}", file=sys.stderr)
            continue
        s["drive_id"], s["original"] = fid, orig
        s["archiv_name"] = f"{sid}{Path(orig).suffix.upper()}"
        plan.append({"fileId": fid, "title": s["archiv_name"], "description": f"Original: {orig}"})
    write_json(ed / "shots.json", shots)
    print(json.dumps(plan, ensure_ascii=False, indent=1))


def cmd_archivieren(a):
    """Komprimierte Archiv-Versionen (HEVC 1080p, SDR) aller Shots + Transkript/Kontext.
    Mit Drive-Token: Upload nach 03_Archiv/<event>/ – danach können die Originale weg."""
    ed, wd = _event_dirs(a.event)
    shots = read_json(ed / "shots.json")
    keep = set(a.vier_k or [])
    for sid, meta in shots.items():
        src = wd / "raw" / meta["datei"]
        if not src.exists():
            print(f"! {sid}: Original fehlt lokal ({meta['datei']})")
            continue
        out = media.compress_for_archive(src, wd / "archiv" / f"{sid}.mp4", meta, sid in keep)
        meta["archiv_mb"] = round(out.stat().st_size / 1e6, 1)
        meta["original_mb"] = round(src.stat().st_size / 1e6, 1)
    write_json(ed / "shots.json", shots)
    vorher = sum(m.get("original_mb", 0) for m in shots.values())
    nachher = sum(m.get("archiv_mb", 0) for m in shots.values())
    print(f"Archiv: {vorher / 1000:.2f} GB → {nachher / 1000:.2f} GB")
    if os.environ.get(f"RCLONE_CONFIG_{config.REMOTE.upper()}_TOKEN"):
        ziel = f"{config.ARCHIV}/{ed.name}"
        drive.upload(wd / "archiv", ziel)
        for name in ("transkript.txt", "Kontext.md", "shots.json"):
            if (ed / name).exists():
                drive.upload(ed / name, ziel)
        print(f"Hochgeladen: {ziel} – Originale im Eingang können gelöscht werden.")
    else:
        print("Kein Drive-Schreibzugriff – Archiv-Dateien liegen nur lokal in", wd / "archiv")


def cmd_hochladen(a):
    ed, wd = _event_dirs(a.event)
    ziel = f"{config.ENTWUERFE}/{ed.name}"
    sub = "vorschau" if a.vorschau else "export"
    for f in sorted((wd / sub).glob("*.mp4")):
        drive.upload(f, ziel)
    for name in ("Kontext.md", "Schnittplan.txt"):
        if (ed / name).exists():
            drive.upload(ed / name, ziel)
    print(f"Hochgeladen nach Drive: JOE X PSGOTRICH/{ziel}")


def cmd_ki_vorlage(a):
    from . import ki
    ed, wd = _event_dirs(a.event)
    print(ki.quelle(ed, wd, a.shot, a.von, a.bis))


def cmd_ki_shot(a):
    from . import ki
    ed, wd = _event_dirs(a.event)
    sid = ki.uebernehmen(ed, wd, a.datei, a.vorlage, a.prompt, a.modell, a.credits, a.drive_id)
    print(f"Neuer Shot: {sid} – in schnitt.json wie jeden Shot nutzen "
          f'({{"shot": "{sid}", "von": 0, "bis": …}}).')


def cmd_ki_liste(a):
    from . import ki
    ed, _ = _event_dirs(a.event)
    ki.liste(ed)


def main(argv=None):
    p = argparse.ArgumentParser(prog="vedit")
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("status").set_defaults(f=cmd_status)
    n = s.add_parser("neu")
    n.add_argument("ordner", help="Drive-Ordner relativ zu JOE X PSGOTRICH, z. B. 'Samstag shit '")
    n.add_argument("datum", help="Drehtag YYYY-MM-DD")
    n.add_argument("name", help="Event-Name, z. B. 'Samstag-Bremen'")
    n.add_argument("--skip-check", action="store_true", help="Upload-Prüfung überspringen")
    n.set_defaults(f=cmd_neu)
    g = s.add_parser("holen", help="Footage per Datei-IDs laden (ohne Token, Link-Freigabe)")
    g.add_argument("liste", help="Textdatei mit Zeilen 'DRIVE_ID Dateiname'")
    g.add_argument("datum")
    g.add_argument("name")
    g.add_argument("--quelle", default="", help="Drive-Ordnername (nur zur Info)")
    g.set_defaults(f=cmd_holen)
    i = s.add_parser("ingest", help="IDs/Proxys/Transkript für schon geladenes Footage")
    i.add_argument("event")
    i.set_defaults(f=cmd_ingest)
    for name, prev in (("vorschau", True), ("render", False)):
        r = s.add_parser(name)
        r.add_argument("event")
        r.add_argument("nr", nargs="*")
        r.set_defaults(f=lambda a, prev=prev: cmd_render(a, prev))
    ar = s.add_parser("archiv", help="Archiv-Index aller Events")
    ar.add_argument("--lang", action="store_true", help="alle Shots auflisten")
    ar.set_defaults(f=cmd_archiv)
    ap = s.add_parser("archiv-plan", help="Umbenenn-/Verschiebeplan fürs Drive-Archiv")
    ap.add_argument("event")
    ap.set_defaults(f=cmd_archiv_plan)
    av = s.add_parser("archivieren", help="komprimiertes Archiv (HEVC 1080p) bauen + hochladen")
    av.add_argument("event")
    av.add_argument("--4k", dest="vier_k", nargs="*", help="Shot-IDs, die in voller Auflösung bleiben")
    av.set_defaults(f=cmd_archivieren)
    kv = s.add_parser("ki-vorlage", help="Archiv-Clip als Higgsfield-Vorlage schneiden (SDR, ≤10 s)")
    kv.add_argument("event")
    kv.add_argument("shot", help="z. B. JP-261017-04")
    kv.add_argument("von", type=float)
    kv.add_argument("bis", type=float)
    kv.set_defaults(f=cmd_ki_vorlage)
    ks = s.add_parser("ki-shot", help="Higgsfield-Ergebnis als Shot JP-YYMMDD-KI-NN übernehmen")
    ks.add_argument("event")
    ks.add_argument("datei", help="lokale Datei oder Higgsfield-URL")
    ks.add_argument("--vorlage", help="Archiv-ID des echten Clips")
    ks.add_argument("--prompt", default="")
    ks.add_argument("--modell", default="?")
    ks.add_argument("--credits", type=float)
    ks.add_argument("--drive-id", help="Drive-ID, wenn das Ergebnis schon im Archiv liegt")
    ks.set_defaults(f=cmd_ki_shot)
    kl = s.add_parser("ki-liste", help="KI-Shots eines Events + verbrauchte Credits")
    kl.add_argument("event")
    kl.set_defaults(f=cmd_ki_liste)
    h = s.add_parser("hochladen")
    h.add_argument("event")
    h.add_argument("--vorschau", action="store_true", help="Vorschauen statt finaler Exporte")
    h.set_defaults(f=cmd_hochladen)
    a = p.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    sys.exit(main())
