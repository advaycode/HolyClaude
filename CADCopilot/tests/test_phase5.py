"""Phase 5 (Fusion) offline checks. The live Fusion path needs the add-in enabled
inside Fusion; here we verify backend selection and that a missing add-in yields a
clear, actionable error instead of a crash."""

import pytest

from cad_mcp.backends import get_backend
from cad_mcp.backends.base import CADError
from cad_mcp.backends.fusion_backend import FusionBackend


def test_backend_factory_selects_fusion():
    be = get_backend("fusion")
    assert isinstance(be, FusionBackend)


def test_fusion_connect_error_is_actionable():
    be = FusionBackend()
    with pytest.raises(CADError) as ei:
        be.connect()        # nothing listening on 9876 unless the add-in is enabled
    msg = str(ei.value).lower()
    assert "add-in" in msg or "fusion" in msg or "reach" in msg
    assert be.get_last_error()["ok"] is False


def test_unified_tool_layer_is_backend_agnostic():
    # the same tool functions exist regardless of backend; FusionBackend implements
    # the core surface (rare ops fall back to the escape hatch like Inventor)
    for m in ("new_document", "create_sketch", "create_extrude", "create_fillet",
              "list_bodies", "export", "eval_native", "screenshot_png"):
        assert callable(getattr(FusionBackend, m))
