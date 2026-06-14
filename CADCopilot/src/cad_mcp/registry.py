"""EntityRegistry — deterministic semantic naming for CAD entities.

CAD's "persistent naming problem": transient face/edge indices and default body
names shift on recompute, breaking later fillet/hole targeting. The registry
locks a stable semantic name (Body_Block_001, Edge_TopRim_004, Sketch_Profile_002)
to a live backend handle at creation, and stores a geometric *descriptor* so the
handle can be re-resolved after a recompute (Phase 2 uses the descriptor for
faces/edges). Tools always return + accept these names.

Handles are live COM/adsk proxies and are only ever touched on the backend's
worker thread, so storing them here is safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Entry:
    name: str
    kind: str                       # body | sketch | profile | feature | face | edge | workplane | axis | occurrence
    handle: Any = None              # live backend object (worker-thread only)
    descriptor: dict = field(default_factory=dict)  # geometric signature for re-resolution


class EntityRegistry:
    def __init__(self) -> None:
        self._items: dict[str, Entry] = {}
        self._counters: dict[str, int] = {}

    def reset(self) -> None:
        self._items.clear()
        self._counters.clear()

    def _auto_name(self, kind: str, hint: str = "") -> str:
        self._counters[kind] = self._counters.get(kind, 0) + 1
        n = self._counters[kind]
        base = kind.capitalize()
        if hint:
            hint = "".join(c for c in hint if c.isalnum() or c in "-_")
            return f"{base}_{hint}_{n:03d}"
        return f"{base}_{n:03d}"

    def register(self, kind: str, handle: Any, name: str = "", *,
                 hint: str = "", descriptor: Optional[dict] = None) -> str:
        """Register a handle and return its (possibly auto-generated) name.

        If ``name`` is provided but already taken, a numeric suffix is added so
        the requested intent is preserved without collision.
        """
        if not name:
            name = self._auto_name(kind, hint)
        elif name in self._items:
            i = 2
            while f"{name}_{i}" in self._items:
                i += 1
            name = f"{name}_{i}"
        self._items[name] = Entry(name=name, kind=kind, handle=handle,
                                  descriptor=descriptor or {})
        return name

    def get(self, name: str) -> Entry:
        if name not in self._items:
            raise KeyError(
                f"Unknown entity {name!r}. Known: {', '.join(sorted(self._items)) or '(none)'}"
            )
        return self._items[name]

    def resolve(self, name: str) -> Any:
        return self.get(name).handle

    def update_handle(self, name: str, handle: Any) -> None:
        self.get(name).handle = handle

    def remove(self, name: str) -> None:
        self._items.pop(name, None)

    def names(self, kind: str = "") -> list[str]:
        return [n for n, e in self._items.items() if not kind or e.kind == kind]

    def __contains__(self, name: str) -> bool:
        return name in self._items
