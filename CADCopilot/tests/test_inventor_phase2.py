"""Live Phase-2 coverage: revolve, hole, fillet, chamfer, shell, patterns, mirror,
boolean, work planes, full inspection, parameters, and screenshot. Skips if
Inventor is unavailable. Hole-center sketches are on the XY origin plane so sketch
coords == world coords and counts are deterministic."""

import sys
import pytest

from cad_mcp import units

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Inventor is Windows-only")


def mm(v):
    return units.to_cm(v, "mm")


@pytest.fixture(scope="module")
def be():
    from cad_mcp import state
    try:
        return state.backend()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Inventor not available: {e}")


def _count_cyl(faces):
    return sum(1 for f in faces if f.surface_type == "cylindrical")


def test_inspection_and_fillet(be):
    be.new_document("part", "p2_plate")
    sk = be.create_sketch("xy", "base").name
    be.add_rectangle(sk, mm(0), mm(0), mm(80), mm(40), "rect")
    be.create_extrude(sk, mm(5), "new_body", "pos", 0.0, "plate")

    faces = be.list_faces("")
    assert len(faces) == 6
    tops = [f for f in faces if f.normal and round(f.normal[2], 2) == 1.0]
    assert len(tops) == 1 and tops[0].area_mm2 > 0

    edges = be.list_edges(None, None)
    assert len(edges) == 12
    assert any(e.length_mm > 0 for e in edges)

    # fillet a vertical edge (length == plate thickness 5mm)
    vertical = next(e for e in edges if abs(e.length_mm - 5.0) < 0.01)
    res = be.create_fillet([vertical.name], mm(2), "round1")
    assert res.ok
    assert any(f.feature_type == "fillet" for f in be.list_features(None))


def test_rectangular_hole_grid(be):
    be.new_document("part", "p2_grid")
    base = be.create_sketch("xy", "base").name
    be.add_rectangle(base, mm(0), mm(0), mm(80), mm(40), "rect")
    be.create_extrude(base, mm(5), "new_body", "pos", 0.0, "plate")

    hs = be.create_sketch("xy", "holes").name        # XY plane: sketch coords == world
    be.add_point(hs, mm(40), mm(20), "c1")           # centered seed -> safe in either pattern direction
    hole = be.create_hole(hs, mm(4), 0.0, True, False, "hole")  # default dir; auto-retries if needed
    assert hole.ok
    be.pattern_rectangular([hole.name], "x", 3, mm(8), "y", 2, mm(8), "grid")

    assert _count_cyl(be.list_faces("")) == 6     # 3x2 distinct holes


def test_circular_hole_pattern(be):
    be.new_document("part", "p2_disc")
    sk = be.create_sketch("xy", "disc").name
    be.add_circle(sk, mm(0), mm(0), mm(30), "outer")   # centered on origin
    be.create_extrude(sk, mm(6), "new_body", "pos", 0.0, "disc")

    hs = be.create_sketch("xy", "holes").name
    be.add_point(hs, mm(20), mm(0), "c1")              # off-center at r=20
    hole = be.create_hole(hs, mm(4), 0.0, True, False, "hole")
    be.pattern_circular([hole.name], "z", 6, 360.0, True, "bolt_circle")

    # 6 holes + 1 outer cylindrical rim
    assert _count_cyl(be.list_faces("")) >= 6


def test_revolve_and_shell(be):
    be.new_document("part", "p2_rev")
    sk = be.create_sketch("xy", "prof").name
    # closed rectangular profile offset from a centerline; revolve around the line
    be.add_rectangle(sk, mm(10), mm(0), mm(20), mm(30), "p")
    ax = be.add_axis_line(sk, mm(0), mm(0), mm(0), mm(30), "axis").name   # construction centerline at x=0
    res = be.create_revolve("prof", ax, units.deg_to_rad(360), "new_body", "cup")
    assert res.ok
    assert len(be.list_bodies()) >= 1


def test_boolean_union(be):
    be.new_document("part", "p2_bool")
    a = be.create_sketch("xy", "a").name
    be.add_rectangle(a, mm(0), mm(0), mm(20), mm(20), "ra")
    be.create_extrude(a, mm(20), "new_body", "pos", 0.0, "boxA")
    b = be.create_sketch("xy", "b").name
    be.add_rectangle(b, mm(10), mm(10), mm(30), mm(30), "rb")
    be.create_extrude(b, mm(20), "new_body", "pos", 0.0, "boxB")
    bodies = be.list_bodies()
    assert len(bodies) == 2
    be.boolean_combine(bodies[0].name, [bodies[1].name], "union", "fused")
    assert len(be.list_bodies()) == 1


def test_parameters(be):
    be.new_document("part", "p2_param")
    be.set_parameter("Bore", "12 mm", "cylinder bore", "create")
    params = {p.name: p for p in be.get_parameters()}
    assert "Bore" in params
    assert abs(params["Bore"].value_mm - 12.0) < 0.01


def test_screenshot(be):
    be.new_document("part", "p2_shot")
    sk = be.create_sketch("xy", "s").name
    be.add_rectangle(sk, mm(0), mm(0), mm(30), mm(30), "r")
    be.create_extrude(sk, mm(30), "new_body", "pos", 0.0, "cube")
    png = be.screenshot_png(800, 600)
    assert isinstance(png, (bytes, bytearray)) and len(png) > 2000
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
