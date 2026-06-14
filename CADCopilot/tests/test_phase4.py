"""Phase 4: save a part, build an assembly, insert components by path and by library
query, ground one. Requires Inventor; skips otherwise."""

import os
import sys
import pytest

from cad_mcp import units, index, config

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


def test_assembly_insert_and_ground(be):
    out = str(config.ensure_work_dir())
    part_path = os.path.join(out, "asm_cube.ipt")

    # build + save a cube part
    be.new_document("part", "asm_cube")
    sk = be.create_sketch("xy", "s").name
    be.add_rectangle(sk, mm(0), mm(0), mm(20), mm(20), "r")
    be.create_extrude(sk, mm(20), "new_body", "pos", 0.0, "cube")
    be.save_document(part_path)
    assert os.path.exists(part_path)

    # new assembly, insert two occurrences by path
    be.new_document("assembly", "asm_test")
    r1 = be.insert_component(part_path, "base", [0, 0, 0], [0, 0, 0], True)
    r2 = be.insert_component(part_path, "second", [mm(30), 0, 0], [0, 0, 0], False)
    assert r1.ok and r2.ok
    assert r2.data["occurrences"] == 2

    g = be.ground("second", True)
    assert g.ok


def test_insert_part_by_library_query(be):
    out = str(config.ensure_work_dir())
    # ensure the saved cube is indexed, then insert it by query (not full path)
    index.build_index([out], deep=False)
    be.new_document("assembly", "asm_lib")
    r = be.insert_component("asm_cube", "fromlib", [0, 0, 0], [0, 0, 0], True)
    assert r.ok
    assert r.data["occurrences"] == 1
