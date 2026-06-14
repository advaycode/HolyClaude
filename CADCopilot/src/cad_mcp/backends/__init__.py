"""Backend factory."""

from __future__ import annotations

from .base import Backend


def get_backend(name: str) -> Backend:
    """Instantiate the selected backend. Import is lazy so the server can start
    even when one engine's dependencies aren't reachable."""
    name = (name or "inventor").lower()
    if name == "inventor":
        from .inventor_backend import InventorBackend
        return InventorBackend()
    if name == "fusion":
        from .fusion_backend import FusionBackend
        return FusionBackend()
    raise ValueError(f"Unknown CAD_BACKEND {name!r}; expected 'inventor' or 'fusion'")
