"""Rendert Videos aus edits/<event>/schnitt.json.

Ein Video = Liste von Clips (Shot-ID + von/bis in Sekunden) + Texte + optional Musik.
Untertitel werden automatisch aus dem Transkript auf die Schnitt-Timeline gelegt.
Ein ffmpeg-Aufruf pro Video (kein Zwischen-Encoding → schnell, keine Generationsverluste).
"""
from pathlib import Path

from . import config
from .transcribe import load_words
from .util import read_json, run

FONT = "Inter Black"


def out_name(event_date: str, v: dict, suffix="") -> str:
    kind = "Reel" if v.get("format", "9:16") == "9:16" else "YouTube"
    return f"{event_date}_{v['fokus']}_{v['typ']}_{kind}_{v['nr']}_{v['titel']}{suffix}.mp4"


def _ass_time(t: float) -> str:
    t = max(t, 0)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def build_ass(v: dict, event_dir: Path, w: int, h: int, path: Path):
    vertical = h > w
    sub_size = int(h * (0.042 if vertical else 0.055))
    title_size = int(h * (0.062 if vertical else 0.08))
    kicker_size = int(h * (0.03 if vertical else 0.045))
    sub_margin = int(h * (0.27 if vertical else 0.08))   # Reels: über der UI-Leiste
    top_margin = int(h * (0.16 if vertical else 0.08))
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {w}", f"PlayResY: {h}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Sub,{FONT},{sub_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,"
        f"1,0,0,0,100,100,0,0,1,{max(sub_size // 9, 3)},2,2,60,60,{sub_margin},1",
        f"Style: Titel,{FONT},{title_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,"
        f"1,0,0,0,100,100,1,0,1,{max(title_size // 10, 4)},3,8,60,60,{top_margin},1",
        f"Style: Kicker,{FONT},{kicker_size},&H0000E5FF,&H00FFFFFF,&H00000000,&H64000000,"
        f"1,0,0,0,100,100,1,0,1,{max(kicker_size // 9, 3)},2,8,60,60,"
        f"{int(top_margin * 0.6)},1",
        f"Style: Mitte,{FONT},{title_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,"
        f"1,0,0,0,100,100,1,0,1,{max(title_size // 10, 4)},3,5,60,60,0,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    # Untertitel: Wörter jedes Clips auf die Ausgabe-Timeline umrechnen, 1–3 Wörter pro Einblendung
    if v.get("untertitel", True):
        t0 = 0.0
        max_words = v.get("woerter_pro_untertitel", 3 if vertical else 7)
        stamp = []
        for c in v["clips"]:
            for wd in load_words(event_dir, c["shot"]):
                if wd.get("event") or wd["e"] <= c["von"] or wd["s"] >= c["bis"]:
                    continue
                s = t0 + max(wd["s"], c["von"]) - c["von"]
                e = t0 + min(wd["e"], c["bis"]) - c["von"]
                stamp.append((s, e, wd["w"]))
            t0 += c["bis"] - c["von"]
        chunk = []
        for i, wd in enumerate(stamp):
            chunk.append(wd)
            nxt = stamp[i + 1] if i + 1 < len(stamp) else None
            brk = (len(chunk) >= max_words or nxt is None or nxt[0] - wd[1] > 0.5
                   or wd[2].endswith((".", "?", "!", ",")))
            if brk:
                end = min(nxt[0], chunk[-1][1] + 0.4) if nxt else chunk[-1][1] + 0.4
                text = " ".join(x[2] for x in chunk)
                if v.get("untertitel_gross", vertical):
                    text = text.upper()
                lines.append(f"Dialogue: 0,{_ass_time(chunk[0][0])},{_ass_time(end)},Sub,,0,0,0,,"
                             f"{_esc(text)}")
                chunk = []
    pos_style = {"oben": "Titel", "kicker": "Kicker", "mitte": "Mitte", "unten": "Sub"}
    sizes = {"Titel": title_size, "Kicker": kicker_size, "Mitte": title_size, "Sub": sub_size}
    for t in v.get("texte", []):
        style = pos_style.get(t.get("pos", "oben"), "Titel")
        fx = "{\\fad(120,120)}" if t.get("fade", True) else ""
        longest = max((len(x) for x in t["text"].split()), default=1)   # einzelne Wörter brechen nicht um
        fit = int(w * 0.88 / (0.68 * max(longest, 1)))     # grobe Breite pro Zeichen (Inter Black, Versalien)
        if fit < sizes[style]:
            fx += f"{{\\fs{fit}}}"
        lines.append(f"Dialogue: 1,{_ass_time(t['von'])},{_ass_time(t['bis'])},{style},,0,0,0,,"
                     f"{fx}{_esc(t['text'])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def resolve_framing(c: dict, meta: dict, event_dir: Path, work_dir: Path, w: int, h: int) -> dict:
    """Modus + Ausschnitt eines Clips. `modus`: auto (Standard) | crop | voll.
    `x`: Zahl (fest) oder "auto"/fehlend → Gesichtserkennung."""
    from . import reframe
    modus = c.get("modus", "auto")
    if modus == "voll":
        return {"modus": "voll"}
    if modus == "crop" and isinstance(c.get("x"), (int, float)):
        return {"modus": "crop", "x": c["x"], "y": c.get("y", 0.5)}
    if w > h and meta["breite"] >= meta["hoehe"]:      # 16:9 → 16:9: nichts zu tun
        return {"modus": "crop", "x": 0.5, "y": 0.5}
    zoom = float(c.get("zoom", 1.0))
    src = work_dir / "proxy" / f"{c['shot']}.mp4"
    if not src.exists():
        src = work_dir / "raw" / meta["datei"]
    key = f"{c['shot']}|{c['von']}|{c['bis']}|{zoom}|{w}x{h}"
    p = reframe.cached_plan(
        work_dir / "reframe.json", key,
        lambda: reframe.plan(reframe.analyze(src, c["von"], c["bis"], meta["breite"], meta["hoehe"]),
                             meta["breite"], meta["hoehe"], w, h, zoom))
    if modus == "crop" and p["modus"] == "voll":     # crop erzwungen, aber kein Gesicht → Mitte
        return {"modus": "crop", "x": 0.5, "y": 0.5}
    return p


def _clip_filter(i: int, c: dict, meta: dict, w: int, h: int, preview: bool, fr: dict) -> str:
    from .reframe import x_expr
    zoom = float(c.get("zoom", 1.0))
    chain = []
    if meta.get("hdr") and not preview:
        chain.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
                     "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv")
    if c.get("tempo"):
        chain.append(f"setpts=PTS/{c['tempo']}")
    luma = fr.get("luma", 128)
    if c.get("hell") or luma < 70:
        g = c.get("hell") or (1.6 if luma < 40 else 1.35)
        chain.append(f"eq=gamma={g}:saturation=1.15:contrast=1.05")
    if fr["modus"] == "voll":
        # Ganzes Bild mittig, dasselbe Video unscharf + etwas dunkler als Hintergrund
        bw, bh = max(w // 6, 2) // 2 * 2, max(h // 6, 2) // 2 * 2
        vz = float(c.get("vollzoom", c.get("zoom", 1.15)))   # Vollbild leicht größer als Bildbreite
        fw = int(w * vz) // 2 * 2
        chain.append(f"split=2[bg{i}][fg{i}];"
                     f"[bg{i}]scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},"
                     f"boxblur=10:3,eq=brightness=-0.06:saturation=1.1,scale={w}:{h}[bgb{i}];"
                     f"[fg{i}]scale={fw}:-2:flags=lanczos[fgs{i}];"
                     f"[bgb{i}][fgs{i}]overlay=(W-w)/2:(H-h)/2")
    else:
        # Bild füllend skalieren (cover), Ausschnitt nach Gesicht
        chain.append(f"scale=w='if(gt(a,{w}/{h}),-2,{w})*{zoom}':h='if(gt(a,{w}/{h}),{h},-2)*{zoom}'"
                     ":flags=lanczos")
        chain.append(f"crop={w}:{h}:'(iw-{w})*({x_expr(fr['x'])})':'(ih-{h})*{fr.get('y', 0.5)}'")
    chain.append(f"fps={config.FPS},setsar=1,format=yuv420p")
    v = f"[{i}:v]{','.join(chain)}[v{i}]"
    dur = c["bis"] - c["von"]
    a_chain = [f"atrim=0:{dur:.3f}", "asetpts=PTS-STARTPTS"]
    if c.get("tempo"):
        a_chain.append(f"atempo={c['tempo']}")
    if c.get("lautstaerke") is not None:
        a_chain.append(f"volume={c['lautstaerke']}dB")
    a = (f"[{i}:a]{','.join(a_chain)},aresample=48000,"
         f"aformat=channel_layouts=stereo[a{i}]" if meta.get("audio")
         else f"anullsrc=r=48000:cl=stereo,atrim=0:{dur:.3f}[a{i}]")
    return v + ";" + a


def render_video(event_dir: Path, work_dir: Path, v: dict, preview=False,
                 music_path: Path | None = None, suffix="") -> Path:
    shots = read_json(event_dir / "shots.json", {})
    spec = read_json(event_dir / "schnitt.json", {})
    vertical = v.get("format", "9:16") == "9:16"
    w, h = (config.REEL_W, config.REEL_H) if vertical else (config.YT_W, config.YT_H)
    if preview:
        w, h = w // 2, h // 2
    out_dir = work_dir / ("vorschau" if preview else "export")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / out_name(spec["datum"], v, suffix)
    ass = out_dir / (out.stem + ".ass")
    build_ass(v, event_dir, w, h, ass)

    cmd = ["ffmpeg", "-y", "-v", "error", "-stats"]
    for c in v["clips"]:
        meta = shots[c["shot"]]
        src = (work_dir / "proxy" / f"{c['shot']}.mp4") if preview else (work_dir / "raw" / meta["datei"])
        if not src.exists():
            raise SystemExit(f"Quelle fehlt: {src} – erst `vedit holen` ausführen.")
        cmd += ["-ss", f"{c['von']:.3f}", "-to", f"{c['bis']:.3f}", "-i", src]
    n = len(v["clips"])
    framing = [resolve_framing(c, shots[c["shot"]], event_dir, work_dir, w, h) for c in v["clips"]]
    for c, fr in zip(v["clips"], framing):
        print(f"  {c['shot']} {c['von']}–{c['bis']}: {fr['modus']}"
              f"{' (' + fr['grund'] + ')' if fr.get('grund') else ''}")
    parts = [_clip_filter(i, c, shots[c["shot"]], w, h, preview, fr)
             for i, (c, fr) in enumerate(zip(v["clips"], framing))]
    concat_in = "".join(f"[v{i}][a{i}]" for i in range(n))
    ass_arg = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    graph = ";".join(parts) + f";{concat_in}concat=n={n}:v=1:a=1[vc][ac];[vc]ass='{ass_arg}'[vo]"
    # Lautheit für Social: −14 LUFS
    graph += ";[ac]loudnorm=I=-14:TP=-1.5:LRA=11[av]"
    amap = "[av]"
    if music_path:
        m = v["musik"]
        cmd += ["-ss", f"{m.get('start', 0):.3f}", "-i", music_path]
        graph += (f";[{n}:a]volume={m.get('pegel', -12)}dB,aresample=48000,"
                  f"aformat=channel_layouts=stereo[mu];[av][mu]amix=inputs=2:duration=first:"
                  f"normalize=0[amx]")
        amap = "[amx]"
    cmd += ["-filter_complex", graph, "-map", "[vo]", "-map", amap,
            "-c:v", "libx264", "-preset", "veryfast" if preview else config.PRESET,
            "-crf", "26" if preview else str(config.CRF), "-profile:v", "high",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "192k", out]
    run(cmd)
    ass.unlink(missing_ok=True)
    return out
