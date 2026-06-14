"""Process-wide backend singleton + session unit default.

The backend is created and connected lazily on first CAD tool call, so the MCP
server starts instantly even when Inventor/Fusion isn't open yet.
"""

from __future__ import annotations

from typing import Optional

from . import config
from .backends import get_backend
from .backends.base import Backend

_backend: Optional[Backend] = None
_session_unit: str = config.CAD_UNIT_MODE  # "inch" (FRC default) | "mm" (FTC)


def backend() -> Backend:
    global _backend
    if _backend is None:
        be = get_backend(config.CAD_BACKEND)
        be.connect()
        _backend = be
    return _backend


def is_connected() -> bool:
    return _backend is not None


def session_unit() -> str:
    return _session_unit


def set_session_unit(unit: str) -> str:
    global _session_unit
    _session_unit = (unit or "inch").strip().lower()
    return _session_unit
