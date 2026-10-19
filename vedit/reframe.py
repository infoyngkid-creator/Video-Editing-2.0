"""Reframing Querformat → Hochformat mit Gesichtserkennung (OpenCV YuNet).

Ansatz wie Google AutoFlip, nur schlank:
- Gesichter im Clip-Fenster mit ~4 fps erkennen (auf Proxy, sonst Original).
- Entscheiden: `crop` (Ausschnitt folgt dem Gesicht) oder `voll` (ganzes Bild mittig, Blur-Hintergrund).
  voll, wenn kein Gesicht, oder mehrere Leute, die nicht zusammen in den 9:16-Ausschnitt passen.
- Im crop-Modus: ruhig stehen, solange sich das Gesicht kaum bewegt; sonst geglätteter Schwenk.
  Gesicht wird nie an den Rand gesetzt, bei Zoom liegt es im oberen Drittel.
"""
import json
import subprocess
from pathlib import Path

import numpy as np

from . import config

MODEL = config.ROOT / "models" / "face_detection_yunet_2023mar.onnx"
FPS = 4
AW = 640                 # Analysebreite
MIN_FACE = 0.035         # Gesichter schmaler als 3,5 % der Bildbreite ignorieren (Hintergrund)
STILL = 0.06             # Bewegungsspanne (Anteil Bildbreite), bis zu der der Ausschnitt still steht
SMOOTH_S = 1.5           # Glättungsfenster für Schwenks
DEADZONE = 0.18          # halbe Totzone in Anteil der Ausschnittbreite
MAX_SPEED = 0.5          # max. Schwenk in Ausschnittbreiten pro Sekunde
_det = None


def _frames(src: Path, von: float, bis: float):
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{von:.3f}", "-to", f"{bis:.3f}", "-i", str(src),
         "-vf", f"fps={FPS},scale={AW}:-2", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        capture_output=True, check=True).stdout
    return out


def analyze(src: Path, von: float, bis: float, src_w: int, src_h: int) -> list[dict]:
    """Liefert pro Sample: t (relativ zum Clipstart) und Gesichter (cx, cy, w, h normiert, score)."""
    global _det
    import cv2
    ah = int(round(AW * src_h / src_w / 2) * 2)
    raw = _frames(src, von, bis)
    n = len(raw) // (AW * ah * 3)
    if _det is None:
        _det = cv2.FaceDetectorYN.create(str(MODEL), "", (AW, ah), 0.6, 0.3, 50)
    _det.setInputSize((AW, ah))
    samples = []
    for i in range(n):
        img = np.frombuffer(raw, np.uint8, AW * ah * 3, i * AW * ah * 3).reshape(ah, AW, 3)
        _, faces = _det.detect(img)
        fl = []
        for f in (faces if faces is not None else []):
            x, y, w, h, score = f[0], f[1], f[2], f[3], f[-1]
            if w / AW >= MIN_FACE:
                fl.append({"cx": (x + w / 2) / AW, "cy": (y + h / 2) / ah,
                           "w": w / AW, "h": h / ah, "score": float(score)})
        samples.append({"t": i / FPS, "faces": fl})
    return samples


def _smooth(vals, win):
    if len(vals) < 3:
        return vals
    k = max(1, int(win * FPS))
    pad = np.pad(np.array(vals, float), (k, k), mode="edge")
    ker = np.ones(2 * k + 1) / (2 * k + 1)
    return list(np.convolve(pad, ker, mode="valid"))


def plan(samples: list[dict], src_w: int, src_h: int, out_w: int, out_h: int, zoom=1.0) -> dict:
    """Entscheidet Modus + Ausschnitt. Rückgabe: {"modus": "voll"} oder
    {"modus": "crop", "x": float | [(t, x), …], "y": float}."""
    sh = out_h * zoom
    sw = sh * src_w / src_h
    if sw < out_w:   # Quelle schon schmaler als Ziel (Hochformat) → kein Reframing nötig
        return {"modus": "crop", "x": 0.5, "y": 0.5}
    crop_frac = out_w / sw           # Breite des Ausschnitts in Anteil der Quellbreite
    with_faces = [s for s in samples if s["faces"]]
    if len(with_faces) < max(2, 0.3 * len(samples)):
        return {"modus": "voll", "grund": "kein Gesicht"}

    # Pro Sample: Zielpunkt = Gruppe, wenn sie in den Ausschnitt passt, sonst größtes Gesicht
    group_fits, targets = 0, []
    for s in with_faces:
        fs = s["faces"]
        left = min(f["cx"] - f["w"] / 2 for f in fs)
        right = max(f["cx"] + f["w"] / 2 for f in fs)
        if right - left <= crop_frac * 0.9:
            group_fits += 1
            cx = (left + right) / 2
            cy = float(np.mean([f["cy"] for f in fs]))
        else:
            big = max(fs, key=lambda f: f["w"] * f["score"])
            cx, cy = big["cx"], big["cy"]
        targets.append((s["t"], cx, cy))
    multi = sum(1 for s in with_faces if len(s["faces"]) >= 2)
    if multi > 0.5 * len(with_faces) and group_fits < 0.5 * len(with_faces):
        return {"modus": "voll", "grund": "mehrere Personen"}

    def to_x(cx):     # Gesichtsmitte → Crop-Offset-Anteil, Gesicht nie am Rand
        off = cx * sw - out_w / 2
        return float(np.clip(off / (sw - out_w), 0, 1))

    ys = [t[2] for t in targets]
    y = 0.5
    if zoom > 1.0:   # Gesicht ins obere Drittel, nicht abschneiden
        cy = float(np.median(ys))
        y = float(np.clip((cy * sh - 0.38 * out_h) / (sh - out_h), 0, 1))
    xs = [t[1] for t in targets]
    if max(xs) - min(xs) <= STILL:
        return {"modus": "crop", "x": round(to_x(float(np.median(xs))), 3), "y": round(y, 3)}
    # Totzone: Ausschnitt steht, solange das Gesicht im mittleren Drittel des Ausschnitts bleibt;
    # sonst sanft nachführen (max. halbe Ausschnittbreite pro Sekunde), danach glätten.
    dead = crop_frac * DEADZONE
    speed = crop_frac * MAX_SPEED / FPS
    cur = float(np.median(xs[: max(1, FPS)]))
    path = []
    for cx in _smooth(xs, 0.5):
        diff = cx - cur
        if abs(diff) > dead:
            step = np.clip(diff - np.sign(diff) * dead, -speed, speed)
            cur += step
        path.append(cur)
    path = _smooth(path, SMOOTH_S)
    keys, last = [], None
    for (t, _, _), cx in zip(targets, path):
        xv = round(to_x(cx), 3)
        if last is None or abs(xv - last) > 0.015:
            keys.append((round(t, 2), xv))
            last = xv
    if len(keys) > 1 and max(k[1] for k in keys) - min(k[1] for k in keys) < 0.04:
        return {"modus": "crop", "x": float(np.median([k[1] for k in keys])), "y": round(y, 3)}
    return {"modus": "crop", "x": keys, "y": round(y, 3)}


def x_expr(keys) -> str:
    """Stückweise lineare Kurve als ffmpeg-Ausdruck über t."""
    if isinstance(keys, (int, float)):
        return f"{keys}"
    if len(keys) == 1:
        return f"{keys[0][1]}"
    expr = f"{keys[-1][1]}"
    for (t0, x0), (t1, x1) in reversed(list(zip(keys, keys[1:]))):
        seg = f"({x0}+({x1}-{x0})*(t-{t0})/{max(t1 - t0, 0.01)})"
        expr = f"if(lt(t\\,{t1})\\,{seg}\\,{expr})"
    return f"if(lt(t\\,{keys[0][0]})\\,{keys[0][1]}\\,{expr})"


def cached_plan(cache: Path, key: str, compute):
    data = json.loads(cache.read_text()) if cache.exists() else {}
    if key not in data:
        data[key] = compute()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data, indent=1))
    return data[key]
