"""Vetted FTC/FRC/goBILDA + design-for-3D-print constants so tools use real
numbers instead of the agent guessing. All lengths in millimetres.

Sources: goBILDA technical docs, REV/WCP specs, common FDM practice. Treat the
goBILDA series->type map as a strong hint, not gospel.
"""

# --- goBILDA --------------------------------------------------------------- #
GOBILDA = {
    "grid_pitch_mm": 8.0,          # the goBILDA 8mm hole grid
    "hole_dia_mm": 4.1,            # M4 clearance through-hole on the pattern
    "bolt_M4": 4.0,
    "bolt_M3": 3.0,
    "bolt_circle_32_mm": 32.0,     # common goBILDA bolt circles
    "bolt_circle_48_mm": 48.0,
    "bearing_od_mm": 14.0,         # standard goBILDA bearing OD
    "rex_shaft_mm": 8.0,           # 8mm REX
    "hex_shaft_mm": 5.0,           # 5mm hex (also REV)
    "d_shaft_mm": 6.0,
}

# --- REV / FRC / WCP ------------------------------------------------------- #
REV = {"extrusion_mm": 15.0, "pattern_mm": 8.0, "bolt": 3.0, "hex_shaft_mm": 5.0}
FRC = {
    "tube_1x1_in": 25.4, "tube_2x1_in": (50.8, 25.4),
    "hole_pattern_in": 12.7,       # 0.5in pattern
    "bolt_10_32_clear_mm": 5.0, "bolt_8_32_clear_mm": 4.4,
    "bearing_bore_in": (22.225, 28.575),  # 0.875in, 1.125in
}

# --- design-for-3D-print (FDM, 0.4mm nozzle) ------------------------------- #
DFM = {
    "nozzle_mm": 0.4,
    "layer_mm": 0.2,
    "min_wall_mm": 1.2,            # >= 3 perimeters
    "overhang_deg": 45.0,
    "fillet_base_mm": 1.0,
    # clearances added to a NOMINAL diameter/slot for a given fit
    "clearance": {
        "press": -0.05,           # interference / press fit
        "snug": 0.10,
        "clearance": 0.20,        # parts slide together
        "rotating": 0.30,         # shaft spins freely
        "loose": 0.40,
    },
    # M3 hardware accommodations (hole diameter / pocket dims, mm)
    "heat_set_M3_dia_mm": 4.1,    # 4.0-4.2 hole for M3 brass heat-set insert
    "heat_set_M3_depth_mm": 4.0,
    "nut_trap_M3": {"across_flats_mm": 5.6, "across_corners_mm": 6.6, "depth_mm": 2.6},
    "clearance_M3_mm": 3.4,
    "tap_M3_mm": 2.5,
}


def clearance_for(nominal_mm: float, fit: str) -> dict:
    """Return the adjusted dimension for a fit type over a nominal size."""
    fit = (fit or "clearance").lower()
    if fit in ("heat_set", "heat_set_m3", "insert"):
        return {"fit": "heat_set_M3", "diameter_mm": DFM["heat_set_M3_dia_mm"],
                "depth_mm": DFM["heat_set_M3_depth_mm"]}
    if fit in ("nut_trap", "nut_trap_m3", "nut"):
        return {"fit": "nut_trap_M3", **DFM["nut_trap_M3"]}
    delta = DFM["clearance"].get(fit)
    if delta is None:
        raise ValueError(f"Unknown fit {fit!r}; use one of "
                         f"{list(DFM['clearance']) + ['heat_set', 'nut_trap']}")
    return {"fit": fit, "nominal_mm": nominal_mm, "delta_mm": delta,
            "adjusted_mm": round(nominal_mm + delta, 3)}


ALL = {"goBILDA": GOBILDA, "REV": REV, "FRC": FRC, "DFM": DFM}
