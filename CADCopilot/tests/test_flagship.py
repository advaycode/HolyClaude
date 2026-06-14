"""Flagship 'build anything' end-to-end test — drives the backend exactly as the
agent would to build a real, printable goBILDA-style motor-mount bracket and a
multi-feature revolve part, then exports STL.

Marked `flagship` so it does NOT run in the default suite (it launches Inventor).
Run it attended:  pytest -m flagship -s
"""

import os
import sys
import pytest

from cad_mcp import units, config, ftc_constants

pytestmark = [
    pytest.mark.flagship,
    pytest.mark.skipif(sys.platform != "win32", reason="Inventor is Windows-only"),
]


def mm(v):
    return units.to_cm(v, "mm")


@pytest.fixture(scope="module")
def be():
    from cad_mcp import state
    try:
        return state.backend()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Inventor not available: {e}")


def test_gobilda_motor_mount_bracket(be):
    """Plate + goBILDA 8mm hole grid + 24mm motor bore + corner fillets -> STL."""
    g = ftc_constants.GOBILDA
    be.new_document("part", "Motor Mount Plate")

    # 96 x 48 mm plate, 6 mm thick (goBILDA-proportioned)
    base = be.create_sketch("xy", "plate").name
    be.add_rectangle(base, mm(0), mm(0), mm(96), mm(48), "outline")
    be.create_extrude(base, mm(6), "new_body", "pos", 0.0, "plate")

    # goBILDA 8mm hole grid (sketch on XY origin plane -> world coords)
    grid = be.create_sketch("xy", "grid").name
    for i in range(11):           # 11 x 5 holes at 8 mm, inset 8 mm
        for j in range(5):
            be.add_point(grid, mm(8 + i * g["grid_pitch_mm"]), mm(8 + j * g["grid_pitch_mm"]), "")
    be.create_hole(grid, mm(g["hole_dia_mm"]), 0.0, True, False, "gobilda_grid")

    # central motor bore (e.g. goBILDA/yellowjacket pilot)
    bore = be.create_sketch("xy", "bore").name
    be.add_point(bore, mm(48), mm(24), "c")
    be.create_hole(bore, mm(24), 0.0, True, False, "motor_bore")

    # round the four outer corners (target by edge length == plate thickness)
    edges = be.list_edges(None, None)
    verticals = [e.name for e in edges if abs(e.length_mm - 6.0) < 0.01]
    if verticals:
        be.create_fillet(verticals[:4], mm(4), "corners")

    bodies = be.list_bodies()
    assert len(bodies) == 1
    # 11*5 grid holes + 1 motor bore = 56 cylindrical faces (+ any fillet-created)
    cyl = sum(1 for f in be.list_faces("") if f.surface_type == "cylindrical")
    assert cyl >= 56

    out = os.path.join(str(config.ensure_work_dir()), "motor_mount.stl")
    r = be.export("stl", out, None, {})
    assert r.ok and os.path.getsize(out) > 1000
    print(f"\nFLAGSHIP: bracket built, {cyl} holes, STL {os.path.getsize(out)} bytes -> {out}")


def test_revolved_pulley_blank(be):
    """Revolve a stepped pulley blank around a centerline + bore -> proves the
    revolve/axis-line path the agent uses for shafts/pulleys/pistons."""
    be.new_document("part", "puly blank")     # preserve Advay's 'puly' spelling style
    sk = be.create_sketch("xy", "prof").name
    # L-profile: hub + flange, offset from the centerline at x=0
    be.add_line(sk, [[mm(4), mm(0)], [mm(16), mm(0)], [mm(16), mm(4)],
                     [mm(8), mm(4)], [mm(8), mm(20)], [mm(4), mm(20)]], True, "p")
    ax = be.add_axis_line(sk, mm(0), mm(0), mm(0), mm(20), "axis").name
    r = be.create_revolve("prof", ax, units.deg_to_rad(360), "new_body", "blank")
    assert r.ok
    bb = be.bounding_box(None)
    assert bb.extra["dimensions_mm"][2] > 19  # ~20 mm tall
    print(f"\nFLAGSHIP: pulley blank revolved, bbox {bb.extra['dimensions_mm']}")
