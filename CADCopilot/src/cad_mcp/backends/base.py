"""Backend abstraction shared by the Inventor (COM) and Fusion (TCP bridge) engines.

The unified MCP tool layer calls these methods and never branches on the active
engine. Both concrete backends expose the identical surface.

Unit convention at this boundary:
  * Distances passed INTO backend methods are in CENTIMETRES (cm) — the internal
    database unit of both Inventor and Fusion. The MCP tool layer converts the
    user's mm / inch inputs to cm via ``cad_mcp.units`` before calling.
  * Angles passed in are in RADIANS.
  * Measurements returned in the info dataclasses are in MILLIMETRES (mm) and
    DEGREES — canonical human units the agent reasons in. The tool layer may
    re-present them in the session's preferred unit.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
class CADError(Exception):
    """A backend operation failed. Carries a recovery hint for the agent."""

    def __init__(self, message: str, *, operation: str = "", recovery: str = "",
                 affected: Optional[list[str]] = None):
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.recovery = recovery
        self.affected = affected or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": False,
            "operation": self.operation,
            "message": self.message,
            "recovery_suggestion": self.recovery,
            "affected": self.affected,
        }


# --------------------------------------------------------------------------- #
# Result / info dataclasses (JSON-serialisable via to_dict)
# --------------------------------------------------------------------------- #
@dataclass
class OpResult:
    """Generic result of a mutating operation."""
    ok: bool = True
    name: str = ""               # semantic name registered for the created entity
    kind: str = ""               # e.g. "extrude", "sketch", "body"
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BodyInfo:
    name: str
    face_count: int = 0
    edge_count: int = 0
    volume_mm3: float = 0.0
    area_mm2: float = 0.0
    bbox_mm: list[float] = field(default_factory=list)  # [xmin,ymin,zmin,xmax,ymax,zmax]
    appearance: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FaceInfo:
    name: str
    surface_type: str = ""       # planar | cylindrical | conical | spherical | toroidal | nurbs
    area_mm2: float = 0.0
    centroid_mm: list[float] = field(default_factory=list)
    normal: list[float] = field(default_factory=list)   # for planar faces
    radius_mm: float = 0.0       # for cylindrical/spherical

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EdgeInfo:
    name: str
    curve_type: str = ""         # line | circle | arc | ellipse | spline
    length_mm: float = 0.0
    start_mm: list[float] = field(default_factory=list)
    end_mm: list[float] = field(default_factory=list)
    midpoint_mm: list[float] = field(default_factory=list)
    radius_mm: float = 0.0
    adjacent_faces: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FeatureInfo:
    name: str
    feature_type: str = ""
    suppressed: bool = False
    health: str = "ok"           # ok | warning | error
    consumed_bodies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParamInfo:
    name: str
    expression: str = ""
    value_mm: float = 0.0
    unit: str = ""
    comment: str = ""
    is_user: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MeasureResult:
    what: str
    value: float = 0.0
    unit: str = "mm"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Backend base class
# --------------------------------------------------------------------------- #
def _todo(name: str):
    raise CADError(f"{name} is not implemented in this backend yet",
                   operation=name, recovery="This feature lands in a later build phase.")


class Backend:
    """Common interface. Concrete backends override the methods they support.

    Methods that a phase hasn't implemented raise CADError via ``_todo`` so the
    server stays alive and reports a clear message instead of crashing.
    """

    name = "base"

    # --- lifecycle / connection -------------------------------------------- #
    def connect(self) -> dict[str, Any]:
        """Attach to (or launch) the CAD app. Returns {connected, app, version}."""
        _todo("connect")

    def disconnect(self) -> None:
        pass

    # --- documents --------------------------------------------------------- #
    def new_document(self, doc_type: str, name: str, output_path: str = "") -> OpResult:
        _todo("new_document")

    def save_document(self, path: str) -> OpResult: _todo("save_document")
    def close_all_documents(self, save: bool) -> OpResult: _todo("close_all_documents")

    # --- sketch geometry --------------------------------------------------- #
    def create_sketch(self, plane: str, name: str) -> OpResult: _todo("create_sketch")
    def add_rectangle(self, sketch: str, x1: float, y1: float, x2: float, y2: float, name: str) -> OpResult: _todo("add_rectangle")
    def add_circle(self, sketch: str, cx: float, cy: float, radius: float, name: str) -> OpResult: _todo("add_circle")
    def add_line(self, sketch: str, points: list[list[float]], closed: bool, name: str) -> OpResult: _todo("add_line")
    def add_arc(self, sketch: str, center: list[float], start: list[float], end: list[float], name: str) -> OpResult: _todo("add_arc")
    def add_spline(self, sketch: str, points: list[list[float]], name: str) -> OpResult: _todo("add_spline")
    def add_arc(self, sketch: str, center: list[float], start: list[float], end: list[float], name: str) -> OpResult: _todo("add_arc")
    def add_ellipse(self, sketch: str, center: list[float], major_axis: list[float], major_r: float, minor_r: float, name: str) -> OpResult: _todo("add_ellipse")
    def add_polygon(self, sketch: str, sides: int, center: list[float], radius: float, inscribed: bool, name: str) -> OpResult: _todo("add_polygon")
    def add_slot(self, sketch: str, p1: list[float], p2: list[float], width: float, name: str) -> OpResult: _todo("add_slot")
    def add_point(self, sketch: str, x: float, y: float, name: str) -> OpResult: _todo("add_point")
    def add_axis_line(self, sketch: str, x1: float, y1: float, x2: float, y2: float, name: str) -> OpResult: _todo("add_axis_line")
    def project_geometry(self, sketch: str, entity: str) -> OpResult: _todo("project_geometry")

    # --- solid features ---------------------------------------------------- #
    def create_extrude(self, profile: str, distance: float, operation: str, direction: str, taper_deg: float, name: str) -> OpResult: _todo("create_extrude")
    def create_revolve(self, profile: str, axis: str, angle: float, operation: str, name: str) -> OpResult: _todo("create_revolve")
    def create_loft(self, sections: list[str], rails: list[str], operation: str, name: str) -> OpResult: _todo("create_loft")
    def create_sweep(self, profile: str, path: str, operation: str, twist: float, name: str) -> OpResult: _todo("create_sweep")
    def create_coil(self, profile: str, axis: str, pitch: float, rotations: float, operation: str, name: str) -> OpResult: _todo("create_coil")
    def create_hole(self, sketch: str, diameter: float, depth: float, through_all: bool, flip: bool, name: str) -> OpResult: _todo("create_hole")
    def create_fillet(self, edges: list[str], radius: float, name: str) -> OpResult: _todo("create_fillet")
    def create_chamfer(self, edges: list[str], distance: float, angle: Optional[float], name: str) -> OpResult: _todo("create_chamfer")
    def create_shell(self, faces_to_remove: list[str], thickness: float, inside: bool, name: str) -> OpResult: _todo("create_shell")
    def create_rib(self, profile: str, thickness: float, operation: str, name: str) -> OpResult: _todo("create_rib")
    def create_thread(self, face: str, designation: str, length: float, name: str) -> OpResult: _todo("create_thread")
    def create_spur_gear(self, teeth: int, module: float, thickness: float, bore: float, pressure_angle: float, name: str) -> OpResult: _todo("create_spur_gear")

    # --- reference geometry / patterns ------------------------------------- #
    def add_workplane(self, kind: str, refs: list[str], value: float, name: str) -> OpResult: _todo("add_workplane")
    def add_axis(self, kind: str, refs: list[str], name: str) -> OpResult: _todo("add_axis")
    def pattern_rectangular(self, features: list[str], dir1: str, count1: int, spacing1: float, dir2: str, count2: int, spacing2: float, name: str) -> OpResult: _todo("pattern_rectangular")
    def pattern_circular(self, features: list[str], axis: str, count: int, angle: float, fill360: bool, name: str) -> OpResult: _todo("pattern_circular")
    def mirror_feature(self, features: list[str], plane: str, operation: str, name: str) -> OpResult: _todo("mirror_feature")
    def boolean_combine(self, target_body: str, tool_bodies: list[str], operation: str, name: str) -> OpResult: _todo("boolean_combine")

    # --- parameters -------------------------------------------------------- #
    def set_parameter(self, name: str, expression: str, comment: str, mode: str) -> OpResult: _todo("set_parameter")
    def get_parameters(self) -> list[ParamInfo]: _todo("get_parameters")

    # --- inspection -------------------------------------------------------- #
    def list_features(self, body: Optional[str]) -> list[FeatureInfo]: _todo("list_features")
    def list_bodies(self) -> list[BodyInfo]: _todo("list_bodies")
    def list_faces(self, body: str) -> list[FaceInfo]: _todo("list_faces")
    def list_edges(self, body: Optional[str], face: Optional[str]) -> list[EdgeInfo]: _todo("list_edges")
    def measure(self, entity_a: str, entity_b: Optional[str], what: str) -> MeasureResult: _todo("measure")
    def bounding_box(self, body: Optional[str]) -> MeasureResult: _todo("bounding_box")
    def get_last_error(self) -> dict[str, Any]: _todo("get_last_error")
    def screenshot_png(self, width: int, height: int) -> bytes: _todo("screenshot_png")

    # --- assembly ---------------------------------------------------------- #
    def insert_component(self, source: str, name: str, position: list[float], rotation: list[float], grounded: bool) -> OpResult: _todo("insert_component")
    def list_occurrence_faces(self, occurrence: str) -> list[FaceInfo]: _todo("list_occurrence_faces")
    def add_constraint(self, kind: str, a: str, b: str, offset: float, name: str) -> OpResult: _todo("add_constraint")
    def add_joint(self, kind: str, a: str, b: str, name: str) -> OpResult: _todo("add_joint")
    def ground(self, occurrence: str, grounded: bool) -> OpResult: _todo("ground")
    def pattern_component(self, occurrences: list[str], kind: str, params: dict, name: str) -> OpResult: _todo("pattern_component")

    # --- iProperties / materials / physical --------------------------------- #
    def get_iproperties(self) -> dict: _todo("get_iproperties")
    def set_iproperty(self, name: str, value: str) -> OpResult: _todo("set_iproperty")
    def physical_properties(self) -> dict: _todo("physical_properties")
    def set_material(self, material: str) -> OpResult: _todo("set_material")
    def import_file(self, path: str) -> OpResult: _todo("import_file")

    # --- iLogic ------------------------------------------------------------ #
    def run_ilogic_rule(self, document: str, rule: str, external: bool) -> OpResult: _todo("run_ilogic_rule")
    def list_ilogic_rules(self, document: str) -> dict: _todo("list_ilogic_rules")
    def create_ilogic_rule(self, name: str, code: str, document: str) -> OpResult: _todo("create_ilogic_rule")

    # --- export ------------------------------------------------------------ #
    def export(self, fmt: str, output_path: str, body: Optional[str], options: dict) -> OpResult: _todo("export")

    # --- escape hatch ------------------------------------------------------ #
    def eval_native(self, code: str, scope: dict) -> Any: _todo("eval_native")
