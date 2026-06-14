# FTC / FRC / goBILDA conventions (for CADCopilot)

All numbers in **mm** unless noted. These are the defaults to design around so parts
mate with COTS hardware. Mirror whatever ecosystem the surrounding project uses.

## goBILDA (Advay's primary system)
- **Hole grid:** 8 mm pitch. Custom plates that bolt to goBILDA land on this grid.
- **Pattern hole:** 4.1 mm clearance for M4 (the goBILDA pattern bolt).
- **Bolt circles:** 32 mm and 48 mm are common hub/bearing circles.
- **Bearings:** 14 mm OD standard.
- **Shafts:** 8 mm REX (primary), 5 mm hex, 6 mm D. Size custom bores to these
  (add a clearance — see `dfm-3dprint-rules`).
- **Fasteners:** M3 and M4 (set-screw collars, clamping hubs).
- **Part numbers:** 4-4-4 `AAAA-BBBB-CCCC`. Series hint: 11xx structure/channel,
  12xx servos, 13xx motors, 15xx/16xx motion, 19xx bearings, 20xx rollers/wheels,
  23xx gearmotors, 2025-* shooter gears, 26MIN-* Minotaur kit, 36xx REX shafts.
- **Gears:** FTC commonly mod-2 / 20-DP; pairs like 20T/30T. Center distance for a
  meshing pair = module × (N1 + N2) / 2  (or (N1+N2)/(2·DP)).

## REV
- 15 mm extrusion rail; 8 mm pattern; M3 hardware; 5 mm hex shaft.

## FRC / WCP (the "26MRB"/Minotaur world)
- 1×1 in and 2×1 in box tube; 0.5 in (12.7 mm) hole pattern.
- #10-32 (~5.0 mm clear) and #8-32 (~4.4 mm clear) fasteners.
- Bearing bores 0.875 in (22.225) and 1.125 in (28.575).
- Swerve: MK4N modules, Kraken + MAXPlanetary, 80/20 extrusion, polycarb plates.
- WCP part naming like `WR20W-200-001`.

## Belts / chain
- Center distance from belt/chain pitch length and pulley/sprocket teeth; leave a
  tensioning range. GT2/HTD pulleys for FTC; #25/#35 chain for FRC.

Use the `ftc_constants` tool for the machine-readable version, and
`apply_print_clearance` to size printed bores over a nominal shaft/bearing.
