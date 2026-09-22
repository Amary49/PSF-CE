from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import re
import tempfile


def safe_name(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(text)).strip("_")
    return s or "item"


def stable_hash(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def atomic_json_dump(obj, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
