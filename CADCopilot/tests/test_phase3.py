"""Phase 3: export, iLogic plumbing, DFM helpers, scratchpad, parts index, and the
guarded execute_script escape hatch."""

import os
import sys
import pytest

from cad_mcp import ftc_constants, scratchpad, index, tools, units

pytestmark_live = pytest.mark.skipif(sys.platform != "win32", reason="Inventor is Windows-only")


# ---- offline ----
def test_clearance_math():
    assert ftc_constants.clearance_for(8, "rotating")["adjusted_mm"] == 8.3
    assert ftc_constants.clearance_for(5, "press")["adjusted_mm"] == 4.95
    hs = ftc_constants.clearance_for(0, "heat_set")
    assert hs["diameter_mm"] == 4.1


def test_scratchpad_roundtrip():
    scratchpad.clear()
    scratchpad.update("plan", {"parts": ["block", "piston"]})
    scratchpad.update("bore_mm", 85.5)
    assert scratchpad.get("bore_mm") == 85.5
    assert scratchpad.get()["plan"]["parts"] == ["block", "piston"]


def test_code_guard():
    from cad_mcp.tools import _validate_code
    _validate_code("result = compdef.SurfaceBodies.Count")          # ok
    for bad in ("import os", "from sys import argv", "open('x')",
                "eval('1')", "x.__class__", "__import__('os')"):
        with pytest.raises(ValueError):
            _validate_code(bad)


def test_index_on_tempdir(tmp_path):
    for fn in ("2002-0180-0003.ipt", "claw 1.ipt", "45 t.ipt", "Tube 5.ipt", "drive.iam"):
        (tmp_path / fn).write_bytes(b"PK\x00 fake inventor binary iLogic")
    # point the index at the temp dir directly
    res = index.build_index([str(tmp_path)], deep=True)
    assert res["indexed"] == 5
    assert any(r["part_number"] == "2002-0180-0003" for r in index.search("2002"))
    assert any("claw" in r["name"].lower() for r in index.search("claw"))
    assert index.search("drive")[0]["kind"] == "assembly"


# ---- live ----
@pytest.fixture(scope="module")
def be():
    from cad_mcp import state
    try:
        return state.backend()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Inventor not available: {e}")


@pytestmark_live
def test_export_stl_step(be):
    from cad_mcp import config
    be.new_document("part", "p3_export")
    sk = be.create_sketch("xy", "s").name
    be.add_circle(sk, units.to_cm(0, "mm"), units.to_cm(0, "mm"), units.to_cm(10, "mm"), "c")
    be.create_extrude(sk, units.to_cm(10, "mm"), "new_body", "pos", 0.0, "cyl")
    out_dir = str(config.ensure_work_dir())
    stl = os.path.join(out_dir, "p3.stl")
    step = os.path.join(out_dir, "p3.stp")
    r1 = be.export("stl", stl, None, {})
    r2 = be.export("step", step, None, {})
    assert r1.ok and os.path.getsize(stl) > 84      # binary STL header + data
    assert r2.ok and os.path.getsize(step) > 100


@pytestmark_live
def test_escape_hatch_builds_geometry(be):
    be.new_document("part", "p3_escape")
    code = (
        "sk = compdef.Sketches.Add(compdef.WorkPlanes.Item(3))\n"
        "sk.SketchCircles.AddByCenterRadius(tg.CreatePoint2d(0, 0), cm(8))\n"
        "ed = compdef.Features.ExtrudeFeatures.CreateExtrudeDefinition("
        "sk.Profiles.AddForSolid(), C.kNewBodyOperation)\n"
        "ed.SetDistanceExtent(cm(12), C.kPositiveExtentDirection)\n"
        "compdef.Features.ExtrudeFeatures.Add(ed)\n"
        "result = 'cylinder built'\n"
    )
    out = be.eval_native(code, {})
    assert out == "cylinder built"
    assert len(be.list_bodies()) == 1
