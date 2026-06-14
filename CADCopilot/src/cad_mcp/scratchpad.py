"""A tiny JSON-backed scratchpad the agent uses to plan multi-part builds and hold
a parameter table across many tool calls. Stored beside generated CAD (never the
vault)."""

from __future__ import annotations

import json
from typing import Any

from . import config


def _path():
    return config.ensure_work_dir() / "scratchpad.json"


def _load() -> dict:
    p = _path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    _path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def update(key: str, value: Any) -> dict:
    data = _load()
    data[key] = value
    _save(data)
    return data


def get(key: str = "") -> Any:
    data = _load()
    return data.get(key) if key else data


def clear() -> None:
    _save({})
