---
title: "Inventor Context — How Advay Builds"
type: knowledge-branch
scope: always-loaded
owner: Advay (FTC Masquerade 4997 / FRC builder)
cad: Autodesk Inventor (imperial, "Standard (in)" templates)
last_reviewed: 2026-06-13
status: BOOTSTRAP (filesystem-derived; awaiting deep COM enrichment)
---

# Inventor Context — How Advay Builds

> Auto-loaded brief for the Inventor CAD-copilot. Tells the AI how Advay's real designs are structured, which COTS ecosystems he builds around, his naming/units conventions, and the feature recipes he reuses. Derived from a read-only filesystem scan of `C:\Users\advay` (13,031 Inventor files, 16.87 GB). Exact dimensions, parameter values, and feature trees are NOT yet captured — see "TO BE ENRICHED."

## TL;DR for the copilot
- **Units: imperial (inches).** Every modern assembly is seeded from `Standard (in).iam`. Default new parts/assemblies to inch templates unless told otherwise.
- **Primary ecosystem: goBILDA** (4-4-4 part numbers like `2002-0180-0003`). Some WCP/Westcoast (`WR20W…`) and FRC swerve COTS (MK4N, Kraken, 8020). Design to goBILDA hole grids and shaft standards by default.
- **He hand-builds custom parts** (gears, pulleys, rollers, plates, tubes, claws) and drops COTS straight from vendor libraries. Match the convention of whichever he's editing.
- **Naming is loose-but-meaningful for one-offs** (`45 t.ipt`, `50t gears.iam`, `puly 20t.ipt`) and **strict structured for robot BOMs** (`26MRB-200-006 1in ID Stub Roller.ipt`). Mirror the surrounding folder's style.
- **He keeps `OldVersionsToKeepOnSave = 1`** → expect `*.0001.ipt` shadow files in `OldVersions\`. Never treat those as live parts.
- **3D printing is a first-class output** (161 `.stl`, 11 `.3mf` in one archive). Custom plastic parts (rollers, guards, claws) are print-targeted.

---

## 1. Project Map

Root authoring + curriculum lives under `C:\Users\advay\Documents\CacheCAD\` (project file: `CacheCad.ipj`, single-workspace, `UsingUniqueFilenames = Yes`). COTS and overflow live under `C:\Users\advay\Downloads\`.

### Authored robots (treat as Advay's design intent)
| Project | Path | Notes |
|---|---|---|
| **Masquerade 4997** (ACTIVE) | `C:\Users\advay\Documents\CacheCAD\Masquerade 4997 Cache Cad` | 1,510 files. Most recent edits (2026-04-27): `claw assemble.iam`, `claw 1.ipt`, `45 t.ipt`, `puly 20t.ipt`, `50t gears.iam`. Loose top-level naming. |
| **26MRB Minotaur Rebuilt, Rebuild** (ACTIVE) | `…\CacheCAD\26MRB Minotaur Rebuilt, Rebuild` | 375 files. Cleanest structured BOM. Subsystem folders `26MRB-000/100/200/300/400/500/800/900/1000`. The reference standard for how Advay organizes a serious robot. |
| **2026 Minotaur Rebuilt** (SUPERSEDED) | `…\CacheCAD\2026 Minotaur Rebuilt` | 1,183 files. Earlier iteration; 26MRB-Rebuild replaces it. |
| **Advay(1) personal archive** | `C:\Users\advay\Downloads\Advay(1)\Advay(1)` | 3,378 files. Sprawling sandbox: `Masq 25-26.ipj`, `IntakeV1/v2`, `ShooterV1`, `TransferV1`, `Turret`, `3DPrints`, `Advay_shooter_decode_2025`. Experiments + print masters live here. |
| **Telegram\Masq Robot** (team-shared) | `C:\Users\advay\Downloads\Telegram Desktop\Masq Robot` | 366 files. Holds the `Channel Generator` (parametric goBILDA U-channels). |

### Curriculum / training (NOT design intent — teaching scaffolds)
| Project | Path | Notes |
|---|---|---|
| 2026 FRC CAD Training | `…\CacheCAD\2026 FRC CAD Training` | Progressive exercises (Rocket/Plane/Car/Train/Dresser, WR20W intake). `Standard\3 - Parts with ILogic\Tube 1..5`. |
| 2024 Intro to CAD | `…\CacheCAD\2024 Intro to CAD` | Course w/ student folders (advay, Avaneesh_K, Calvin…). `3 - Parts with ILogic\Shaft-1..10`, `Tube-1..10`, plus `Generators Key.pptx/pdf`. |

### COTS / vendor libraries (drop-in, do not redesign)
| Library | Path | Files |
|---|---|---|
| FRC Parts Library | `…\CacheCAD\FRC Parts Library` | 1,870 |
| FTC Parts Library | `…\CacheCAD\FTC Parts Library` | 1,361 |
| VEX Parts Library | `…\CacheCAD\VEX Parts Library` | 1,532 |
| goBILDA downloads | scattered in `C:\Users\advay\Downloads\` (e.g. `2002-…`, `2305-…`, `26MIN-…`) + extracted `.STEP`/`.step` beside numbered folders | ~1,630 |

### Collaboration (peer teams — reference, not Advay's)
`Downloads\Telegram Desktop\Other Teams`: `masq ftc wheel`, `srijan cad`, `aravclankershooter`, `Midnight V2`, `SAR330`.

---

## 2. COTS Ecosystems & Implied Hardware Constraints

**goBILDA is the backbone.** Part numbers follow the **4-4-4 pattern** `AAAA-BBBB-CCCC`. Observed series → component class:
- `11xx` — structure / U-channel & frame (e.g. `1121-0010-0264` = 264mm U-channel)
- `12xx` — servos / servo brackets (`1201-0043-0002`)
- `13xx` — motors (`1311-0016-4008`)
- `15xx / 16xx` — motion: shafts, hubs, motors (`1516-4008-…`, `1611-0514-4008`, `1501-0006-0030`)
- `19xx` — bearings / pillow blocks (`1908-0025-0032`)
- `23xx` — gearmotors / gearboxes / drive (`2302-0014-0048`, `2319-4008-0030`)
- `20xx` — rollers / compliant wheels / misc (`2002-0180-0003`)
- `2025-…` — gear/hood-gear family used in shooters (`2025-300-21`)
- `26MIN-…` — goBILDA Minotaur kit parts (`26MIN-200-008 1in ID Stub Roller`)
- `36xx` — REX shafts / bearings (`3614-0014-0096`, 8mm REX)

**Implied constraints the copilot should respect:**
- **goBILDA hole grid:** 8mm pattern on goBILDA channel (and the goBILDA "GoRail/U-channel" mounting matrix). Custom plates that bolt to goBILDA must land on this grid.
- **Shafts:** goBILDA **8mm REX** (hex-ish) and round-bore stock; bores on Advay's custom rollers/pulleys are sized to these (e.g. "1in ID Stub Roller", "8mm REX").
- **Fasteners:** goBILDA **M3 / M4** hardware; goBILDA hubs and set-screw collars.
- **U-channel frame system:** goBILDA low-side and standard U-channel (240mm, 264mm, 288mm widths seen) is the structural default for FTC builds.

**FRC / Westcoast layer (Minotaur/26MRB):** swerve via **MK4N** (`26MRB-121-000 MK4N Swerve Corner Mount`), **Kraken** motors w/ **MAXPlanetary** (`26MRB-500-003 Kraken Max Planetary.iam`), **80/20** extrusion (`8020 Crash Bar`, `8020 Corner Bracket`), 2x1 box tubing, polycarb plates. **WR20W** = Westcoast Robotics 2020-spec-width drivetrain (training).

---

## 3. Naming & Units Conventions (observed)

**Units:** imperial. All assemblies seed from **`Standard (in).iam`** (appears in every modern `.iam`). Inch is the working unit; goBILDA metric COTS are consumed as-is.

**Two naming registers — match the surrounding folder:**

**(A) Structured robot BOM** — used in 26MRB (and the disciplined parts of Minotaur):
`{ROBOT}-{SUBSYS}-{ITEM} {Description}`
- Robot tag: `26MRB` (2026 Minotaur Rebuilt)
- Subsystem (hundreds): `000` rebuild/top, `100` drivetrain, `110` bumpers, `121` swerve, `200` intake, `300` transfer, `400` tower, `500` shooter, `800` endgame, `900` electronics, `1000` machining
- Item: zero-padded 3-digit running index (`-001`, `-002`…)
- Examples: `26MRB-200-006 1in ID Stub Roller.ipt`, `26MRB-500-012 24T Pulley.ipt`, `26MRB-100-016 Cross 2x1 Gusset.ipt`
- Mirror/right variants spelled out: `…Mirror`, `…Right`, `…Left`. Spelling is casual ("Gaurd", "Batery", "Complient") — preserve his spelling, don't silently "fix" it in filenames.

**(B) Loose shorthand** — used at the top level of Masquerade and in sandboxes:
- Gears by tooth count: **`45 t.ipt`**, **`50t gears.iam`** (note inconsistent spacing: "45 t" vs "50t")
- Pulleys: **`puly 20t.ipt`** ("puly" = pulley, his spelling)
- Generic/scratch: `claw 1.ipt`, `cam aj.ipt`, `super.iam`, `normal shooter.iam`, `stupidBigGear.ipt`
- COTS kept under their **raw goBILDA number**: `2002-0180-0003.ipt`, `2025-300-21.ipt`

**Tooth-count vocabulary:** trailing/leading `t` or `T` = teeth. `45 t`, `50t`, `20t`, `24T Pulley`, `60t Tensioned Belt`, `30T`, `90t x 48t` (gearbox ratio shorthand).

**Versioning:** Inventor's keep-1-old-version (`OldVersionsToKeepOnSave = 1`) produces `*.0001.ipt` in `OldVersions\` (e.g. `45 t.0001.ipt`, `claw 1.0001.ipt`). These are auto-backups, not parts. Manual major revs are folder-level (`IntakeV1`/`Intakev2`, `…REV2`, `Electronics V2`).

---

## 4. Part Archetypes & Feature Recipes

Each recipe describes the parametric approach the copilot should default to. (Exact dims pending COM pass.)

### Gears (spur)
- **Two paths in use:**
  1. **Design Accelerator (Spur Gear Generator)** → emits `Spur Gear11/12/21/22.ipt` into a `Design Accelerator\` subfolder, paired `Spur Gears1.iam`. Preferred for meshing pairs and correct involute geometry. `50t gears\Design Accelerator\2025-300-21.ipt` shows this in the Masquerade gear work.
  2. **Hand-modeled blanks** named by tooth count (`45 t.ipt`, `50t gears.iam`) for quick fits / 3D-printed gears.
- **Recipe:** define module/diametral pitch + tooth count → generate gear → on the blank face add **central bore** sized to shaft (8mm REX or round), **set-screw / hub bolt circle** (goBILDA pattern), optional **lightening pockets**, **chamfer** tooth tips for print/clearance.
- Defaults: spur, FTC mod-2 commonly (20T/30T pairs seen); name file by tooth count.

### Pulleys (timing / GT2-class)
- **Reference part: `puly 20t.ipt` — the one confirmed iLogic-parametric part in the active project.** Parameter vocabulary: **Teeth (=20), Pitch, Bore, Face Width, Module**, driven by a `Form 1` iLogic UI + `NumericParameterControlSpec` on `TeethNumber`.
- **Recipe:** parametric tooth profile revolve/extrude by `Teeth`×`Pitch`, `Face Width` extrude, central `Bore`, flanges optional, hub bolt pattern. Reuse `puly 20t.ipt` as the template for new pulleys; change `Teeth`.
- Belt naming by tooth count: `60t Tensioned Belt`, `24T Pulley Shooter`.

### Shafts (iLogic, training-origin)
- Template set: `2024 Intro to CAD\3 - Parts with ILogic\Shaft-1..10`. (Note: these specific files scanned as static outputs, but the **vocabulary and workflow** are the model Advay was taught and reuses.)
- **Recipe:** parametric stepped cylinder — `Length`, per-step `Diameter`, with REX/hex profile option, **retaining-ring grooves**, **chamfered ends**, **drilled/tapped ends** or set-screw flats. Size OD to goBILDA bearing IDs (8mm) and hub bores.
- Live custom shafts in robots: `26MRB-200-009 Pivot Shaft.ipt`, `26MRB-500-014 First Complient Shaft.ipt`.

### Tubes / Channels (iLogic + iFeature)
- **Round/box tube template set:** `Tube 1..5` (FRC training) / `Tube-1..10` (Intro). Parametric: `Length`, OD/wall (round, e.g. `.625in Round Tube`) or 2×1 box section, **end hole pattern**, **lightening**.
- **U-channel (goBILDA) — `Channel Generator\`:** `GoBilda 240mm U-Channel.ipt` and `…Low-Side U-Channel.ipt` are **iFeature-factory** (`IFeatureFactory`) parts: fixed length per file (240mm), **pre-parametrized goBILDA hole pattern**, low-side = reduced web height. Material implied **aluminum**.
- **Recipe (custom channel/tube):** sketch profile → extrude to `Length` → apply goBILDA-grid hole iFeature → mirror/pattern holes → fillet inside corners. For COTS channel, just place the vendor part; for custom, copy the generator part and edit length.
- Live: `26MRB-100-000 Drivetrain Boxtubing.ipt` (**material confirmed: Aluminum 6061**), `26MRB-200-005 Intake .625in Round Tube.ipt`.

### Claw plates / Polycarb plates (cut parts, current focus)
- Active subject: `claw 1.ipt` + `claw assemble.iam` (Masquerade, edited 2026-04-27).
- **Recipe:** single sketch on a flat → extrude to plate thickness (polycarb stock, ~1/4"/3/16") → **goBILDA/8mm hole grid** for mounts → **bore + bearing pocket** at pivot → **profile fillets** on outer edges → **lightening cutouts**. Symmetric parts get `…Right` / `…Mirror` twins.
- Pattern parts: `26MRB-200-001 Slap Down Polycarb Plate Right.ipt`, `…-008 Polycarb Roller`, `26MRB-500-008/010 Rack Gear Left/Right`.

### Mounting plates / brackets
- **Recipe:** flat plate → **bolt-circle / linear hole pattern on goBILDA-or-FRC grid** → mating bearing/motor pilot bore (e.g. Kraken/NEO pilot, MAXPlanetary) → corner fillets → standoff-tapped holes. Examples: `26MRB-500-001 Shooter Main Plate`, `26MRB-200-015 Motor Mount Plate`, `26MRB-121-000 MK4N Swerve Corner Mount`.

### Rollers (intake/shooter — frequently 3D-printed)
- Active: `26MIN-200-008 1in ID Stub Roller.ipt`, `26MRB-200-006 1in ID Stub Roller`, `…-008 Polycarb Roller`, `…-011 Hood Polycarb Roller`.
- **Recipe:** revolve a cylindrical body → **central bore = shaft + bearing** ("1in ID") → **hex/REX broach** or set-screw bosses at ends → optional surface tread/compliant feature → name by ID + role. Many exported to STL/3MF (`PulleyIntake.3mf`, `intakeWheels.stl`).

---

## 5. iLogic Usage Patterns & Parameter Vocabulary

- **Confirmed live iLogic part:** `puly 20t.ipt` — `iLogic` rules, `Form 1` UI, `NumericParameterControlSpec`, `TeethNumber`. This is Advay's working pattern for parametric COTS-mating parts.
- **Generator mindset (taught + reused):** "Shaft-1..10", "Tube 1..5 / Tube-1..10" come from a **Generators** lesson (`Generators Key.pptx`). Expect Advay to think in terms of *generate a family by changing one number*, not bespoke geometry each time.
- **Inventor Design Accelerator** for gears: `Spur Gear11/12/21/22` + `Spur Gears1/2.iam` under `Design Accelerator\`. Use it for meshing gear pairs.
- **iFeature factory** for vendor extrusions (goBILDA channels): `IFeatureFactory`, fixed length + canned `Holes` pattern.
- **Parameter vocabulary to prefer (match his terms):**
  - Gears/pulleys: `Teeth` / `TeethNumber`, `Pitch`, `Module` (or Diametral Pitch), `Bore`, `Face Width`
  - Shafts: `Length`, `Diameter` (per step), end/groove features
  - Tubes/channels: `Length`, `Profile Type` (standard vs low-side), `Mounting Holes`
- **No widespread User Parameters** detected — parametrics live as iLogic rule variables / Design Accelerator inputs. When adding parametrics, expose a small `Form` like `puly 20t`.

---

## 6. "Build Like Advay" Cheatsheet

When generating or editing parts, default to:
- **Template/units:** new part & assembly from **`Standard (in)`** (inches). Keep assemblies seeded from `Standard (in).iam`.
- **Ecosystem first:** if it bolts to existing structure, design to the **goBILDA 8mm hole grid**; for FRC, the **FRC/2x1 + 80/20** grid. Pull COTS from FRC/FTC/VEX libraries rather than modeling vendor parts.
- **Shafts/bores:** size to **8mm REX** and goBILDA bearing IDs; common roller bore "1in ID". M3/M4 fasteners.
- **Hole patterns:** linear/rectangular on the vendor grid; bolt circles for hubs; always pattern rather than place-one-by-one.
- **Fillets/chamfers:** chamfer gear tooth tips and shaft ends for printability; modest corner fillets on plates/brackets; round inside channel corners.
- **Materials:** structural = **Aluminum 6061** (confirmed on box tubing); flat mech parts = **polycarbonate**; printed rollers/guards/claws = **ABS/PLA** (`Generic` plastic). Set iProperties material accordingly.
- **Naming:** structured robot part → `{ROBOT}-{SUBSYS}-{ITEM} Description` (zero-padded); quick part → tooth-count shorthand (`45 t`, `puly 20t`). Symmetric → add `Right`/`Left`/`Mirror`. Don't auto-correct his spelling in filenames.
- **3D-print export:** custom plastic parts target **STL** (default) and **3MF**; orient & wall-thickness for FDM. Mechanical COTS-interface parts also kept as **STEP/STP** for sharing.
- **Versioning:** rely on Inventor `OldVersions\*.0001`; do major revs as new folders (`…V2`, `…REV2`). Ignore `*.NNNN.ipt` shadows as live geometry.
- **Subsystem-first assembly:** build `{ROBOT}-X00 Subsystem.iam` containers; roll up into `{ROBOT}-000`.

---

## 7. TO BE ENRICHED (deep COM indexing pass)

Filesystem scan can't read inside compressed OLE streams. The MCP's live-Inventor COM pass should add:
- **Exact feature trees** per part (sketch → extrude/revolve → pattern → fillet order) for each archetype; current recipes are inferred, not read.
- **Real parameter values & ranges:** `puly 20t` Pitch/Module/Bore/Face Width numbers; gear module + diametral pitch actually used; plate thicknesses; tube wall/OD; hole-grid pitch (verify 8mm) and bolt-circle diameters.
- **Confirmed materials & iProperties** per part (only `Aluminum 6061` / `Generic` sampled so far) — mass, appearance, stock.
- **goBILDA part-number → component-type dictionary** validated against actual placed COTS (series map in §2 is inferred from patterns).
- **Full assembly constraint graphs** for `claw assemble.iam`, `50t gears.iam`, `26MRB-*` subsystems (digest only reached `Standard (in).iam` top-level refs).
- **Which "iLogic" training parts are truly parametric** vs static (scan said Shaft-1..10 / Tube-1..5 are static outputs despite folder name) — and any iLogic rule source text.
- **iFeature definitions** behind the goBILDA Channel Generator (hole macro params, available lengths beyond 240mm).
- **Thumbnails** (PNG present in every `.ipt`/`.iam`) for a visual part index.
- **Active-vs-dead disambiguation** across the 3,378-file `Advay(1)` sandbox and superseded `2026 Minotaur Rebuilt`.
