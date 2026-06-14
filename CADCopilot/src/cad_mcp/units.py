"""The single unit-conversion authority.

Inventor and Fusion both store length in CENTIMETRES and angles in RADIANS. The
MCP tool layer accepts human units (default per session: inch for FRC, mm for FTC)
and converts here before calling a backend. Measurements coming back are in mm.
"""

from __future__ import annotations

import math

# centimetres per unit
_LEN_TO_CM = {
    "mm": 0.1, "millimeter": 0.1, "millimetre": 0.1,
    "cm": 1.0, "centimeter": 1.0, "centimetre": 1.0,
    "m": 100.0, "meter": 100.0, "metre": 100.0,
    "in": 2.54, "inch": 2.54, '"': 2.54,
    "ft": 30.48, "foot": 30.48, "feet": 30.48, "'": 30.48,
    "thou": 0.00254, "mil": 0.00254,
}

_ALIASES = {"millimeters": "mm", "inches": "in", "centimeters": "cm", "meters": "m"}


def _norm(unit: str) -> str:
    u = (unit or "").strip().lower()
    u = _ALIASES.get(u, u)
    if u not in _LEN_TO_CM:
        raise ValueError(f"Unknown length unit {unit!r}. Use mm, cm, m, in, ft, thou.")
    return u


def to_cm(value: float, unit: str = "mm") -> float:
    """Convert a user length to Inventor/Fusion internal centimetres."""
    return float(value) * _LEN_TO_CM[_norm(unit)]


def from_cm(value_cm: float, unit: str = "mm") -> float:
    """Convert internal centimetres to a user length."""
    return float(value_cm) / _LEN_TO_CM[_norm(unit)]


def cm_to_mm(value_cm: float) -> float:
    return float(value_cm) * 10.0


def mm_to_cm(value_mm: float) -> float:
    return float(value_mm) / 10.0


def deg_to_rad(deg: float) -> float:
    return math.radians(float(deg))


def rad_to_deg(rad: float) -> float:
    return math.degrees(float(rad))


def point_to_cm(pt, unit: str = "mm") -> list[float]:
    """Convert a 2- or 3-element user-unit point to a cm list."""
    return [to_cm(c, unit) for c in pt]
