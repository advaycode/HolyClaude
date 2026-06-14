# Design-for-3D-print rules (FDM, for CADCopilot)

Assume a 0.4 mm nozzle, 0.2 mm layers unless told otherwise. Bake these in when a
part is going to be printed (rollers, guards, claws, brackets, engine display parts).

## Walls & geometry
- **Min wall ≥ 1.2 mm** (≥3 perimeters). Thin flanges warp and peel.
- **Overhangs:** unsupported faces steeper than **45° from vertical** need support —
  prefer orientation/chamfers that avoid it.
- **Fillet load-bearing internal corners** (≥1 mm) to cut stress risers.
- **Bridging:** keep unsupported spans short (<10 mm) or add a chamfer.
- **Orientation:** put expected load in the X-Y plane; layer-adhesion (Z) is weakest.

## Fits & clearances (add to the NOMINAL size — use `apply_print_clearance`)
| Fit | Δ on diameter |
|---|---|
| press / interference | −0.05 mm |
| snug | +0.10 mm |
| clearance (slides) | +0.20 mm |
| rotating (spins free) | +0.30 mm |
| loose | +0.40 mm |

So a printed bore over an 8 mm REX shaft that must spin → drill ~8.3 mm.

## Hardware accommodations (M3)
- **Brass heat-set insert:** 4.0–4.2 mm hole, ≥4 mm deep (use 4.1 mm).
- **Captive nut trap:** hex pocket 5.6 mm across-flats, 6.6 mm across-corners,
  2.6 mm deep.
- **Clearance hole** for M3 bolt: 3.4 mm. **Tap/self-thread:** 2.5 mm.

## Manifold / export
- Export **binary STL** (or 3MF). The model must be **watertight/manifold** — close
  all bodies, avoid zero-thickness faces, union overlapping bodies before export.
- For large parts, **split for print** and add interlocking 1 mm pins/pockets
  (0.2 mm clearance) so halves register and glue cleanly.
- For moving display assemblies (e.g. an engine), give mating moving parts the
  **rotating (+0.3 mm)** clearance, or print-in-place with ≥0.3 mm gaps.
