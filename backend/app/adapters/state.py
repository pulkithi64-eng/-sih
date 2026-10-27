"""Persistent source state: online/offline flags (admin toggle) and call statistics.

Stored in backend/data/sources_state.json (override with VERISENSE_SOURCES_STATE). Shared by the adapters and the
simulated authority services so that toggling a source offline makes both the adapter and /mock/* report an outage.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

_DEFAULT = Path(__file__).resolve().parents[2] / "data" / "sources_state.json"
_lock = threading.RLock()


def _path() -> Path:
    return Path(os.environ.get("VERISENSE_SOURCES_STATE", str(_DEFAULT)))


def load() -> dict:
    p = _path()
    with _lock:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                data.setdefault("online", {})
                data.setdefault("stats", {})
                return data
            except (OSError, ValueError):
                pass
        return {"online": {}, "stats": {}}


def _save(data: dict) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    for _ in range(5):
        try:
            os.replace(tmp, p)
            return
        except PermissionError:  # Windows: reader holds the file briefly
            time.sleep(0.05)
    tmp.unlink(missing_ok=True)


def is_online(source_id: str) -> bool:
    return bool(load()["online"].get(source_id, True))


def set_online(source_id: str, online: bool) -> None:
    with _lock:
        data = load()
        data["online"][source_id] = bool(online)
        _save(data)


def record_call(source_id: str, latency_ms: float | None, success: bool) -> None:
    with _lock:
        data = load()
        st = data["stats"].setdefault(source_id, {"calls": 0, "successes": 0, "lastLatencyMs": None, "lastCheckedAt": None})
        st["calls"] += 1
        st["successes"] += 1 if success else 0
        if latency_ms is not None:
            st["lastLatencyMs"] = round(latency_ms, 1)
        st["lastCheckedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _save(data)


def stats(source_id: str) -> dict:
    return load()["stats"].get(source_id, {})
