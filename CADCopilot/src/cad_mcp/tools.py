"""MCP tool layer. Each tool converts the user's units to internal cm/radians and
dispatches to the active backend, then returns JSON-friendly results. Tool bodies
never branch on which engine is active.

Phase 1 registers documents, sketch primitives, extrude, and core inspection.
Later phases add the remaining features, assembly, export, library and escape hatch.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import Image

from . import config, ftc_constants, index, research, screenshots, scratchpad, units, state
from .backends.base import OpResult

_DENY_IMPORTS = {"os", "sys", "subprocess", "socket", "shutil", "requests", "urllib",
                 "http", "ctypes", "importlib", "builtins", "pathlib", "glob", "io"}
_DENY_CALLS = {"eval", "exec", "compile", "__import__", "open", "input", "getattr"}


def _validate_code(code: str) -> None:
    """ast denylist for the execute_script escape hatch — blocks filesystem,
    network, process and reflection escapes while allowing CAD geometry code."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"syntax error: {e}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in _DENY_IMPORTS:
                    raise ValueError(f"import of {a.name!r} is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in _DENY_IMPORTS:
                raise ValueError(f"import from {node.module!r} is not allowed")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _DENY_CALLS:
            raise ValueError(f"call to {node.func.id}() is not allowed")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("dunder attribute access is not allowed")
        elif isinstance(node, ast.Name) and node.id in {"__import__", "__builtins__"}:
            raise ValueError("access to builtins is not allowed")


def _u(value: float, unit: Optional[str]) -> float:
    """User length -> internal cm, using the session default unit if unset."""
    return units.to_cm(value, unit or state.session_unit())


def _result(r) -> dict:
    if isinstance(r, OpResult):
        return r.to_dict()
    if isinstance(r, list):
        return {"items": [x.to_dict() if hasattr(x, "to_dict") else x for x in r],
                "count": len(r)}
    if hasattr(r, "to_dict"):
        return r.to_dict()
    return {"result": r}


def register(mcp) -> None:
    # ----------------------------------------------------------------- #
    # connection / units
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def connect_cad() -> dict:
        """Connect to the CAD app (Inventor attaches to a running instance, else
        launches the newest; first call can take ~30-60s if it must launch).
        Returns the connected app + version + any open document."""
        return state.backend().connect()

    @mcp.tool()
    def set_default_units(unit: str) -> dict:
        """Set the default length unit for subsequent tool inputs ('in' for FRC,
        'mm' for FTC/goBILDA). Individual calls can still override per-call."""
        return {"default_unit": state.set_session_unit(unit)}

    # ----------------------------------------------------------------- #
    # documents
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def new_document(doc_type: str = "part", name: str = "", output_path: str = "") -> dict:
        """Create and activate a new part or assembly document.
        doc_type: 'part' | 'assembly'. name: display name. output_path: where it
        will be saved/exported later (the build asks you per project)."""
        return _result(state.backend().new_document(doc_type, name, output_path))

    # ----------------------------------------------------------------- #
    # sketch geometry
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def create_sketch(plane: str = "xy", name: str = "") -> dict:
        """Start a sketch on an origin plane ('xy'|'xz'|'yz') or a named planar
        face (from list_faces). Returns the sketch's semantic name."""
        return _result(state.backend().create_sketch(plane, name))

    @mcp.tool()
    def add_rectangle(sketch: str, x1: float, y1: float, x2: float, y2: float,
                      unit: str = "", name: str = "") -> dict:
        """Add a two-corner rectangle to a sketch. Coordinates are in the session
        unit unless `unit` is given (e.g. 'mm')."""
        return _result(state.backend().add_rectangle(
            sketch, _u(x1, unit), _u(y1, unit), _u(x2, unit), _u(y2, unit), name))

    @mcp.tool()
    def add_circle(sketch: str, cx: float, cy: float, radius: float,
                   unit: str = "", name: str = "") -> dict:
        """Add a circle (center + radius) to a sketch."""
        return _result(state.backend().add_circle(
            sketch, _u(cx, unit), _u(cy, unit), _u(radius, unit), name))

    @mcp.tool()
    def add_line(sketch: str, points: list[list[float]], closed: bool = False,
                 unit: str = "", name: str = "") -> dict:
        """Add a connected polyline through [[x,y],...]. Set closed=true to close
        the loop into a region (needed for extrude/revolve profiles)."""
        cm_pts = [[_u(p[0], unit), _u(p[1], unit)] for p in points]
        return _result(state.backend().add_line(sketch, cm_pts, closed, name))

    # ----------------------------------------------------------------- #
    # features
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def create_extrude(sketch: str, distance: float, operation: str = "new_body",
                       direction: str = "pos", taper_deg: float = 0.0,
                       unit: str = "", name: str = "") -> dict:
        """Extrude a sketch's closed profile(s).
        operation: 'new_body'|'join'|'cut'|'intersect'.
        direction: 'pos'|'neg'|'symmetric'. taper_deg: optional draft.
        Returns the feature name and the resulting body names."""
        from .units import deg_to_rad
        return _result(state.backend().create_extrude(
            sketch, _u(distance, unit), operation, direction,
            deg_to_rad(taper_deg) if taper_deg else 0.0, name))

    @mcp.tool()
    def add_point(sketch: str, x: float, y: float, unit: str = "", name: str = "") -> dict:
        """Add a hole-center / construction point to a sketch (use before create_hole)."""
        return _result(state.backend().add_point(sketch, _u(x, unit), _u(y, unit), name))

    @mcp.tool()
    def add_axis_line(sketch: str, x1: float, y1: float, x2: float, y2: float,
                      unit: str = "", name: str = "") -> dict:
        """Add a construction centerline to a sketch to revolve around. Pass its
        returned name as `axis` to create_revolve (most reliable revolve axis)."""
        return _result(state.backend().add_axis_line(
            sketch, _u(x1, unit), _u(y1, unit), _u(x2, unit), _u(y2, unit), name))

    @mcp.tool()
    def add_arc(sketch: str, cx: float, cy: float, sx: float, sy: float, ex: float, ey: float,
                unit: str = "", name: str = "") -> dict:
        """Add an arc by center (cx,cy), start (sx,sy) and end (ex,ey) points (CCW)."""
        return _result(state.backend().add_arc(
            sketch, [_u(cx, unit), _u(cy, unit)], [_u(sx, unit), _u(sy, unit)],
            [_u(ex, unit), _u(ey, unit)], name))

    @mcp.tool()
    def add_ellipse(sketch: str, cx: float, cy: float, major_dx: float, major_dy: float,
                    major_r: float, minor_r: float, unit: str = "", name: str = "") -> dict:
        """Add an ellipse: center, major-axis direction (major_dx,major_dy), and radii."""
        return _result(state.backend().add_ellipse(
            sketch, [_u(cx, unit), _u(cy, unit)], [major_dx, major_dy],
            _u(major_r, unit), _u(minor_r, unit), name))

    @mcp.tool()
    def add_polygon(sketch: str, sides: int, cx: float, cy: float, radius: float,
                    inscribed: bool = True, unit: str = "", name: str = "") -> dict:
        """Add a regular polygon (3-120 sides). inscribed=true puts vertices on the
        radius circle; false makes the sides tangent (across-flats)."""
        return _result(state.backend().add_polygon(
            sketch, sides, [_u(cx, unit), _u(cy, unit)], _u(radius, unit), inscribed, name))

    @mcp.tool()
    def add_spline(sketch: str, points: list[list[float]], unit: str = "", name: str = "") -> dict:
        """Add a fit-point spline through [[x,y],...] (organic curves, cam profiles)."""
        return _result(state.backend().add_spline(
            sketch, [[_u(p[0], unit), _u(p[1], unit)] for p in points], name))

    @mcp.tool()
    def add_slot(sketch: str, x1: float, y1: float, x2: float, y2: float, width: float,
                 unit: str = "", name: str = "") -> dict:
        """Add a center-to-center slot (two arcs + two lines) of the given width."""
        return _result(state.backend().add_slot(
            sketch, [_u(x1, unit), _u(y1, unit)], [_u(x2, unit), _u(y2, unit)], _u(width, unit), name))

    @mcp.tool()
    def create_revolve(sketch: str, axis: str = "y", angle_deg: float = 360.0,
                       operation: str = "new_body", name: str = "") -> dict:
        """Revolve a sketch profile around an axis ('x'|'y'|'z' or a named axis).
        Pistons, shafts, pulleys, flywheels, valves. angle_deg=360 for a full revolve."""
        return _result(state.backend().create_revolve(
            sketch, axis, units.deg_to_rad(angle_deg), operation, name))

    @mcp.tool()
    def create_loft(sections: list[str], rails: list[str] = [], operation: str = "new_body",
                    name: str = "") -> dict:
        """Loft a solid through >=2 profile sketches (on different planes). Optional
        `rails` (sketch names) guide the shape and prevent singularities — use them
        for organic shapes like intake/exhaust manifolds."""
        return _result(state.backend().create_loft(sections, list(rails), operation, name))

    @mcp.tool()
    def create_sweep(profile: str, path: str, operation: str = "new_body",
                     twist_deg: float = 0.0, name: str = "") -> dict:
        """Sweep a profile sketch along a path sketch (the path's connected curves).
        For tubing, wiring channels, swept ribs."""
        return _result(state.backend().create_sweep(profile, path, operation,
                                                    units.deg_to_rad(twist_deg), name))

    @mcp.tool()
    def create_coil(profile: str, axis: str, pitch: float, rotations: float = 1.0,
                    operation: str = "new_body", unit: str = "", name: str = "") -> dict:
        """Coil/helix a profile around an axis (use add_axis_line) — springs, threads,
        helical flutes, auger/flywheel teeth. pitch is per revolution."""
        return _result(state.backend().create_coil(profile, axis, _u(pitch, unit),
                                                   rotations, operation, name))

    @mcp.tool()
    def create_spur_gear(teeth: int, module: float, thickness: float, bore: float = 0.0,
                         pressure_angle_deg: float = 20.0, unit: str = "", name: str = "") -> dict:
        """Generate a parametric spur gear blank (FTC mod-2 etc.): pitch dia = module*teeth.
        module/thickness/bore in the session unit. Returns pitch/outside diameters.
        Trapezoidal-tooth approximation (great for 3D print); for a true involute pair
        use Inventor's Design Accelerator via execute_script."""
        return _result(state.backend().create_spur_gear(
            teeth, _u(module, unit), _u(thickness, unit), _u(bore, unit) if bore else 0.0,
            units.deg_to_rad(pressure_angle_deg), name))

    @mcp.tool()
    def create_hole(sketch: str, diameter: float, depth: float = 0.0, through_all: bool = True,
                    flip: bool = False, unit: str = "", name: str = "") -> dict:
        """Drill holes at every point in `sketch` (add center points with add_point first).
        through_all=true ignores depth. flip reverses the drill direction."""
        return _result(state.backend().create_hole(
            sketch, _u(diameter, unit), _u(depth, unit) if depth else 0.0, through_all, flip, name))

    @mcp.tool()
    def create_fillet(edges: list[str], radius: float, unit: str = "", name: str = "") -> dict:
        """Round the named edges (from list_edges) with a constant radius."""
        return _result(state.backend().create_fillet(edges, _u(radius, unit), name))

    @mcp.tool()
    def create_chamfer(edges: list[str], distance: float, unit: str = "", name: str = "") -> dict:
        """Chamfer the named edges by an equal setback distance."""
        return _result(state.backend().create_chamfer(edges, _u(distance, unit), None, name))

    @mcp.tool()
    def create_shell(faces_to_remove: list[str], thickness: float, inside: bool = True,
                     unit: str = "", name: str = "") -> dict:
        """Hollow the body to a wall thickness, removing the named faces (open them)."""
        return _result(state.backend().create_shell(faces_to_remove, _u(thickness, unit), inside, name))

    @mcp.tool()
    def pattern_rectangular(features: list[str], dir1: str = "x", count1: int = 2, spacing1: float = 8.0,
                            dir2: str = "", count2: int = 1, spacing2: float = 0.0,
                            unit: str = "", name: str = "") -> dict:
        """Rectangular (grid) pattern of features along axis dir1 (and optional dir2).
        Spacings are in the session unit. Great for bolt grids / goBILDA hole arrays."""
        return _result(state.backend().pattern_rectangular(
            features, dir1, count1, _u(spacing1, unit), dir2, count2, _u(spacing2, unit) if spacing2 else 0.0, name))

    @mcp.tool()
    def pattern_circular(features: list[str], axis: str = "z", count: int = 4,
                         angle_deg: float = 360.0, fill360: bool = True, name: str = "") -> dict:
        """Circular pattern of features about an axis. fill360 distributes `count`
        evenly over a full circle; else spans angle_deg. Bolt circles, cylinder bores."""
        return _result(state.backend().pattern_circular(features, axis, count, angle_deg, fill360, name))

    @mcp.tool()
    def mirror_feature(features: list[str], plane: str = "xy", name: str = "") -> dict:
        """Mirror features across a plane ('xy'|'xz'|'yz' or a named plane/face).
        Use for left/right symmetry and V-bank engine layouts."""
        return _result(state.backend().mirror_feature(features, plane, "join", name))

    @mcp.tool()
    def boolean_combine(target_body: str, tool_bodies: list[str], operation: str = "union",
                        name: str = "") -> dict:
        """Combine bodies: operation 'union'|'subtract'|'intersect'. target is kept,
        tool_bodies are consumed."""
        return _result(state.backend().boolean_combine(target_body, tool_bodies, operation, name))

    @mcp.tool()
    def add_workplane(kind: str = "offset", refs: list[str] = [], value: float = 0.0,
                      unit: str = "", name: str = "") -> dict:
        """Create a work plane. kind='offset' (refs=[plane], value=distance) or
        kind='angle' (refs=[axis, plane], value=degrees). For V-banks / offset sketches."""
        v = units.deg_to_rad(value) if kind == "angle" else _u(value, unit)
        return _result(state.backend().add_workplane(kind, list(refs), v, name))

    # ----------------------------------------------------------------- #
    # inspection
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def list_bodies() -> dict:
        """List solid bodies with face/edge counts, volume (mm^3) and bounding box
        (mm). Use the returned names to target later operations."""
        return _result(state.backend().list_bodies())

    @mcp.tool()
    def bounding_box(body: str = "") -> dict:
        """Overall extents in mm of one body (by name) or the whole model. Use to
        check size and split-for-print thresholds."""
        return _result(state.backend().bounding_box(body or None))

    @mcp.tool()
    def list_features(body: str = "") -> dict:
        """List the feature tree (name, type, suppressed, health). Use after an op to
        confirm it succeeded and to see the build order."""
        return _result(state.backend().list_features(body or None))

    @mcp.tool()
    def list_faces(body: str = "") -> dict:
        """List a body's faces with type, area (mm^2), centroid and (for planar)
        normal / (for cylindrical) radius. Use the returned names to place sketches,
        holes or shells. Pick the top face by normal ~ [0,0,1]."""
        return _result(state.backend().list_faces(body))

    @mcp.tool()
    def list_edges(body: str = "", face: str = "") -> dict:
        """List edges (by body or by a named face) with type, length (mm) and
        endpoints. Use the returned names to target fillets/chamfers."""
        return _result(state.backend().list_edges(body or None, face or None))

    @mcp.tool()
    def measure(entity_a: str, entity_b: str = "", what: str = "distance") -> dict:
        """Measure: what='distance' (between two named entities), 'length' (an edge),
        or 'bbox' (a body). Verify dimensions before/after ops (e.g. bore > piston)."""
        return _result(state.backend().measure(entity_a, entity_b or None, what))

    @mcp.tool()
    def set_parameter(name: str, expression: str, comment: str = "", mode: str = "set") -> dict:
        """Create or set a named parameter, e.g. set_parameter('Bore','85.5 mm').
        Other dimensions can reference it. mode='create' forces a new user parameter."""
        return _result(state.backend().set_parameter(name, expression, comment, mode))

    @mcp.tool()
    def get_parameters() -> dict:
        """List all model + user parameters with expressions and values (mm). Read
        these before changing dimensions."""
        return _result(state.backend().get_parameters())

    @mcp.tool()
    def screenshot(width: int = 1024, height: int = 768) -> Image:
        """Render the current viewport and RETURN IT AS AN IMAGE so you can see the
        model and self-correct. Call after every few operations."""
        png = state.backend().screenshot_png(width, height)
        return Image(data=screenshots.downscale(png), format="png")

    @mcp.tool()
    def get_last_error() -> dict:
        """Return the most recent backend error with a recovery suggestion."""
        return state.backend().get_last_error()

    # ----------------------------------------------------------------- #
    # export
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def export(fmt: str = "stl", path: str = "", body: str = "", resolution: int = 0) -> dict:
        """Export the active document to a file. fmt: 'stl'|'step'|'iges'|'obj'.
        STL is binary, manifold (for 3D printing). If path is empty it goes to the
        output dir. resolution 0=high..2=low (STL)."""
        if not path:
            path = str(Path(config.CAD_OUTPUT_DIR) / f"cadcopilot_export.{fmt.lstrip('.')}")
        return _result(state.backend().export(fmt, path, body or None, {"resolution": resolution}))

    # ----------------------------------------------------------------- #
    # iLogic
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def run_ilogic_rule(rule: str, document: str = "", external: bool = False) -> dict:
        """Run an existing iLogic rule (e.g. drive Advay's parametric Tube/Shaft/
        pulley parts). document selects an open doc by name (default: active).
        external=true runs an external rule by name."""
        return _result(state.backend().run_ilogic_rule(document, rule, external))

    @mcp.tool()
    def list_ilogic_rules(document: str = "") -> dict:
        """List iLogic rules in the active (or named) document."""
        return _result(state.backend().list_ilogic_rules(document))

    @mcp.tool()
    def create_ilogic_rule(name: str, code: str, document: str = "") -> dict:
        """Create an iLogic rule (VB.NET) on the active document — make parts
        parametric/self-updating like Advay's Tube/Shaft/pulley generators."""
        return _result(state.backend().create_ilogic_rule(name, code, document))

    # ----------------------------------------------------------------- #
    # iProperties / materials / physical / import
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def get_iproperties() -> dict:
        """Read key iProperties (part number, description, material, designer, title)."""
        return _result(state.backend().get_iproperties())

    @mcp.tool()
    def set_iproperty(name: str, value: str) -> dict:
        """Set an iProperty, e.g. set_iproperty('Part Number','26MRB-500-001'). Follow
        Advay's BOM naming (see cad://knowledge/naming-schema)."""
        return _result(state.backend().set_iproperty(name, value))

    @mcp.tool()
    def physical_properties() -> dict:
        """Mass (g), volume (mm^3), area, and center of mass of the active part."""
        return _result(state.backend().physical_properties())

    @mcp.tool()
    def set_material(material: str) -> dict:
        """Assign a material by name (e.g. 'Aluminum 6061', 'ABS Plastic', 'Polycarbonate')."""
        return _result(state.backend().set_material(material))

    @mcp.tool()
    def import_file(path: str) -> dict:
        """Open/import a CAD file (STEP/IGES/SAT/IPT/IAM) as a document."""
        return _result(state.backend().import_file(path))

    # ----------------------------------------------------------------- #
    # save + assembly
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def save_document(path: str) -> dict:
        """Save the active part/assembly to a .ipt/.iam path (parts must be saved
        before they can be inserted into an assembly)."""
        return _result(state.backend().save_document(path))

    @mcp.tool()
    def close_all_documents(save: bool = False) -> dict:
        """Close all open Inventor documents (save=false discards). Useful to clear
        state / release file locks before a fresh build."""
        return _result(state.backend().close_all_documents(save))

    @mcp.tool()
    def insert_component(source: str, name: str = "", x: float = 0.0, y: float = 0.0, z: float = 0.0,
                         rx_deg: float = 0.0, ry_deg: float = 0.0, rz_deg: float = 0.0,
                         grounded: bool = False, unit: str = "") -> dict:
        """Insert a component into the active ASSEMBLY at a position + rotation.
        source = a full .ipt/.iam path (or a library query, see insert_part).
        Position in the session unit; rotation in degrees (use rx/ry/rz for V-banks)."""
        pos = [_u(x, unit), _u(y, unit), _u(z, unit)]
        rot = [units.deg_to_rad(rx_deg), units.deg_to_rad(ry_deg), units.deg_to_rad(rz_deg)]
        return _result(state.backend().insert_component(source, name, pos, rot, grounded))

    @mcp.tool()
    def insert_part(query: str, name: str = "", x: float = 0.0, y: float = 0.0, z: float = 0.0,
                    grounded: bool = False, unit: str = "") -> dict:
        """Find a part in the indexed library by name/part-number and drop it into the
        active assembly. Reuse COTS instead of remodelling (run reindex_parts first)."""
        pos = [_u(x, unit), _u(y, unit), _u(z, unit)]
        return _result(state.backend().insert_component(query, name, pos, [0, 0, 0], grounded))

    @mcp.tool()
    def ground(occurrence: str, grounded: bool = True) -> dict:
        """Ground (fix) or unground an inserted component by its name."""
        return _result(state.backend().ground(occurrence, grounded))

    @mcp.tool()
    def list_occurrence_faces(occurrence: str) -> dict:
        """List the faces of an inserted component (by name) so you can target them
        for assembly constraints/joints. Returns face names + type + centroid."""
        return _result(state.backend().list_occurrence_faces(occurrence))

    @mcp.tool()
    def add_constraint(kind: str, a: str, b: str, offset: float = 0.0, unit: str = "",
                       name: str = "") -> dict:
        """Add an assembly constraint between two occurrence faces (from
        list_occurrence_faces). kind: 'mate'|'flush'|'insert'|'angle'|'tangent'.
        offset is a distance (mate/flush/insert) or angle in degrees (angle)."""
        off = units.deg_to_rad(offset) if kind.lower() == "angle" else _u(offset, unit)
        return _result(state.backend().add_constraint(kind, a, b, off if offset else 0.0, name))

    @mcp.tool()
    def add_joint(kind: str, a: str, b: str, name: str = "") -> dict:
        """Add an assembly joint between two occurrence faces/entities.
        kind: 'rigid'|'rotational'(revolute)|'slider'|'cylindrical'|'planar'|'ball'."""
        return _result(state.backend().add_joint(kind, a, b, name))

    # ----------------------------------------------------------------- #
    # planning scratchpad
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def scratchpad_update(key: str, value: str) -> dict:
        """Save a plan/parameter-table entry that persists across tool calls."""
        scratchpad.update(key, value)
        return {"ok": True, "key": key}

    @mcp.tool()
    def scratchpad_get(key: str = "") -> dict:
        """Read the scratchpad (all entries, or one key)."""
        return {"value": scratchpad.get(key)}

    @mcp.tool()
    def web_research(query: str, max_pages: int = 3) -> dict:
        """Free web research (DuckDuckGo + page text, no API key, no cost). Use it to
        gather reference context BEFORE planning a build you lack reliable data on —
        e.g. a real-world object's parts, layout, and proportions ('fire truck
        dimensions', 'planetary gearbox stages'). Returns concise extracted text."""
        return {"research": research.web_research(query, max_pages)}

    # ----------------------------------------------------------------- #
    # FTC / DFM helpers
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def ftc_constants() -> dict:
        """Return vetted goBILDA / REV / FRC / design-for-3D-print constants (mm)."""
        return ftc_constants.ALL

    @mcp.tool()
    def apply_print_clearance(nominal_mm: float, fit: str = "clearance") -> dict:
        """Compute the print-adjusted dimension for a fit:
        'press'|'snug'|'clearance'|'rotating'|'loose', or 'heat_set'/'nut_trap' (M3).
        Use the returned diameter when sizing a hole so printed parts actually fit."""
        try:
            return ftc_constants.clearance_for(nominal_mm, fit)
        except ValueError as e:
            return {"ok": False, "error": str(e)}

    @mcp.tool()
    def gobilda_pattern(sketch: str, x0: float, y0: float, nx: int = 2, ny: int = 2,
                        pitch_mm: float = 8.0, diameter_mm: float = 0.0) -> dict:
        """Drill a goBILDA-style hole grid into `sketch`: nx x ny holes at `pitch_mm`
        (default 8mm). diameter_mm defaults to the M4 pattern hole. x0/y0 (sketch
        coords) are in mm. Sketch on the face/plane you want the pattern on first."""
        be = state.backend()
        dia = diameter_mm or ftc_constants.GOBILDA["hole_dia_mm"]
        for i in range(nx):
            for j in range(ny):
                be.add_point(sketch, units.to_cm(x0 + i * pitch_mm, "mm"),
                             units.to_cm(y0 + j * pitch_mm, "mm"), "")
        return _result(be.create_hole(sketch, units.to_cm(dia, "mm"), 0.0, True, False, "gobilda_holes"))

    # ----------------------------------------------------------------- #
    # parts library
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def search_parts(query: str, limit: int = 20) -> dict:
        """Search the indexed Inventor library (goBILDA / vendor / Advay's parts) by
        name, part number, project or path. Reuse these instead of remodelling.
        Run reindex_parts first if results are empty."""
        return {"results": index.search(query, limit), "query": query}

    @mcp.tool()
    def reindex_parts(roots: list[str] = [], deep: bool = False, limit: int = 0) -> dict:
        """(Re)build the parts catalog index. roots defaults to CacheCAD + Downloads.
        deep=true also scans binaries for iLogic markers and component references
        (slower). limit caps files for a quick test."""
        return index.build_index(list(roots) or None, deep, limit or None)

    @mcp.tool()
    def parts_index_stats() -> dict:
        """How many parts are currently indexed."""
        return index.stats()

    # ----------------------------------------------------------------- #
    # guarded escape hatch
    # ----------------------------------------------------------------- #
    @mcp.tool()
    def execute_script(code: str, language: str = "inventor_python") -> dict:
        """Run backend-native code for geometry the typed tools can't express
        (e.g. phased crank journals, lofted manifolds). The live document is in
        scope as: app, doc, compdef, tg (TransientGeometry), tobj, C (constants),
        reg (entity registry), math, cm(mm). Set `result` to return a value.
        Transaction-wrapped (rolled back on error). Blocked: filesystem, network,
        process, imports of os/sys/etc. Use as a deliberate last resort."""
        try:
            _validate_code(code)
        except ValueError as e:
            return {"ok": False, "rejected": True, "error": str(e)}
        out = state.backend().eval_native(code, {})
        return {"ok": True, "result": out if isinstance(out, (str, int, float, bool, list, dict, type(None))) else str(out)}
