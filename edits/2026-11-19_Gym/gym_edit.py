"""Gym Hard Edit – beat-synchron auf 'Body' (143.5 BPM). Aufruf: python3 gym_edit.py <work_dir> <out_dir> [w h]"""
import subprocess, sys
from pathlib import Path

W, H = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (1080, 1920)
work, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
raw = work / "raw"
SRC = {
    "A": raw / "31b69a6ddb394b9ea23c0611a2d467da.mov",      # JP-260804-01 Spinde, graded
    "B": raw / "F4239487-7F22-4B68-9FF7-B435464DC241.mp4",  # JP-261116-01 Silhouette Türrahmen
    "C": raw / "CD8CE606-95AC-466F-BA4D-062C4D7B88FC.mp4",  # JP-261118-01 Spiegel-Selfie
}
SONG = Path(sys.argv[1]).parent / "musik" / "Body.mp3"
SONG_START = 4.50          # Drop (Beat 9.10) landet bei 4.60 im Edit
BEAT = 60 / 143.55
FPS = 30

# (quelle, von, dauer, zoom, cx, cy, punch, flash, grade, tempo)
INTRO = 4.60
segs = [
    ("B", 1.30, INTRO, 2.0, 0.55, 0.50, 0.0, 0, "dark", 1.0),   # Shirt geht über den Kopf … (Push-in)
    ("B", 6.00, 6 * BEAT, 2.0, 0.55, 0.50, 0.25, 1, "dark", 1.0),  # DROP: Shirt aus
    ("A", 8.45, 4 * BEAT, 1.0, 0.5, 0.5, 0.12, 1, "cine", 1.0),   # Blick nach oben, Brust
    ("A", 7.00, 2 * BEAT, 1.0, 0.5, 0.5, 0.12, 1, "cine", 1.0),   # Rücken / Flex
    ("A", 10.00, 2 * BEAT, 1.1, 0.5, 0.5, 0.12, 1, "cine", 1.0),  # Handschuhe richten
    ("A", 5.10, 2 * BEAT, 1.0, 0.5, 0.5, 0.12, 1, "cine", 1.0),   # Cinema-Bars Pose
    ("B", 9.00, 2 * BEAT, 2.0, 0.55, 0.50, 0.12, 0, "dark", 1.0), # Flex im Türrahmen
    ("B", 10.30, 2 * BEAT, 1.6, 0.55, 0.50, 0.12, 1, "dark", 1.0),
    ("A", 8.45, 4 * BEAT, 1.0, 0.5, 0.5, 0.0, 0, "cine", 0.5),    # Outro Slow-Mo
]

GRADE = {
    "dark": "eq=contrast=1.12:brightness=0.02:saturation=0.85:gamma=1.08",
    "cine": "eq=contrast=1.06:saturation=0.9",
    "mirror": "eq=contrast=1.15:brightness=-0.06:saturation=0.75:gamma=0.92,"
              "colorbalance=rs=-0.04:bs=0.05:rm=-0.02:bm=0.03",
}
LOOK = "vignette=PI/4.5,noise=alls=6:allf=t"   # leichte Vignette + Korn für alle

parts = []
for i, (k, von, dur, zoom, cx, cy, punch, flash, grade, tempo) in enumerate(segs):
    src_dur = dur * tempo
    push = 0.08 if i == 0 else 0.0                       # langsamer Push-in im Intro
    z = f"({zoom}*(1+{push}*t/{dur:.3f})*(1+{punch}*exp(-t/0.14)))"
    vf = [
        f"setpts=(PTS-STARTPTS)/{tempo}",
        f"fps={FPS}",
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
        f"scale=w='trunc({W}*{z}/2)*2':h='trunc({H}*{z}/2)*2':eval=frame:flags=bicubic",
        f"crop={W}:{H}:x='(iw-{W})*{cx}':y='(ih-{H})*{cy}'",
        GRADE[grade], LOOK, "format=yuv420p",
    ]
    if punch and i == 1:   # Drop: kurzer Shake
        vf.insert(5, f"crop={W - 40}:{H - 70}:x='20+18*sin(t*90)*exp(-t/0.25)':y='35+30*cos(t*77)*exp(-t/0.25)',scale={W}:{H}")
    if flash:
        vf.append(f"fade=in:st=0:d=0.12:color=white")
    if i == len(segs) - 1:
        vf.append(f"fade=out:st={dur - 1.0:.3f}:d=1.0")
    if i == 0:
        vf.append("fade=in:st=0:d=0.5")
    p = out / f"seg{i:02d}.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{von:.3f}", "-t", f"{src_dur:.3f}", "-i", str(SRC[k]),
           "-an", "-vf", ",".join(vf), "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium",
           "-crf", "17", "-r", str(FPS), str(p)]
    subprocess.run(cmd, check=True)
    parts.append(p)

lst = out / "list.txt"
lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
total = sum(s[2] for s in segs)
silent = out / "stumm.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                "-c", "copy", str(silent)], check=True)
name = "2026-11-19_Gym_HardEdit_Reel_01_Body"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent),
                "-ss", f"{SONG_START}", "-t", f"{total:.3f}", "-i", str(SONG),
                "-filter_complex", f"[1:a]afade=t=in:d=0.3,afade=t=out:st={total - 1.5:.3f}:d=1.5,"
                "loudnorm=I=-14:TP=-1.5:LRA=11[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                "-movflags", "+faststart", "-shortest", str(out / f"{name}_PREVIEW.mp4")], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-f", "lavfi", "-t", f"{total:.3f}",
                "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-c:a", "aac", "-movflags", "+faststart", "-shortest",
                str(out / f"{name}_OHNE-MUSIK.mp4")], check=True)
print("fertig", round(total, 2), "s")
