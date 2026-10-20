import json
import shlex
import subprocess
import sys
from pathlib import Path


def run(cmd, check=True, capture=False):
    """Führt ein Kommando aus; zeigt es vorher an."""
    print("$ " + " ".join(shlex.quote(str(c)) for c in cmd), file=sys.stderr)
    return subprocess.run([str(c) for c in cmd], check=check, text=True,
                          capture_output=capture)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fmt_ts(sec: float) -> str:
    m, s = divmod(max(sec, 0.0), 60)
    return f"{int(m)}:{s:04.1f}"
