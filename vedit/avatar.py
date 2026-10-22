"""KI-Avatar-Swap (Workflow wie OpenArt-Tutorial, aber per fal.ai-API):

1. Standbild aus dem Shot + Avatar-Bild → Nano Banana Pro ersetzt die Person (Pose/Hintergrund bleiben).
2. Dieses Bild + Clip → Kling Motion Control: Avatar macht die Bewegungen aus dem Clip, Originalton bleibt.

Braucht FAL_KEY (fal.ai → Dashboard → Keys) im Environment. Kostet pro Lauf Credits –
deshalb erst `--nur-bild` prüfen, dann mit `--bild` das geprüfte Bild für das Video nehmen.
"""
import os
import urllib.request
from pathlib import Path

from .util import run

BILD_MODELL = "fal-ai/nano-banana-pro/edit"
VIDEO_MODELL = "fal-ai/kling-video/v2.6/standard/motion-control"
MAX_DAUER = {"video": 30.0, "image": 10.0}   # Kling-Limit je character_orientation

PROMPT = (
    "Replace the entire person in this image (image 1) with the person from image 2. "
    "Keep the exact same pose, body position, angle, framing, camera distance and background "
    "completely unchanged. Do not preserve any facial features, hair or likeness of the original "
    "person from image 1. This is a full person replacement, keeping only the pose and background."
)

SDR = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
       "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,")


def _fal():
    if not os.environ.get("FAL_KEY"):
        raise SystemExit("FAL_KEY fehlt – in claude.ai/code → Environment → Umgebungsvariablen eintragen.")
    try:
        import fal_client
    except ImportError:
        raise SystemExit("pip install fal-client")
    return fal_client


def _laden(url: str, ziel: Path) -> Path:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, ziel)
    return ziel


def clip_schneiden(src: Path, hdr: bool, von: float, bis: float, ziel: Path) -> Path:
    """SDR-H.264-Clip, max. 1080 px kurze Seite – das, was Kling als Bewegungsvorlage bekommt."""
    vf = (SDR if hdr else "") + "scale='if(lt(iw,ih),min(1080,iw),-2)':'if(lt(iw,ih),-2,min(1080,ih))',format=yuv420p"
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{von}", "-to", f"{bis}", "-i", src, "-vf", vf,
         "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", ziel])
    return ziel


def standbild(clip: Path, t: float, ziel: Path) -> Path:
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t}", "-i", clip, "-frames:v", "1", "-q:v", "2", ziel])
    return ziel


def bild_tauschen(frame: Path, avatar: Path, ziel: Path, prompt: str = PROMPT) -> Path:
    fal = _fal()
    urls = [fal.upload_file(str(frame)), fal.upload_file(str(avatar))]
    print("Nano Banana Pro: tausche Person …")
    res = fal.subscribe(BILD_MODELL, arguments={
        "prompt": prompt, "image_urls": urls, "num_images": 1,
        "aspect_ratio": "auto", "resolution": "2K", "output_format": "png"})
    return _laden(res["images"][0]["url"], ziel)


def video_bewegen(bild: Path, clip: Path, ziel: Path, ausrichtung="video", prompt="") -> Path:
    fal = _fal()
    args = {"image_url": fal.upload_file(str(bild)), "video_url": fal.upload_file(str(clip)),
            "character_orientation": ausrichtung, "keep_original_sound": True}
    if prompt:
        args["prompt"] = prompt
    print("Kling Motion Control: generiere Video (dauert ein paar Minuten) …")
    res = fal.subscribe(VIDEO_MODELL, arguments=args, with_logs=False)
    return _laden(res["video"]["url"], ziel)
