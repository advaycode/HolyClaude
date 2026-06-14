# Naming schema (for CADCopilot)

Match the convention of whatever Advay is editing — do not impose one style.

## Two registers Advay uses
1. **Structured robot BOM** (serious robots like 26MRB): `{ROBOT}-{SUBSYS}-{ITEM} Description`
   e.g. `26MRB-200-006 1in ID Stub Roller`. Item index is zero-padded 3 digits.
   Subsystem-by-hundreds: `000` top · `100` drivetrain · `110` bumpers · `121` swerve ·
   `200` intake · `300` transfer · `400` tower · `500` shooter · `800` endgame ·
   `900` electronics · `1000` machining.
2. **Loose shorthand for one-offs**: `45 t.ipt`, `50t gears.iam`, `puly 20t.ipt`.
   Trailing/leading `t`/`T` = teeth. `puly` = pulley (his spelling).

## Rules for the copilot
- **Preserve Advay's spellings** in file/part names (`puly`, `Gaurd`, `Batery`) — never
  auto-correct.
- Symmetric parts get `Right` / `Left` / `Mirror` suffixes.
- `OldVersionsToKeepOnSave = 1` → `*.0001.ipt` shadow files in `OldVersions\` are NOT
  live parts; ignore them.
- **Entity names inside the MCP** are semantic and stable: bodies `Body_*`, sketches
  `Sketch_*`, features `Feature_<Op>_NNN`, faces `Face_<type>_NNN`, edges
  `Edge_<type>_NNN`. Always create with a name and reference by that name; never trust
  raw Inventor indices across a recompute (re-run `list_faces`/`list_edges` after a
  feature that changes the body).
