"""Kommandozeile: python -m vedit <befehl> …

Ablauf für ein neues Event:
  status                          Drive-Überblick: Eingang, Entwürfe, laufende Uploads
  neu <drive-ordner> <datum> <name>   Event anlegen, Footage holen, IDs, Proxys, Transkript
  vorschau <event> [nr …]         schnelle 540p-Vorschau aus Proxys
  render <event> [nr …]           finale Videos aus Originalen
  hochladen <event>               Exporte + Kontext.md + Schnittplan.txt nach 02_Entwürfe
"""
import argparse
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
            if not (wd / "raw" / datei).exists():
                if datei in ids:
                    drive.link_download(ids[datei], wd / "raw" / datei)
                else:
                    drive.download_file(f"{quelle}/{datei}", wd / "raw")
    for v in _select(ed, a.nr):
        mus = _music(wd, v)
        if mus:
            print(render.render_video(ed, wd, v, preview, mus, "_PREVIEW" if not preview else ""))
            print(render.render_video(ed, wd, v, preview, None, "_OHNE-MUSIK"))
        else:
            print(render.render_video(ed, wd, v, preview))


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
    h = s.add_parser("hochladen")
    h.add_argument("event")
    h.add_argument("--vorschau", action="store_true", help="Vorschauen statt finaler Exporte")
    h.set_defaults(f=cmd_hochladen)
    a = p.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    sys.exit(main())
