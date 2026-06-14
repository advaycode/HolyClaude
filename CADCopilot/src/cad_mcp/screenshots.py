"""Viewport screenshot post-processing: downscale + compress so the image the
agent sees stays small enough not to blow the token budget."""

from __future__ import annotations

import io

from PIL import Image


def downscale(png_bytes: bytes, max_dim: int = 1024) -> bytes:
    """Return PNG bytes scaled so the longest side <= max_dim."""
    img = Image.open(io.BytesIO(png_bytes))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()
