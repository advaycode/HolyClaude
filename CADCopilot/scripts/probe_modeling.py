"""Live-validate the fork's loft/sweep/coil/spur_gear via the backend."""
import sys, traceback
sys.path.insert(0, r"C:\Users\advay\Obsidian\CADCopilot\src")
from cad_mcp import state, units
def mm(v): return units.to_cm(v, "mm")
be = state.backend()


def sec(t, fn):
    print(f"\n=== {t} ===", flush=True)
    try:
        fn(); print("OK")
    except Exception:
        print("FAIL:", traceback.format_exc().splitlines()[-1])


def loft():
    be.new_document("part", "m_loft")
    s1 = be.create_sketch("xy", "s1").name
    be.add_circle(s1, mm(0), mm(0), mm(15), "c1")
    wp = be.add_workplane("offset", ["xy"], mm(30), "wp").name
    s2 = be.create_sketch(wp, "s2").name
    be.add_circle(s2, mm(0), mm(0), mm(6), "c2")
    r = be.create_loft([s1, s2], [], "new_body", "loft1")
    print("  ->", r.message, "bodies", len(be.list_bodies()))
sec("loft", loft)


def sweep():
    be.new_document("part", "m_sweep")
    path = be.create_sketch("xz", "path").name
    be.add_line(path, [[mm(0), mm(0)], [mm(0), mm(40)]], False, "pl")
    prof = be.create_sketch("xy", "prof").name
    be.add_circle(prof, mm(0), mm(0), mm(4), "pc")
    r = be.create_sweep("prof", "path", "new_body", 0.0, "sweep1")
    print("  ->", r.message, "bodies", len(be.list_bodies()))
sec("sweep", sweep)


def coil():
    be.new_document("part", "m_coil")
    prof = be.create_sketch("xz", "prof").name
    be.add_circle(prof, mm(12), mm(0), mm(1.5), "pc")     # offset from Z axis
    r = be.create_coil("prof", "z", mm(5), 4.0, "new_body", "spring")
    print("  ->", r.message, "bodies", len(be.list_bodies()))
sec("coil", coil)


def gear():
    be.new_document("part", "m_gear")
    r = be.create_spur_gear(20, mm(2.0), mm(6), mm(8), 20.0, "g20")
    print("  ->", r.message, r.data)
    print("  cyl faces:", sum(1 for f in be.list_faces("") if f.surface_type == "cylindrical"))
sec("spur_gear", gear)

def closed_poly():
    be.new_document("part", "m_poly")
    sk = be.create_sketch("xy", "L").name
    # L-shaped closed profile via add_line (tests chained-point fix)
    be.add_line(sk, [[mm(0), mm(0)], [mm(40), mm(0)], [mm(40), mm(10)],
                     [mm(10), mm(10)], [mm(10), mm(40)], [mm(0), mm(40)]], True, "Lp")
    r = be.create_extrude("L", mm(5), "new_body", "pos", 0.0, "Lbar")
    print("  -> extruded closed polyline:", r.ok, "bodies", len(be.list_bodies()))
sec("closed polyline profile", closed_poly)

print("\nDONE")
