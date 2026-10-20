"""Transkription mit Wort-Zeitstempeln.

- ElevenLabs Scribe (mit Sprecher-Erkennung + Audio-Events wie Lachen), wenn ELEVENLABS_API_KEY gesetzt ist
- sonst lokal faster-whisper (ohne Sprecher-Tags)
Ergebnis je Shot: edits/<event>/transkript/<ID>.json (Wörter) und eine kompakte transkript.txt
zum Lesen/Planen (auch am Handy gut lesbar).
"""
import json
import os
import subprocess
from pathlib import Path

from . import config
from .util import fmt_ts, read_json, write_json


def _scribe(wav: Path) -> list[dict]:
    out = subprocess.run(
        ["curl", "-sS", "--fail-with-body", "-X", "POST",
         "https://api.elevenlabs.io/v1/speech-to-text",
         "-H", f"xi-api-key: {os.environ['ELEVENLABS_API_KEY']}",
         "-F", "model_id=scribe_v1", "-F", "diarize=true", "-F", "tag_audio_events=true",
         "-F", "language_code=deu", "-F", f"file=@{wav}"],
        check=True, capture_output=True, text=True).stdout
    words = []
    for w in json.loads(out).get("words", []):
        if w.get("type") == "spacing":
            continue
        words.append({"w": w["text"].strip(), "s": round(w["start"], 2), "e": round(w["end"], 2),
                      "spk": w.get("speaker_id"), "event": w.get("type") == "audio_event"})
    return words


_model = None


def _whisper(wav: Path) -> list[dict]:
    global _model
    from faster_whisper import WhisperModel
    if _model is None:
        _model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    # WAV selbst lesen (16 kHz mono) – umgeht PyAV-Versionskonflikte
    import wave
    import numpy as np
    with wave.open(str(wav)) as f:
        audio = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float32) / 32768
    segs, _ = _model.transcribe(audio, language="de", word_timestamps=True,
                                vad_filter=True, beam_size=5)
    return [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2), "spk": None,
             "event": False}
            for seg in segs for w in (seg.words or [])]


def phrases(words: list[dict], gap=0.6, max_len=8) -> list[dict]:
    """Fasst Wörter zu Sätzen/Phrasen zusammen (Pause oder Sprecherwechsel trennt)."""
    out, cur = [], []
    for w in words:
        if cur and (w["s"] - cur[-1]["e"] > gap or w["spk"] != cur[-1]["spk"]
                    or len(cur) >= max_len * 3 or cur[-1]["w"].endswith((".", "?", "!"))):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return [{"s": p[0]["s"], "e": p[-1]["e"], "spk": p[0]["spk"],
             "text": " ".join(x["w"] for x in p)} for p in out]


def transcribe_event(event_dir: Path, work_dir: Path, shots: dict, force=False):
    tdir = event_dir / "transkript"
    tdir.mkdir(parents=True, exist_ok=True)
    engine = "scribe" if os.environ.get("ELEVENLABS_API_KEY") else "whisper"
    for sid, meta in shots.items():
        out = tdir / f"{sid}.json"
        if out.exists() and not force:
            continue
        if not meta.get("audio"):
            write_json(out, {"engine": None, "words": []})
            continue
        wav = work_dir / "proxy" / f"{sid}.wav"
        print(f"Transkribiere {sid} ({meta['dauer']} s) mit {engine} …")
        words = _scribe(wav) if engine == "scribe" else _whisper(wav)
        write_json(out, {"engine": engine, "words": words})
    write_overview(event_dir, shots)


def load_words(event_dir: Path, sid: str) -> list[dict]:
    return read_json(event_dir / "transkript" / f"{sid}.json", {"words": []})["words"]


def write_overview(event_dir: Path, shots: dict):
    lines = [f"# Transkript – {event_dir.name}", ""]
    for sid, meta in shots.items():
        lines.append(f"## {sid}  ({meta['datei']}, {meta['dauer']} s, "
                     f"{meta['breite']}x{meta['hoehe']}, {meta['aufgenommen'][:16]})")
        for p in phrases(load_words(event_dir, sid)):
            spk = f"{p['spk']}: " if p["spk"] else ""
            lines.append(f"{fmt_ts(p['s'])}–{fmt_ts(p['e'])}  {spk}{p['text']}")
        lines.append("")
    (event_dir / "transkript.txt").write_text("\n".join(lines), encoding="utf-8")
