"""Diagnose hole-not-cutting via the real backend, step by step."""
import sys
sys.path.insert(0, r"C:\Users\advay\Obsidian\CADCopilot\src")
from cad_mcp import state, units
def mm(v): return units.to_cm(v, "mm")

be = state.backend()
be.new_document("part", "diag")
base = be.create_sketch("xy", "base").name
be.add_rectangle(base, mm(0), mm(0), mm(80), mm(40), "rect")
be.create_extrude(base, mm(5), "new_body", "pos", 0.0, "plate")
print("after plate: bodies", len(be.list_bodies()),
      "cyl", sum(1 for f in be.list_faces("") if f.surface_type == "cylindrical"),
      "faces", len(be.list_faces("")))

hs = be.create_sketch("xy", "holes").name
be.add_point(hs, mm(40), mm(20), "c1")
r = be.create_hole(hs, mm(4), 0.0, True, True, "hole")
print("hole result:", r.ok, r.message)
faces = be.list_faces("")
print("after hole: faces", len(faces),
      "cyl", sum(1 for f in faces if f.surface_type == "cylindrical"))
for f in be.list_features(None):
    print("   feature:", f.name, f.feature_type, "health", f.health, "suppressed", f.suppressed)

# now try flip=False variant in a fresh doc
be.new_document("part", "diag2")
base = be.create_sketch("xy", "base").name
be.add_rectangle(base, mm(0), mm(0), mm(80), mm(40), "rect")
be.create_extrude(base, mm(5), "new_body", "pos", 0.0, "plate")
hs = be.create_sketch("xy", "holes").name
be.add_point(hs, mm(40), mm(20), "c1")
r = be.create_hole(hs, mm(4), 0.0, True, False, "hole")  # flip=False -> -Z
faces = be.list_faces("")
print("flip=False: cyl", sum(1 for f in faces if f.surface_type == "cylindrical"))
print("DONE")
