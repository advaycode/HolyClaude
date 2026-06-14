"""Live smoke test: builds a 20mm cube through the full backend stack and checks
the units round-trip via the bounding box. Requires Inventor to be open/available;
skips cleanly otherwise."""

import sys

import pytest

from cad_mcp import units

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Inventor is Windows-only")


@pytest.fixture(scope="module")
def be():
    from cad_mcp import state
    try:
        backend = state.backend()  # connects (attach or launch)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Inventor not available: {e}")
    return backend


def mm(v):
    return units.to_cm(v, "mm")


def test_build_cube(be):
    be.new_document("part", "smoke_cube")
    sk = be.create_sketch("xy", "base").name
    be.add_rectangle(sk, mm(0), mm(0), mm(20), mm(20), "rect")
    res = be.create_extrude(sk, mm(20), "new_body", "pos", 0.0, "block")
    assert res.ok

    bodies = be.list_bodies()
    assert len(bodies) == 1
    assert bodies[0].face_count == 6
    assert bodies[0].edge_count == 12

    bb = be.bounding_box(None)
    dims = bb.extra["dimensions_mm"]
    assert all(abs(d - 20.0) < 0.01 for d in dims), dims
