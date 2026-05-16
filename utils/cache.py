"""
cache.py — SHA256-keyed LLM response cache with TTL.

Prevents redundant Ollama calls for identical (prompt, model, system) triples.
Stored as JSON files in a cache directory. Supports TTL expiry and stats.

Usage:
    cache = ResponseCache()
    cached = cache.get(prompt="explain PCNA", model="gemma3:4b", system="be concise")
    if cached is None:
        result = agent.chat(prompt, system=system, stream=False, print_stream=False)
        cache.set(prompt, result, model="gemma3:4b", system=system)
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CacheEntry:
    key: str
    prompt_hash: str
    model: str
    response: str
    created_at: float
    ttl: float           # seconds, 0 = no expiry
    hits: int = 0

    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return time.time() - self.created_at > self.ttl

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "prompt_hash": self.prompt_hash,
            "model": self.model,
            "response": self.response,
            "created_at": self.created_at,
            "ttl": self.ttl,
            "hits": self.hits,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CacheEntry":
        return cls(**d)


class ResponseCache:
    """
    File-based LLM response cache.

    Each entry is stored as a JSON file named by SHA256 hash of
    (prompt + model + system). Supports per-entry TTL, hit counting,
    and cache statistics.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        default_ttl: float = 0,    # 0 = permanent
        max_entries: int = 1000,
    ) -> None:
        self.cache_dir = Path(cache_dir or Path.home() / ".holyclaude" / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(prompt: str, model: str, system: str) -> str:
        raw = f"{model}|{system}|{prompt}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(
        self,
        prompt: str,
        model: str = "gemma3:4b",
        system: str = "",
    ) -> Optional[str]:
        key = self._make_key(prompt, model, system)
        path = self._path(key)
        if not path.exists():
            self._misses += 1
            return None
        try:
            entry = CacheEntry.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            self._misses += 1
            return None

        if entry.is_expired():
            path.unlink(missing_ok=True)
            self._misses += 1
            return None

        entry.hits += 1
        path.write_text(json.dumps(entry.to_dict()), encoding="utf-8")
        self._hits += 1
        return entry.response

    def set(
        self,
        prompt: str,
        response: str,
        model: str = "gemma3:4b",
        system: str = "",
        ttl: Optional[float] = None,
    ) -> str:
        key = self._make_key(prompt, model, system)
        entry = CacheEntry(
            key=key,
            prompt_hash=key[:16],
            model=model,
            response=response,
            created_at=time.time(),
            ttl=ttl if ttl is not None else self.default_ttl,
        )
        self._path(key).write_text(json.dumps(entry.to_dict()), encoding="utf-8")
        self._maybe_evict()
        return key

    def delete(self, prompt: str, model: str = "gemma3:4b", system: str = "") -> bool:
        path = self._path(self._make_key(prompt, model, system))
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self) -> int:
        n = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
            n += 1
        return n

    def clear_expired(self) -> int:
        n = 0
        for f in self.cache_dir.glob("*.json"):
            try:
                entry = CacheEntry.from_dict(json.loads(f.read_text()))
                if entry.is_expired():
                    f.unlink()
                    n += 1
            except Exception:
                f.unlink()
                n += 1
        return n

    def _maybe_evict(self) -> None:
        entries = list(self.cache_dir.glob("*.json"))
        if len(entries) <= self.max_entries:
            return
        # Evict oldest by mtime
        entries.sort(key=lambda f: f.stat().st_mtime)
        for f in entries[:len(entries) - self.max_entries]:
            f.unlink(missing_ok=True)

    def stats(self) -> dict:
        entries = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in entries)
        return {
            "entries": len(entries),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(1, self._hits + self._misses), 3),
            "size_kb": round(total_size / 1024, 1),
            "cache_dir": str(self.cache_dir),
        }

    def cached(self, model: str = "gemma3:4b", system: str = "", ttl: Optional[float] = None):
        """Decorator: cache the return value of a function taking (prompt) as first arg."""
        def decorator(fn):
            def wrapper(prompt: str, *args, **kwargs):
                cached = self.get(prompt, model=model, system=system)
                if cached is not None:
                    return cached
                result = fn(prompt, *args, **kwargs)
                if isinstance(result, str):
                    self.set(prompt, result, model=model, system=system, ttl=ttl)
                return result
            return wrapper
        return decorator
