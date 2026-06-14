# Build-anything playbook (for CADCopilot)

CADCopilot can build any part or assembly by composing the parametric tools. This is
the method — not a fixed script.

## The loop
1. **Plan** in the scratchpad: list parts/bodies, a named parameter table, and the
   feature order. For an assembly, list components and how they mate.
2. **Read context**: `cad://knowledge/inventor-context` (how Advay builds),
   `ftc-gobilda-conventions` + `dfm-3dprint-rules` when robot/printed.
3. **Set parameters** (`set_parameter`) so dimensions are editable, then build features
   driven by them.
4. **Build per part** with primitives: sketch → constrain → extrude/revolve/loft/sweep →
   hole/fillet/chamfer/shell → pattern/mirror. Name every entity.
5. **Inspect + self-correct** every 3–5 ops: `screenshot` + `list_faces`/`list_edges`/
   `measure`. Target later features by the names those return — never guess indices.
6. **Reuse** COTS: `search_parts` then `insert_part` (in an assembly) instead of
   modelling vendor parts; `run_ilogic_rule` to drive Advay's parametric library parts.
7. **Assemble**: `new_document('assembly')`, `insert_component` each part, `ground` the
   base, then `add_joint`/`add_constraint` to locate the rest.
8. **Export** when printing: `export('stl')` (binary, manifold). Apply
   `apply_print_clearance` to moving/mating dimensions first.

## Decomposing a complex multi-part build (worked example: a V8 engine for printing)
This is illustrative — the same decomposition applies to a gearbox, an intake, a turret.
1. Scratchpad a parameter table: bore, stroke, rod length, journal diameters,
   bank angle (90°), crank phases [0,90,180,270], wall, print clearance 0.3 mm.
2. Build each part in its own `new_document('part')`:
   - **Block**: extrude the outer prism → shell/pocket → `pattern_rectangular` the bolt
     grid → cylinder bores via `pattern` of a circle cut. Mirror one bank at the 90°
     `add_workplane('angle', ...)`.
   - **Piston**: revolve the profile (`add_axis_line` + `create_revolve`) → pin bore.
   - **Connecting rod**: extrude/loft the shank → big-end + small-end holes.
   - **Crankshaft**: main journals on the axis + offset rod journals. Phased journals
     are a **long pole** — use `execute_script` to loop the 4 phases (rotate a profile
     by the phase angle and revolve/extrude each journal), then fillet.
   - **Heads / valves / manifold**: valves = revolve; manifold runners = `create_loft`
     with **rails** (loft without rails is the #1 singularity failure) or `create_sweep`.
   - **Flywheel / oil pan**: revolve + `pattern_circular`; pan = loft/extrude + shell.
3. **Verify each part**: `screenshot`, `bounding_box` (split if larger than the bed),
   `measure` (e.g. bore > piston by the clearance), STL is manifold.
4. **Assemble or keep as printable parts**; cross-check counts (8 pistons, 8 rods,
   5 main journals) against the plan.

## When to use the escape hatch
Reach for `execute_script` only for geometry the typed tools can't express: phased/
indexed features (crank journals), math-driven point clouds, organic lofts needing
custom rails. It's transaction-wrapped (rolled back on error). Prefer typed tools
otherwise — they're inspected and named for you.
