"""Live-validate the new breadth batch: sketch geometry, physical props, iProps,
assembly constraints + joints."""
import os, sys, traceback
sys.path.insert(0, r"C:\Users\advay\Obsidian\CADCopilot\src")
from cad_mcp import state, units, config
def mm(v): return units.to_cm(v, "mm")
be = state.backend()


def sec(t, fn):
    print(f"\n=== {t} ===", flush=True)
    try:
        fn(); print("OK")
    except Exception:
        print("FAIL:", traceback.format_exc().splitlines()[-1])


def sketch_geom():
    be.new_document("part", "b2_sketch")
    # polygon -> extrude (validates closed profile)
    sp = be.create_sketch("xy", "poly").name
    be.add_polygon(sp, 6, [mm(0), mm(0)], mm(15), True, "hex")
    r = be.create_extrude("poly", mm(5), "new_body", "pos", 0.0, "hexbody")
    print("  hexagon extruded:", r.ok)
    # slot -> extrude (validates closure)
    ss = be.create_sketch("xz", "slot").name
    be.add_slot(ss, [mm(-20), mm(40)], [mm(20), mm(40)], mm(8), "sl")
    r2 = be.create_extrude("slot", mm(4), "new_body", "pos", 0.0, "slotbody")
    print("  slot extruded:", r2.ok)
    # arc, ellipse, spline just-add
    sa = be.create_sketch("yz", "misc").name
    be.add_arc(sa, [mm(0), mm(0)], [mm(10), mm(0)], [mm(0), mm(10)], "a")
    be.add_ellipse(sa, [mm(40), mm(0)], [1, 0], mm(12), mm(6), "e")
    be.add_spline(sa, [[mm(0), mm(30)], [mm(10), mm(40)], [mm(25), mm(32)], [mm(35), mm(45)]], "s")
    print("  arc+ellipse+spline added")
sec("sketch geometry", sketch_geom)


def props():
    be.new_document("part", "b2_props")
    sk = be.create_sketch("xy", "s").name
    be.add_rectangle(sk, mm(0), mm(0), mm(30), mm(20), "r")
    be.create_extrude(sk, mm(10), "new_body", "pos", 0.0, "blk")
    pp = be.physical_properties()
    print("  physical:", pp)
    be.set_iproperty("Part Number", "26MRB-999-001")
    be.set_iproperty("Description", "test block")
    ip = be.get_iproperties()
    print("  iprops:", {k: ip[k] for k in ("part_number", "description")})
    assert ip["part_number"] == "26MRB-999-001"
sec("physical + iproperties", props)


def material():
    be.new_document("part", "b2_mat")
    sk = be.create_sketch("xy", "s").name
    be.add_rectangle(sk, mm(0), mm(0), mm(20), mm(20), "r")
    be.create_extrude(sk, mm(20), "new_body", "pos", 0.0, "blk")
    r = be.set_material("Aluminum 6061")
    print("  ", r.message)
sec("set_material", material)


def assembly_mate_joint():
    be.close_all_documents(False)   # release locks from prior probe runs (no Inventor restart)
    out = str(config.ensure_work_dir())
    cube = os.path.join(out, "b2_cube.ipt")
    be.new_document("part", "b2_cube")
    sk = be.create_sketch("xy", "s").name
    be.add_rectangle(sk, mm(0), mm(0), mm(20), mm(20), "r")
    be.create_extrude(sk, mm(20), "new_body", "pos", 0.0, "cube")
    be.save_document(cube)

    # --- constraint in its own assembly ---
    be.new_document("assembly", "b2_asm_c")
    o1 = be.insert_component(cube, "base", [0, 0, 0], [0, 0, 0], True).name
    o2 = be.insert_component(cube, "top", [mm(40), 0, 0], [0, 0, 0], False).name
    f1 = be.list_occurrence_faces(o1)
    f2 = be.list_occurrence_faces(o2)
    print(f"  occ faces: {len(f1)} / {len(f2)}")
    p1 = next(f for f in f1 if f.surface_type == "planar")
    p2 = next(f for f in f2 if f.surface_type == "planar")
    c = be.add_constraint("flush", p1.name, p2.name, 0.0, "flush1")
    print("  constraint:", c.ok, c.message)

    # --- joint in a SEPARATE assembly (avoid over-constraining the same pair) ---
    be.new_document("assembly", "b2_asm_j")
    j1 = be.insert_component(cube, "jbase", [0, 0, 0], [0, 0, 0], True).name
    j2 = be.insert_component(cube, "jtop", [mm(40), 0, 0], [0, 0, 0], False).name
    jf1 = be.list_occurrence_faces(j1)
    jf2 = be.list_occurrence_faces(j2)
    j = be.add_joint("rigid", jf1[0].name, jf2[0].name, "j1")
    print("  joint:", j.ok, j.message)
sec("assembly constraint + joint", assembly_mate_joint)

print("\nDONE")
