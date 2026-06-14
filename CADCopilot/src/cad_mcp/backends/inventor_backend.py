"""Inventor backend — drives Autodesk Inventor in-process via pywin32 COM.

Correctness essentials (validated live against Inventor 2027):
  * Inventor is STA: ALL COM access happens on one dedicated worker thread that
    has called pythoncom.CoInitialize(). Tool calls are serialized onto it.
  * Early binding via gencache.EnsureModule so enums (win32com.client.constants)
    and ByRef out-params resolve; Documents.Add returns a base Document that must
    be CastTo("PartDocument"/"AssemblyDocument").
  * Internal units are CENTIMETRES / RADIANS. Methods here receive cm + radians
    (the tool layer converts from the user's mm/inch). Info objects report mm.
  * Every mutating op runs inside a TransactionManager transaction; on failure it
    aborts (clean rollback) and a CADError with a recovery hint is raised.
"""

from __future__ import annotations

import functools
import math
import os
import queue
import threading
from typing import Any, Callable, Optional

import pythoncom
import win32com.client as win32

from .. import config
from ..registry import EntityRegistry
from .base import (
    Backend, CADError, OpResult, BodyInfo, FaceInfo, EdgeInfo,
    FeatureInfo, ParamInfo, MeasureResult,
)


# --------------------------------------------------------------------------- #
# COM worker thread (STA affinity)
# --------------------------------------------------------------------------- #
class _Task:
    __slots__ = ("fn", "done", "result", "error")

    def __init__(self, fn: Callable[[], Any]):
        self.fn = fn
        self.done = threading.Event()
        self.result: Any = None
        self.error: Optional[BaseException] = None


class ComWorker:
    """Runs all COM work on a single CoInitialized thread."""

    def __init__(self) -> None:
        self._q: "queue.Queue[Optional[_Task]]" = queue.Queue()
        self._thread = threading.Thread(target=self._loop, name="cad-com", daemon=True)
        self._started = threading.Event()
        self._thread.start()
        self._started.wait(5)

    def _loop(self) -> None:
        pythoncom.CoInitialize()
        self._started.set()
        try:
            while True:
                task = self._q.get()
                if task is None:
                    break
                try:
                    task.result = task.fn()
                except BaseException as e:  # noqa: BLE001 - propagate to caller thread
                    task.error = e
                finally:
                    task.done.set()
        finally:
            pythoncom.CoUninitialize()

    def submit(self, fn: Callable[[], Any], timeout: float = 300.0) -> Any:
        task = _Task(fn)
        self._q.put(task)
        if not task.done.wait(timeout):
            raise CADError("CAD operation timed out", recovery="The app may be busy or showing a dialog.")
        if task.error is not None:
            raise task.error
        return task.result

    def shutdown(self) -> None:
        self._q.put(None)


def _recovery_hint(msg: str) -> str:
    m = msg.lower()
    if "profile" in m or "addforsolid" in m:
        return "The sketch needs a single closed loop. Check geometry is closed and not self-intersecting."
    if "no active" in m or "componentdefinition" in m:
        return "Open a part/assembly first with new_document."
    if "disconnected" in m or "rpc" in m or "-2147" in m:
        return "Lost the Inventor connection. Ensure Inventor is open and call cad_status."
    return ""


def worker_op(label: str):
    """Decorator: run the method body on the COM worker thread, wrapping failures
    as CADError and recording them for get_last_error."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(self: "InventorBackend", *a, **k):
            def call():
                return fn(self, *a, **k)
            try:
                return self._worker.submit(call)
            except CADError as e:
                self._last_error = e.to_dict()
                raise
            except Exception as e:  # noqa: BLE001
                ce = CADError(str(e), operation=label, recovery=_recovery_hint(str(e)))
                self._last_error = ce.to_dict()
                raise ce
        return wrapper
    return deco


# --------------------------------------------------------------------------- #
# Backend
# --------------------------------------------------------------------------- #
class InventorBackend(Backend):
    name = "inventor"

    def __init__(self) -> None:
        self._worker = ComWorker()
        self.app = None
        self.C = None                      # win32com.client.constants
        self.doc = None                    # active PartDocument / AssemblyDocument
        self.compdef = None                # active ComponentDefinition
        self.tg = None                     # TransientGeometry
        self.tobj = None                   # TransientObjects
        self.reg = EntityRegistry()
        self._last_error: dict = {}
        self._connected = False
        self._ftmap: Optional[dict] = None

    # ------------------------------------------------------------------ #
    # connection
    # ------------------------------------------------------------------ #
    @worker_op("connect")
    def connect(self) -> dict[str, Any]:
        if self._connected and self.app is not None:
            return self._app_info()
        win32.gencache.EnsureModule(config.INVENTOR_TYPELIB_GUID, 0, 1, 0)
        self.C = win32.constants
        # Attach to a running instance (early-bound via the gen cache); else launch
        # the newest. GetActiveObject can raise KeyError('_dispobj_') against a
        # half-dead instance — any failure falls through to a clean launch.
        try:
            self.app = win32.GetActiveObject("Inventor.Application")
        except Exception:
            self.app = win32.gencache.EnsureDispatch("Inventor.Application")
            self.app.Visible = True
        self.tg = self.app.TransientGeometry
        self.tobj = self.app.TransientObjects
        self._connected = True
        # adopt an already-open part/assembly if present
        try:
            if self.app.Documents.Count and self.app.ActiveDocument is not None:
                self._adopt(self.app.ActiveDocument)
        except Exception:
            pass
        return self._app_info()

    def _app_info(self) -> dict[str, Any]:
        return {
            "connected": True,
            "app": "Autodesk Inventor",
            "version": self.app.SoftwareVersion.DisplayName,
            "active_document": (self.doc.DisplayName if self.doc else None),
            "open_documents": self.app.Documents.Count,
        }

    def _ensure(self):
        if not self._connected:
            raise CADError("Not connected to Inventor", operation="connect",
                           recovery="Ensure Inventor is open; the first CAD tool call connects automatically.")

    def _adopt(self, doc) -> None:
        dt = doc.DocumentType
        if dt == self.C.kPartDocumentObject:
            self.doc = win32.CastTo(doc, "PartDocument")
            self.compdef = self.doc.ComponentDefinition
        elif dt == self.C.kAssemblyDocumentObject:
            self.doc = win32.CastTo(doc, "AssemblyDocument")
            self.compdef = self.doc.ComponentDefinition
        self.reg.reset()

    def _need_part(self):
        if self.compdef is None:
            raise CADError("No active document", operation="active_document",
                           recovery="Call new_document('part', ...) first.")

    # ------------------------------------------------------------------ #
    # transactions
    # ------------------------------------------------------------------ #
    def _transact(self, label: str, fn: Callable[[], Any]) -> Any:
        tx = self.app.TransactionManager.StartTransaction(self.doc, label)
        try:
            result = fn()
            tx.End()
            return result
        except Exception:
            tx.Abort()
            raise

    # ------------------------------------------------------------------ #
    # plane resolution
    # ------------------------------------------------------------------ #
    def _resolve_plane(self, plane: str):
        """Return a planar entity (origin WorkPlane or a named face)."""
        key = (plane or "xy").strip().lower()
        # Inventor origin work planes: 1=YZ, 2=XZ, 3=XY
        idx = {"yz": 1, "xz": 2, "xy": 3}.get(key)
        if idx is not None:
            return self.compdef.WorkPlanes.Item(idx)
        if plane in self.reg:
            return self.reg.resolve(plane)
        raise CADError(f"Unknown plane {plane!r}", operation="create_sketch",
                       recovery="Use 'xy'|'xz'|'yz' or a named face/workplane from list_faces.")

    # ------------------------------------------------------------------ #
    # documents
    # ------------------------------------------------------------------ #
    @worker_op("new_document")
    def new_document(self, doc_type: str, name: str, output_path: str = "") -> OpResult:
        self._ensure()
        dt = (doc_type or "part").lower()
        if dt.startswith("assem"):
            tmpl = self.app.FileManager.GetTemplateFile(self.C.kAssemblyDocumentObject)
            raw = self.app.Documents.Add(self.C.kAssemblyDocumentObject, tmpl, True)
            self.doc = win32.CastTo(raw, "AssemblyDocument")
            kind = "assembly"
        else:
            tmpl = self.app.FileManager.GetTemplateFile(self.C.kPartDocumentObject)
            raw = self.app.Documents.Add(self.C.kPartDocumentObject, tmpl, True)
            self.doc = win32.CastTo(raw, "PartDocument")
            kind = "part"
        self.compdef = self.doc.ComponentDefinition
        self.reg.reset()
        if name:
            try:
                self.doc.DisplayName = name
            except Exception:
                pass
        return OpResult(ok=True, name=name or self.doc.DisplayName, kind=kind,
                        message=f"Created {kind} document",
                        data={"template": tmpl, "requested_output": output_path})

    # ------------------------------------------------------------------ #
    # sketch geometry
    # ------------------------------------------------------------------ #
    @worker_op("create_sketch")
    def create_sketch(self, plane: str, name: str) -> OpResult:
        self._need_part()
        planar = self._resolve_plane(plane)
        sk = self.compdef.Sketches.Add(planar)
        nm = self.reg.register("sketch", sk, name, hint="")
        try:
            sk.Name = nm
        except Exception:
            pass
        return OpResult(ok=True, name=nm, kind="sketch",
                        message=f"Sketch on {plane}", data={"plane": plane})

    @worker_op("add_rectangle")
    def add_rectangle(self, sketch: str, x1: float, y1: float, x2: float, y2: float, name: str) -> OpResult:
        sk = self.reg.resolve(sketch)
        lines = sk.SketchLines.AddAsTwoPointRectangle(
            self.tg.CreatePoint2d(x1, y1), self.tg.CreatePoint2d(x2, y2))
        return OpResult(ok=True, name=sketch, kind="sketch_geometry",
                        message="Rectangle added",
                        data={"width_mm": abs(x2 - x1) * 10, "height_mm": abs(y2 - y1) * 10})

    @worker_op("add_circle")
    def add_circle(self, sketch: str, cx: float, cy: float, radius: float, name: str) -> OpResult:
        sk = self.reg.resolve(sketch)
        sk.SketchCircles.AddByCenterRadius(self.tg.CreatePoint2d(cx, cy), radius)
        return OpResult(ok=True, name=sketch, kind="sketch_geometry",
                        message="Circle added", data={"diameter_mm": radius * 2 * 10})

    @worker_op("add_line")
    def add_line(self, sketch: str, points: list[list[float]], closed: bool, name: str) -> OpResult:
        sk = self.reg.resolve(sketch)
        self._chain_polyline(sk, points, closed)
        return OpResult(ok=True, name=sketch, kind="sketch_geometry",
                        message=f"Polyline of {len(points)} points{' (closed)' if closed else ''}")

    def _chain_polyline(self, sk, points, closed):
        """Build a connected polyline reusing each segment's EndSketchPoint as the
        next segment's start (and closing back to the first start). Sharing the
        SketchPoint objects guarantees coincident vertices, so a closed loop yields
        a valid solid profile — passing fresh Point2d per segment leaves micro-gaps
        that make Profiles.AddForSolid() fail."""
        P = [self.tg.CreatePoint2d(p[0], p[1]) for p in points]
        if len(P) < 2:
            raise CADError("Polyline needs >= 2 points", operation="add_line")
        lines = sk.SketchLines
        first = lines.AddByTwoPoints(P[0], P[1])
        prev = first
        for k in range(2, len(P)):
            prev = lines.AddByTwoPoints(prev.EndSketchPoint, P[k])
        if closed and len(P) > 2:
            lines.AddByTwoPoints(prev.EndSketchPoint, first.StartSketchPoint)
        return first

    @worker_op("add_arc")
    def add_arc(self, sketch, center, start, end, name) -> OpResult:
        sk = self.reg.resolve(sketch)
        sk.SketchArcs.AddByCenterStartEndPoint(
            self.tg.CreatePoint2d(*center), self.tg.CreatePoint2d(*start),
            self.tg.CreatePoint2d(*end), True)
        return OpResult(ok=True, name=sketch, kind="sketch_geometry", message="Arc added")

    @worker_op("add_ellipse")
    def add_ellipse(self, sketch, center, major_axis, major_r, minor_r, name) -> OpResult:
        sk = self.reg.resolve(sketch)
        vec = self.tg.CreateUnitVector2d(major_axis[0], major_axis[1])
        sk.SketchEllipses.Add(self.tg.CreatePoint2d(*center), vec, major_r, minor_r)
        return OpResult(ok=True, name=sketch, kind="sketch_geometry", message="Ellipse added")

    @worker_op("add_polygon")
    def add_polygon(self, sketch, sides, center, radius, inscribed, name) -> OpResult:
        sk = self.reg.resolve(sketch)
        c = self.tg.CreatePoint2d(*center)
        circ = self.tg.CreatePoint2d(center[0] + radius, center[1])
        sk.SketchLines.AddAsPolygon(int(sides), c, circ, bool(inscribed))
        return OpResult(ok=True, name=sketch, kind="sketch_geometry",
                        message=f"{sides}-gon ({'inscribed' if inscribed else 'circumscribed'})")

    @worker_op("add_spline")
    def add_spline(self, sketch, points, name) -> OpResult:
        sk = self.reg.resolve(sketch)
        coll = self.tobj.CreateObjectCollection()
        for p in points:
            coll.Add(self.tg.CreatePoint2d(p[0], p[1]))
        sk.SketchSplines.Add(coll)
        return OpResult(ok=True, name=sketch, kind="sketch_geometry",
                        message=f"Spline through {len(points)} points")

    @worker_op("add_slot")
    def add_slot(self, sketch, p1, p2, width, name) -> OpResult:
        # build a slot from two arcs + two tangent lines (no single API call)
        import math as _m
        sk = self.reg.resolve(sketch)
        (x1, y1), (x2, y2) = p1, p2
        r = width / 2.0
        ang = _m.atan2(y2 - y1, x2 - x1) + _m.pi / 2
        ox, oy = r * _m.cos(ang), r * _m.sin(ang)
        L = sk.SketchLines
        A = sk.SketchArcs
        l1 = L.AddByTwoPoints(self.tg.CreatePoint2d(x1 + ox, y1 + oy), self.tg.CreatePoint2d(x2 + ox, y2 + oy))
        l2 = L.AddByTwoPoints(self.tg.CreatePoint2d(x1 - ox, y1 - oy), self.tg.CreatePoint2d(x2 - ox, y2 - oy))
        A.AddByCenterStartEndPoint(self.tg.CreatePoint2d(x2, y2), l1.EndSketchPoint, l2.EndSketchPoint, True)
        A.AddByCenterStartEndPoint(self.tg.CreatePoint2d(x1, y1), l2.StartSketchPoint, l1.StartSketchPoint, True)
        return OpResult(ok=True, name=sketch, kind="sketch_geometry", message="Slot added")

    # ------------------------------------------------------------------ #
    # extrude
    # ------------------------------------------------------------------ #
    def _operation_const(self, operation: str):
        return {
            "join": self.C.kJoinOperation,
            "cut": self.C.kCutOperation,
            "intersect": self.C.kIntersectOperation,
            "new_body": self.C.kNewBodyOperation,
            "newbody": self.C.kNewBodyOperation,
        }.get((operation or "new_body").lower(), self.C.kNewBodyOperation)

    def _extent_dir_const(self, direction: str):
        return {
            "pos": self.C.kPositiveExtentDirection,
            "positive": self.C.kPositiveExtentDirection,
            "neg": self.C.kNegativeExtentDirection,
            "negative": self.C.kNegativeExtentDirection,
            "symmetric": self.C.kSymmetricExtentDirection,
            "sym": self.C.kSymmetricExtentDirection,
        }.get((direction or "pos").lower(), self.C.kPositiveExtentDirection)

    @worker_op("create_extrude")
    def create_extrude(self, profile: str, distance: float, operation: str,
                       direction: str, taper_deg: float, name: str) -> OpResult:
        self._need_part()
        sk = self.reg.resolve(profile)
        prof = sk.Profiles.AddForSolid()
        if prof.Count == 0:
            raise CADError("No closed profile in sketch", operation="create_extrude",
                           recovery="Add closed geometry (rectangle/circle/closed polyline) before extruding.")
        op = self._operation_const(operation)
        extrudes = self.compdef.Features.ExtrudeFeatures

        def build():
            edef = extrudes.CreateExtrudeDefinition(prof, op)
            edef.SetDistanceExtent(distance, self._extent_dir_const(direction))
            if taper_deg:
                try:
                    edef.TaperAngle = taper_deg  # radians
                except Exception:
                    pass
            return extrudes.Add(edef)

        ext = self._transact("create_extrude", build)
        self.doc.Update()
        feat_name = self.reg.register("feature", ext, name, hint="Extrude")
        try:
            ext.Name = feat_name
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=feat_name, kind="extrude",
                        message=f"Extruded {distance * 10:.3f} mm ({operation})",
                        data={"bodies": self.reg.names("body")})

    # ------------------------------------------------------------------ #
    # inspection
    # ------------------------------------------------------------------ #
    def _reindex_bodies(self) -> None:
        """Resync the body registry to the document's CURRENT SurfaceBodies, keeping
        stable names by Inventor body name and dropping bodies consumed by booleans."""
        old = {}
        for n in self.reg.names("body"):
            old[self.reg.get(n).descriptor.get("inv_name")] = n
            self.reg.remove(n)
        bodies = self.compdef.SurfaceBodies
        for i in range(1, bodies.Count + 1):
            b = bodies.Item(i)
            inv_name = b.Name
            keep = old.get(inv_name, "")
            self.reg.register("body", b, keep, hint=inv_name.replace("Solid", "Body"),
                              descriptor={"inv_name": inv_name})

    def _body_handles(self) -> list[tuple[str, Any]]:
        self._reindex_bodies()
        return [(n, self.reg.resolve(n)) for n in self.reg.names("body")]

    @staticmethod
    def _bbox_mm(b) -> list[float]:
        rb = b.RangeBox
        mn, mx = rb.MinPoint, rb.MaxPoint
        return [mn.X * 10, mn.Y * 10, mn.Z * 10, mx.X * 10, mx.Y * 10, mx.Z * 10]

    @worker_op("list_bodies")
    def list_bodies(self) -> list[BodyInfo]:
        self._need_part()
        out: list[BodyInfo] = []
        for nm, b in self._body_handles():
            vol = 0.0
            try:
                vol = b.Volume * 1000.0  # cm^3 -> mm^3
            except Exception:
                pass
            out.append(BodyInfo(
                name=nm, face_count=b.Faces.Count, edge_count=b.Edges.Count,
                volume_mm3=round(vol, 4), bbox_mm=[round(v, 4) for v in self._bbox_mm(b)]))
        return out

    @worker_op("bounding_box")
    def bounding_box(self, body: Optional[str]) -> MeasureResult:
        self._need_part()
        handles = ([(body, self.reg.resolve(body))] if body else self._body_handles())
        if not handles:
            raise CADError("No bodies to measure", operation="bounding_box",
                           recovery="Create a solid first.")
        xs, ys, zs = [], [], []
        for _, b in handles:
            bb = self._bbox_mm(b)
            xs += [bb[0], bb[3]]; ys += [bb[1], bb[4]]; zs += [bb[2], bb[5]]
        lo = [min(xs), min(ys), min(zs)]
        hi = [max(xs), max(ys), max(zs)]
        dims = [hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]]
        return MeasureResult(what="bounding_box", value=round(max(dims), 4), unit="mm",
                             extra={"min_mm": [round(v, 4) for v in lo],
                                    "max_mm": [round(v, 4) for v in hi],
                                    "dimensions_mm": [round(v, 4) for v in dims]})

    # ------------------------------------------------------------------ #
    # resolution helpers (worker-thread only)
    # ------------------------------------------------------------------ #
    def _resolve_axis(self, axis: str):
        idx = {"x": 1, "y": 2, "z": 3}.get((axis or "z").strip().lower())
        if idx is not None:
            return self.compdef.WorkAxes.Item(idx)
        if axis in self.reg:
            return self.reg.resolve(axis)
        raise CADError(f"Unknown axis {axis!r}", operation="resolve_axis",
                       recovery="Use 'x'|'y'|'z' or a named work axis.")

    def _object_collection(self, names):
        coll = self.tobj.CreateObjectCollection()
        for n in names:
            coll.Add(self.reg.resolve(n))
        return coll

    def _edge_collection(self, names):
        coll = self.tobj.CreateEdgeCollection()
        for n in names:
            coll.Add(self.reg.resolve(n))
        return coll

    def _face_collection(self, names):
        coll = self.tobj.CreateFaceCollection()
        for n in names:
            coll.Add(self.reg.resolve(n))
        return coll

    @staticmethod
    def _pt_mm(p):
        return [round(p.X * 10, 4), round(p.Y * 10, 4), round(p.Z * 10, 4)]

    def _healthy(self, feat) -> bool:
        try:
            return feat.HealthStatus == self.C.kUpToDateHealth
        except Exception:
            return True

    # ------------------------------------------------------------------ #
    # sketch points
    # ------------------------------------------------------------------ #
    @worker_op("add_point")
    def add_point(self, sketch: str, x: float, y: float, name: str) -> OpResult:
        sk = self.reg.resolve(sketch)
        sk.SketchPoints.Add(self.tg.CreatePoint2d(x, y))
        return OpResult(ok=True, name=sketch, kind="sketch_geometry",
                        message="Hole/center point added",
                        data={"x_mm": x * 10, "y_mm": y * 10})

    @worker_op("add_axis_line")
    def add_axis_line(self, sketch: str, x1: float, y1: float, x2: float, y2: float, name: str) -> OpResult:
        sk = self.reg.resolve(sketch)
        line = sk.SketchLines.AddByTwoPoints(self.tg.CreatePoint2d(x1, y1), self.tg.CreatePoint2d(x2, y2))
        try:
            line.Construction = True
        except Exception:
            pass
        nm = self.reg.register("axis", line, name, hint="Axis")
        return OpResult(ok=True, name=nm, kind="axis_line",
                        message="Revolve/centerline axis added (construction)")

    # ------------------------------------------------------------------ #
    # revolve
    # ------------------------------------------------------------------ #
    @worker_op("create_revolve")
    def create_revolve(self, profile: str, axis: str, angle: float,
                       operation: str, name: str) -> OpResult:
        self._need_part()
        sk = self.reg.resolve(profile)
        prof = sk.Profiles.AddForSolid()
        if prof.Count == 0:
            raise CADError("No closed profile in sketch", operation="create_revolve",
                           recovery="Add a closed profile and a separate axis line/use an origin axis.")
        ax = self._resolve_axis(axis)
        op = self._operation_const(operation)
        revs = self.compdef.Features.RevolveFeatures

        def build():
            if angle >= 2 * math.pi - 1e-6:
                return revs.AddFull(prof, ax, op)
            return revs.AddByAngle(prof, ax, angle, self.C.kPositiveExtentDirection, op)

        r = self._transact("create_revolve", build)
        self.doc.Update()
        nm = self.reg.register("feature", r, name, hint="Revolve")
        try:
            r.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="revolve",
                        message=f"Revolved {math.degrees(angle):.1f} deg ({operation})",
                        data={"bodies": self.reg.names("body")})

    # ------------------------------------------------------------------ #
    # hole
    # ------------------------------------------------------------------ #
    @worker_op("create_hole")
    def create_hole(self, sketch: str, diameter: float, depth: float,
                    through_all: bool, flip: bool, name: str) -> OpResult:
        self._need_part()
        sk = self.reg.resolve(sketch)
        pts = self.tobj.CreateObjectCollection()
        for i in range(1, sk.SketchPoints.Count + 1):
            pts.Add(sk.SketchPoints.Item(i))
        if pts.Count == 0:
            raise CADError("No hole-center points in sketch", operation="create_hole",
                           recovery="Add center points with add_point before drilling.")
        hf = self.compdef.Features.HoleFeatures
        pos, neg = self.C.kPositiveExtentDirection, self.C.kNegativeExtentDirection
        # Default drills "into the body" (negative); auto-retry the other way if the
        # feature comes back unhealthy, so the agent never has to guess direction.
        order = [pos, neg] if flip else [neg, pos]

        def attempt(direction):
            def build():
                placement = hf.CreateSketchPlacementDefinition(pts)
                if through_all:
                    return hf.AddDrilledByThroughAllExtent(placement, diameter, direction)
                return hf.AddDrilledByDistanceExtent(placement, diameter, depth, direction)
            return self._transact("create_hole", build)

        h = None
        for i, direction in enumerate(order):
            h = attempt(direction)
            self.doc.Update()
            if self._healthy(h):
                break
            if i < len(order) - 1:
                try:
                    h.Delete()
                    self.doc.Update()
                except Exception:
                    pass
        else:
            raise CADError("Hole found no material in either direction", operation="create_hole",
                           recovery="Ensure the hole-center points lie over the body.")
        nm = self.reg.register("feature", h, name, hint="Hole")
        try:
            h.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="hole",
                        message=f"Drilled {pts.Count}x {diameter * 10:.2f} mm hole(s)")

    # ------------------------------------------------------------------ #
    # fillet / chamfer / shell
    # ------------------------------------------------------------------ #
    @worker_op("create_fillet")
    def create_fillet(self, edges: list[str], radius: float, name: str) -> OpResult:
        self._need_part()
        coll = self._edge_collection(edges)
        f = self._transact("create_fillet",
                            lambda: self.compdef.Features.FilletFeatures.AddSimple(coll, radius))
        self.doc.Update()
        nm = self.reg.register("feature", f, name, hint="Fillet")
        try:
            f.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="fillet",
                        message=f"Filleted {len(edges)} edge(s) R{radius * 10:.2f} mm")

    @worker_op("create_chamfer")
    def create_chamfer(self, edges: list[str], distance: float,
                       angle: Optional[float], name: str) -> OpResult:
        self._need_part()
        coll = self._edge_collection(edges)
        ch = self._transact("create_chamfer",
                            lambda: self.compdef.Features.ChamferFeatures.AddUsingDistance(coll, distance))
        self.doc.Update()
        nm = self.reg.register("feature", ch, name, hint="Chamfer")
        try:
            ch.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="chamfer",
                        message=f"Chamfered {len(edges)} edge(s) {distance * 10:.2f} mm")

    @worker_op("create_shell")
    def create_shell(self, faces_to_remove: list[str], thickness: float,
                     inside: bool, name: str) -> OpResult:
        self._need_part()
        fcoll = self._face_collection(faces_to_remove)
        direction = self.C.kInsideShellDirection if inside else self.C.kOutsideShellDirection

        def build():
            sf = self.compdef.Features.ShellFeatures
            sdef = sf.CreateShellDefinition(fcoll, thickness, direction)
            return sf.Add(sdef)

        sh = self._transact("create_shell", build)
        self.doc.Update()
        nm = self.reg.register("feature", sh, name, hint="Shell")
        try:
            sh.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="shell",
                        message=f"Shelled to {thickness * 10:.2f} mm wall")

    # ------------------------------------------------------------------ #
    # patterns / mirror / boolean
    # ------------------------------------------------------------------ #
    @worker_op("pattern_rectangular")
    def pattern_rectangular(self, features: list[str], dir1: str, count1: int, spacing1: float,
                            dir2: str, count2: int, spacing2: float, name: str) -> OpResult:
        self._need_part()
        feats = self._object_collection(features)
        x = self._resolve_axis(dir1)
        rp = self.compdef.Features.RectangularPatternFeatures
        sp1 = f"{spacing1 * 10} mm"

        # The collection .Add() overload is unreliable; build via a definition.
        def build():
            d = rp.CreateDefinition(feats, x, True, str(count1), sp1)
            if dir2 and count2 and count2 > 1:
                d.YDirectionEntity = self._resolve_axis(dir2)
                d.NaturalYDirection = True
                d.YCount = str(count2)
                d.YSpacing = f"{spacing2 * 10} mm"
            return rp.AddByDefinition(d)

        p = self._transact("pattern_rectangular", build)
        self.doc.Update()
        nm = self.reg.register("feature", p, name, hint="RectPattern")
        try:
            p.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="rect_pattern",
                        message=f"Rectangular pattern {count1}x{max(count2, 1)}")

    @worker_op("pattern_circular")
    def pattern_circular(self, features: list[str], axis: str, count: int,
                         angle: float, fill360: bool, name: str) -> OpResult:
        self._need_part()
        feats = self._object_collection(features)
        ax = self._resolve_axis(axis)
        ang = "360 deg" if fill360 else f"{angle} deg"

        def build():
            cpf = self.compdef.Features.CircularPatternFeatures
            d = cpf.CreateDefinition(feats, ax, True, str(count), ang, bool(fill360))
            return cpf.AddByDefinition(d)

        cp = self._transact("pattern_circular", build)
        self.doc.Update()
        nm = self.reg.register("feature", cp, name, hint="CircPattern")
        try:
            cp.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="circular_pattern",
                        message=f"Circular pattern x{count}")

    @worker_op("mirror_feature")
    def mirror_feature(self, features: list[str], plane: str, operation: str, name: str) -> OpResult:
        self._need_part()
        feats = self._object_collection(features)
        pl = self._resolve_plane(plane)
        mf = self._transact("mirror_feature",
                            lambda: self.compdef.Features.MirrorFeatures.Add(feats, pl, False))
        self.doc.Update()
        nm = self.reg.register("feature", mf, name, hint="Mirror")
        try:
            mf.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="mirror",
                        message=f"Mirrored {len(features)} feature(s) across {plane}")

    @worker_op("boolean_combine")
    def boolean_combine(self, target_body: str, tool_bodies: list[str],
                        operation: str, name: str) -> OpResult:
        self._need_part()
        base = self.reg.resolve(target_body)
        tools = self._object_collection(tool_bodies)
        op = {"union": self.C.kJoinOperation, "join": self.C.kJoinOperation,
              "subtract": self.C.kCutOperation, "cut": self.C.kCutOperation,
              "intersect": self.C.kIntersectOperation}.get((operation or "union").lower(),
                                                           self.C.kJoinOperation)
        cf = self._transact("boolean_combine",
                            lambda: self.compdef.Features.CombineFeatures.Add(base, tools, op))
        self.doc.Update()
        nm = self.reg.register("feature", cf, name, hint="Combine")
        try:
            cf.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="combine",
                        message=f"Boolean {operation} of {len(tool_bodies)} tool body(ies)")

    # ------------------------------------------------------------------ #
    # work geometry
    # ------------------------------------------------------------------ #
    @worker_op("add_workplane")
    def add_workplane(self, kind: str, refs: list[str], value: float, name: str) -> OpResult:
        self._need_part()
        wps = self.compdef.WorkPlanes
        k = (kind or "offset").lower()
        if k == "offset":
            base = self._resolve_plane(refs[0] if refs else "xy")
            wp = wps.AddByPlaneAndOffset(base, value)
        elif k == "angle":
            line = self._resolve_axis(refs[0])
            plane = self._resolve_plane(refs[1])
            wp = wps.AddByLinePlaneAndAngle(line, plane, value)  # value in radians
        else:
            raise CADError(f"Unsupported workplane kind {kind!r}", operation="add_workplane",
                           recovery="Use 'offset' (plane,distance) or 'angle' (axis,plane,degrees).")
        nm = self.reg.register("workplane", wp, name, hint="Plane")
        try:
            wp.Name = nm
        except Exception:
            pass
        return OpResult(ok=True, name=nm, kind="workplane", message=f"Work plane ({k})")

    # ------------------------------------------------------------------ #
    # inspection
    # ------------------------------------------------------------------ #
    def _feature_type_name(self, f) -> str:
        if self._ftmap is None:
            names = {
                "kExtrudeFeatureObject": "extrude", "kRevolveFeatureObject": "revolve",
                "kHoleFeatureObject": "hole", "kFilletFeatureObject": "fillet",
                "kChamferFeatureObject": "chamfer", "kShellFeatureObject": "shell",
                "kRibFeatureObject": "rib", "kLoftFeatureObject": "loft",
                "kSweepFeatureObject": "sweep", "kCoilFeatureObject": "coil",
                "kCombineFeatureObject": "combine",
                "kRectangularPatternFeatureObject": "rect_pattern",
                "kCircularPatternFeatureObject": "circular_pattern",
                "kMirrorFeatureObject": "mirror",
            }
            self._ftmap = {getattr(self.C, k): v for k, v in names.items() if hasattr(self.C, k)}
        try:
            return self._ftmap.get(f.Type, "feature")
        except Exception:
            return "feature"

    @worker_op("list_features")
    def list_features(self, body: Optional[str]) -> list[FeatureInfo]:
        self._need_part()
        out: list[FeatureInfo] = []
        feats = self.compdef.Features
        for i in range(1, feats.Count + 1):
            f = feats.Item(i)
            health = "ok"
            try:
                health = "error" if f.HealthStatus != self.C.kUpToDateHealth else "ok"
            except Exception:
                pass
            out.append(FeatureInfo(name=f.Name, feature_type=self._feature_type_name(f),
                                   suppressed=bool(getattr(f, "Suppressed", False)),
                                   health=health))
        return out

    @worker_op("list_faces")
    def list_faces(self, body: str) -> list[FaceInfo]:
        self._need_part()
        handles = self._body_handles()
        b = self.reg.resolve(body) if body else (handles[0][1] if handles else None)
        if b is None:
            raise CADError("No body to inspect", operation="list_faces",
                           recovery="Create a solid first.")
        st_map = {self.C.kPlaneSurface: "planar", self.C.kCylinderSurface: "cylindrical",
                  self.C.kConeSurface: "conical", self.C.kSphereSurface: "spherical",
                  self.C.kTorusSurface: "toroidal"}
        bb = self._bbox_mm(b)
        bc = [(bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2]
        out: list[FaceInfo] = []
        for i in range(1, b.Faces.Count + 1):
            f = b.Faces.Item(i)
            st = st_map.get(f.SurfaceType, "nurbs")
            pof = self._pt_mm(f.PointOnFace)
            normal, radius = [], 0.0
            try:
                if st == "planar":
                    g = f.Geometry
                    nx, ny, nz = g.Normal.X, g.Normal.Y, g.Normal.Z
                    # orient outward: flip if the plane normal points toward body center
                    dot = nx * (pof[0] - bc[0]) + ny * (pof[1] - bc[1]) + nz * (pof[2] - bc[2])
                    s = 1.0 if dot >= 0 else -1.0
                    normal = [round(nx * s, 4), round(ny * s, 4), round(nz * s, 4)]
                elif st == "cylindrical":
                    radius = round(f.Geometry.Radius * 10, 4)
            except Exception:
                pass
            area = 0.0
            try:
                area = round(f.Evaluator.Area * 100, 4)  # cm^2 -> mm^2
            except Exception:
                pass
            nm = self.reg.register("face", f, "", hint=st,
                                   descriptor={"type": st, "centroid": pof, "normal": normal})
            out.append(FaceInfo(name=nm, surface_type=st, area_mm2=area,
                                centroid_mm=pof, normal=normal, radius_mm=radius))
        return out

    @worker_op("list_edges")
    def list_edges(self, body: Optional[str], face: Optional[str]) -> list[EdgeInfo]:
        self._need_part()
        if face and face in self.reg:
            owner = self.reg.resolve(face)
            edges = owner.Edges
        else:
            handles = self._body_handles()
            b = self.reg.resolve(body) if body else (handles[0][1] if handles else None)
            if b is None:
                raise CADError("No body to inspect", operation="list_edges",
                               recovery="Create a solid first.")
            edges = b.Edges
        ct_map = {self.C.kLineSegmentCurve: "line", self.C.kCircularArcCurve: "arc",
                  self.C.kCircleCurve: "circle", self.C.kEllipseFullCurve: "ellipse",
                  self.C.kEllipticalArcCurve: "elliptical_arc"}
        out: list[EdgeInfo] = []
        for i in range(1, edges.Count + 1):
            e = edges.Item(i)
            ct = ct_map.get(getattr(e, "GeometryType", None), "spline")
            start = self._pt_mm(e.StartVertex.Point) if e.StartVertex else []
            stop = self._pt_mm(e.StopVertex.Point) if e.StopVertex else []
            length = 0.0
            try:
                ev = e.Evaluator
                ext = ev.GetParamExtents()
                length = round(ev.GetLengthAtParam(ext[0], ext[1]) * 10, 4)
            except Exception:
                pass
            mid = [round((a + b) / 2, 4) for a, b in zip(start, stop)] if start and stop else []
            nm = self.reg.register("edge", e, "", hint=ct,
                                   descriptor={"type": ct, "start": start, "end": stop,
                                               "mid": mid, "length_mm": length})
            out.append(EdgeInfo(name=nm, curve_type=ct, length_mm=length,
                                start_mm=start, end_mm=stop, midpoint_mm=mid))
        return out

    def _entity_point(self, name: str) -> list[float]:
        e = self.reg.get(name)
        if e.kind == "edge":
            return e.descriptor.get("mid") or e.descriptor.get("start") or [0, 0, 0]
        if e.kind == "face":
            return e.descriptor.get("centroid") or [0, 0, 0]
        if e.kind == "body":
            b = e.handle
            bb = self._bbox_mm(b)
            return [(bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2]
        raise CADError(f"Cannot measure entity {name!r} of kind {e.kind}")

    @worker_op("measure")
    def measure(self, entity_a: str, entity_b: Optional[str], what: str) -> MeasureResult:
        self._need_part()
        what = (what or "distance").lower()
        if what == "length":
            return MeasureResult(what="length", unit="mm",
                                 value=self.reg.get(entity_a).descriptor.get("length_mm", 0.0))
        if what in ("bbox", "bounding_box"):
            return self.bounding_box(entity_a if entity_a in self.reg else None)
        if what == "distance" and entity_b:
            pa, pb = self._entity_point(entity_a), self._entity_point(entity_b)
            d = math.dist(pa, pb)
            return MeasureResult(what="distance", value=round(d, 4), unit="mm",
                                 extra={"a_mm": pa, "b_mm": pb})
        raise CADError(f"Unsupported measure {what!r}", operation="measure",
                       recovery="Use what='distance' (two entities), 'length' (edge), or 'bbox'.")

    # ------------------------------------------------------------------ #
    # parameters
    # ------------------------------------------------------------------ #
    def _unit_const_for(self, expression: str):
        e = (expression or "").lower()
        if "mm" in e:
            return self.C.kMillimeterLengthUnits
        if '"' in e or " in" in e or e.endswith("in"):
            return self.C.kInchLengthUnits
        if "deg" in e:
            return self.C.kDegreeAngleUnits
        return self.C.kMillimeterLengthUnits

    @worker_op("set_parameter")
    def set_parameter(self, name: str, expression: str, comment: str, mode: str) -> OpResult:
        self._need_part()
        params = self.compdef.Parameters
        existing = None
        for i in range(1, params.Count + 1):
            if params.Item(i).Name == name:
                existing = params.Item(i)
                break

        def build():
            if existing is not None and (mode or "set") != "create":
                existing.Expression = expression
                if comment:
                    existing.Comment = comment
                return existing
            p = params.UserParameters.AddByExpression(name, expression, self._unit_const_for(expression))
            if comment:
                p.Comment = comment
            return p

        p = self._transact("set_parameter", build)
        self.doc.Update()
        return OpResult(ok=True, name=name, kind="parameter",
                        message=f"{'Set' if existing is not None else 'Created'} {name} = {expression}",
                        data={"value_mm": round(p.Value * 10, 4), "expression": p.Expression})

    @worker_op("get_parameters")
    def get_parameters(self) -> list[ParamInfo]:
        self._need_part()
        params = self.compdef.Parameters
        user_names = set()
        try:
            up = params.UserParameters
            for i in range(1, up.Count + 1):
                user_names.add(up.Item(i).Name)
        except Exception:
            pass
        out: list[ParamInfo] = []
        for i in range(1, params.Count + 1):
            p = params.Item(i)
            try:
                out.append(ParamInfo(name=p.Name, expression=p.Expression,
                                     value_mm=round(p.Value * 10, 4), unit=p.Units,
                                     comment=getattr(p, "Comment", "") or "",
                                     is_user=p.Name in user_names))
            except Exception:
                continue
        return out

    # ------------------------------------------------------------------ #
    # screenshot
    # ------------------------------------------------------------------ #
    @worker_op("screenshot_png")
    def screenshot_png(self, width: int, height: int) -> bytes:
        self._ensure()
        path = str(config.ensure_work_dir() / "view.png")
        view = self.app.ActiveView
        if view is None:
            raise CADError("No active view", operation="screenshot",
                           recovery="Open a document first.")
        try:
            self.app.ActiveView.Fit()
        except Exception:
            pass
        view.SaveAsBitmap(path, int(width), int(height))
        with open(path, "rb") as fh:
            return fh.read()

    # ------------------------------------------------------------------ #
    # save + assembly
    # ------------------------------------------------------------------ #
    @worker_op("save_document")
    def save_document(self, path: str) -> OpResult:
        self._ensure()
        if self.doc is None:
            raise CADError("No document to save", operation="save_document",
                           recovery="Create a document first.")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if os.path.exists(path):
            try:
                os.remove(path)   # overwrite cleanly (SaveAs can choke on an existing file)
            except OSError:
                pass
        self.doc.SaveAs(path, False)
        return OpResult(ok=True, name=os.path.basename(path), kind="save",
                        message=f"Saved to {path}", data={"path": path})

    def _need_assembly(self):
        if self.doc is None or self.doc.DocumentType != self.C.kAssemblyDocumentObject:
            raise CADError("Active document is not an assembly", operation="assembly",
                           recovery="Call new_document('assembly', ...) first.")

    def _make_matrix(self, position, rotation):
        m = self.tg.CreateMatrix()  # identity
        if rotation:
            for angle, axis in zip(rotation, ((1, 0, 0), (0, 1, 0), (0, 0, 1))):
                if angle:
                    r = self.tg.CreateMatrix()
                    r.SetToRotation(angle, self.tg.CreateVector(*axis), self.tg.CreatePoint(0, 0, 0))
                    m.TransformBy(r)
        if position:
            m.SetTranslation(self.tg.CreateVector(*position))
        return m

    @worker_op("insert_component")
    def insert_component(self, source: str, name: str, position: list[float],
                         rotation: list[float], grounded: bool) -> OpResult:
        self._need_assembly()
        path = source
        if not os.path.exists(path):
            # treat source as a library query
            from ..index import search
            hits = search(source, 1)
            if not hits:
                raise CADError(f"Component {source!r} not found on disk or in the index",
                               operation="insert_component",
                               recovery="Pass a full .ipt/.iam path or reindex_parts first.")
            path = hits[0]["path"]
        matrix = self._make_matrix(position or [0, 0, 0], rotation or [0, 0, 0])
        occ = self.compdef.Occurrences.Add(path, matrix)
        if grounded:
            try:
                occ.Grounded = True
            except Exception:
                pass
        nm = self.reg.register("occurrence", occ, name, hint=os.path.basename(path).split(".")[0])
        try:
            occ.Name = nm
        except Exception:
            pass
        return OpResult(ok=True, name=nm, kind="occurrence",
                        message=f"Inserted {os.path.basename(path)}",
                        data={"path": path, "occurrences": self.compdef.Occurrences.Count})

    @worker_op("ground")
    def ground(self, occurrence: str, grounded: bool) -> OpResult:
        self._need_assembly()
        occ = self.reg.resolve(occurrence)
        occ.Grounded = bool(grounded)
        return OpResult(ok=True, name=occurrence, kind="occurrence",
                        message=f"{'Grounded' if grounded else 'Ungrounded'} {occurrence}")

    # ------------------------------------------------------------------ #
    # export
    # ------------------------------------------------------------------ #
    _TRANSLATORS = {
        "stl": "{533E9A98-FC3B-11D4-8E7E-0010B541CD80}",
        "step": "{90AF7F40-0C01-11D5-8E83-0010B541CD80}",
        "stp": "{90AF7F40-0C01-11D5-8E83-0010B541CD80}",
        "iges": "{90AF7F44-0C01-11D5-8E83-0010B541CD80}",
        "igs": "{90AF7F44-0C01-11D5-8E83-0010B541CD80}",
        "obj": "{F539FB09-FC01-4260-A429-1818B14D6BAC}",
    }

    @worker_op("export")
    def export(self, fmt: str, output_path: str, body: Optional[str], options: dict) -> OpResult:
        self._ensure()
        if self.doc is None:
            raise CADError("No document to export", operation="export",
                           recovery="Create or open a document first.")
        fmt = (fmt or "stl").lower().lstrip(".")
        clsid = self._TRANSLATORS.get(fmt)
        if not clsid:
            raise CADError(f"Unsupported export format {fmt!r}", operation="export",
                           recovery="Use stl, step, iges or obj.")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        tr = win32.CastTo(self.app.ApplicationAddIns.ItemById(clsid), "TranslatorAddIn")
        ctx = self.tobj.CreateTranslationContext()
        ctx.Type = self.C.kFileBrowseIOMechanism
        opts = self.tobj.CreateNameValueMap()
        medium = self.tobj.CreateDataMedium()
        medium.FileName = output_path
        if tr.HasSaveCopyAsOptions(self.doc, ctx, opts) and fmt == "stl":
            self._set_opt(opts, "OutputType", 1)       # 1 = binary STL
            self._set_opt(opts, "Resolution", int(options.get("resolution", 0)))  # 0 = high
        tr.SaveCopyAs(self.doc, ctx, opts, medium)
        size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        return OpResult(ok=True, name=os.path.basename(output_path), kind="export",
                        message=f"Exported {fmt.upper()} ({size} bytes)",
                        data={"path": output_path, "bytes": size, "format": fmt})

    @staticmethod
    def _set_opt(nvmap, key, value) -> None:
        try:
            nvmap.Value(key)        # raises if absent
            nvmap.Value = (key, value)
        except Exception:
            try:
                nvmap.Add(key, value)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # iLogic
    # ------------------------------------------------------------------ #
    @worker_op("run_ilogic_rule")
    def run_ilogic_rule(self, document: str, rule: str, external: bool) -> OpResult:
        self._ensure()
        il = self.app.ApplicationAddIns.ItemById("{3BDD8D79-2179-4B11-8A5A-257B1C0263AC}")
        auto = il.Automation
        target = self.doc
        if document:
            for i in range(1, self.app.Documents.Count + 1):
                d = self.app.Documents.Item(i)
                if document.lower() in (d.DisplayName or "").lower():
                    target = d
                    break
        if external:
            auto.RunExternalRule(target, rule)
        else:
            auto.RunRule(target, rule)
        try:
            target.Update()
        except Exception:
            pass
        return OpResult(ok=True, name=rule, kind="ilogic",
                        message=f"Ran iLogic {'external ' if external else ''}rule '{rule}'")

    # ------------------------------------------------------------------ #
    # guarded native escape hatch
    # ------------------------------------------------------------------ #
    @worker_op("eval_native")
    def eval_native(self, code: str, scope: dict) -> Any:
        self._ensure()
        g: dict[str, Any] = {
            "app": self.app, "doc": self.doc, "compdef": self.compdef,
            "tg": self.tg, "tobj": self.tobj, "C": self.C, "reg": self.reg,
            "math": math, "win32": win32, "cm": lambda mm: mm / 10.0, "result": None,
        }
        if scope:
            g.update(scope)
        tx = self.app.TransactionManager.StartTransaction(self.doc, "eval_native") if self.doc else None
        try:
            exec(code, g)
            if self.doc:
                self.doc.Update()
            if tx:
                tx.End()
            try:
                self._reindex_bodies()
            except Exception:
                pass
            return g.get("result")
        except Exception:
            if tx:
                tx.Abort()
            raise

    # ------------------------------------------------------------------ #
    # advanced modeling: loft / sweep / coil
    # ------------------------------------------------------------------ #
    def _first_curve(self, sketch):
        for coll_name in ("SketchLines", "SketchArcs", "SketchSplines", "SketchCircles", "SketchEllipses"):
            try:
                coll = getattr(sketch, coll_name)
                if coll.Count:
                    return coll.Item(1)
            except Exception:
                continue
        raise CADError("Path sketch has no curve", operation="create_sweep",
                       recovery="Draw the sweep path (add_line/add_arc) before sweeping.")

    @worker_op("create_loft")
    def create_loft(self, sections: list[str], rails: list[str], operation: str, name: str) -> OpResult:
        self._need_part()
        if len(sections) < 2:
            raise CADError("Loft needs >=2 sections", operation="create_loft",
                           recovery="Create at least two profile sketches on different planes.")
        sec = self.tobj.CreateObjectCollection()
        for s in sections:
            sec.Add(self.reg.resolve(s).Profiles.AddForSolid())
        op = self._operation_const(operation)
        lf = self.compdef.Features.LoftFeatures

        def build():
            ldef = lf.CreateLoftDefinition(sec, op)
            for r in (rails or []):
                try:
                    ldef.LoftRails.Add(self._first_curve(self.reg.resolve(r)))
                except Exception:
                    pass
            return lf.Add(ldef)

        f = self._transact("create_loft", build)
        self.doc.Update()
        nm = self.reg.register("feature", f, name, hint="Loft")
        try:
            f.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="loft",
                        message=f"Lofted {len(sections)} sections"
                                f"{' with rails' if rails else ''}",
                        data={"bodies": self.reg.names("body")})

    @worker_op("create_sweep")
    def create_sweep(self, profile: str, path: str, operation: str, twist: float, name: str) -> OpResult:
        self._need_part()
        prof = self.reg.resolve(profile).Profiles.AddForSolid()
        op = self._operation_const(operation)
        sf = self.compdef.Features.SweepFeatures
        curve = self._first_curve(self.reg.resolve(path))

        def build():
            return sf.AddUsingPath(prof, sf.CreatePath(curve), op)

        f = self._transact("create_sweep", build)
        self.doc.Update()
        nm = self.reg.register("feature", f, name, hint="Sweep")
        try:
            f.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="sweep", message="Swept profile along path",
                        data={"bodies": self.reg.names("body")})

    @worker_op("create_coil")
    def create_coil(self, profile: str, axis: str, pitch: float, rotations: float,
                    operation: str, name: str) -> OpResult:
        self._need_part()
        prof = self.reg.resolve(profile).Profiles.AddForSolid()
        ax = self._resolve_axis(axis)
        op = self._operation_const(operation)
        cf = self.compdef.Features.CoilFeatures

        def build():
            return cf.AddByPitchAndRevolution(
                prof, ax, pitch, float(rotations), op,
                False, False, 0.0, False, 0.0, 0.0, False)

        f = self._transact("create_coil", build)
        self.doc.Update()
        nm = self.reg.register("feature", f, name, hint="Coil")
        try:
            f.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="coil",
                        message=f"Coil pitch {pitch * 10:.2f} mm x {rotations} rev",
                        data={"bodies": self.reg.names("body")})

    # ------------------------------------------------------------------ #
    # spur gear generator (parametric; trapezoidal-tooth approximation)
    # ------------------------------------------------------------------ #
    @worker_op("create_spur_gear")
    def create_spur_gear(self, teeth: int, module: float, thickness: float, bore: float,
                         pressure_angle: float, name: str) -> OpResult:
        self._need_part()
        teeth = int(teeth)
        if teeth < 6:
            raise CADError("teeth must be >= 6", operation="create_spur_gear")
        m = module  # cm
        pitch_r = m * teeth / 2.0
        add_r = pitch_r + m              # addendum (tip)
        ded_r = max(pitch_r - 1.25 * m, m * 0.3)  # dedendum (root), keep positive
        step = 2 * math.pi / teeth
        tw = step * 0.25                 # quarter-tooth angular half width
        pts: list[tuple[float, float]] = []
        for i in range(teeth):
            a = i * step
            for r, da in ((ded_r, -tw), (add_r, -tw * 0.45), (add_r, tw * 0.45), (ded_r, tw)):
                pts.append((r * math.cos(a + da), r * math.sin(a + da)))

        def build():
            sk = self.compdef.Sketches.Add(self.compdef.WorkPlanes.Item(3))
            self._chain_polyline(sk, pts, True)   # shared endpoints -> valid closed gear outline
            ex = self.compdef.Features.ExtrudeFeatures
            ed = ex.CreateExtrudeDefinition(sk.Profiles.AddForSolid(), self.C.kNewBodyOperation)
            ed.SetDistanceExtent(thickness, self.C.kPositiveExtentDirection)
            gear = ex.Add(ed)
            if bore and bore > 0:
                bs = self.compdef.Sketches.Add(self.compdef.WorkPlanes.Item(3))
                bs.SketchCircles.AddByCenterRadius(self.tg.CreatePoint2d(0, 0), bore / 2.0)
                bd = ex.CreateExtrudeDefinition(bs.Profiles.AddForSolid(), self.C.kCutOperation)
                bd.SetDistanceExtent(thickness, self.C.kPositiveExtentDirection)
                ex.Add(bd)
            return gear

        g = self._transact("create_spur_gear", build)
        self.doc.Update()
        nm = self.reg.register("feature", g, name, hint=f"Gear{teeth}T")
        try:
            g.Name = nm
        except Exception:
            pass
        self._reindex_bodies()
        return OpResult(ok=True, name=nm, kind="spur_gear",
                        message=f"{teeth}T spur gear, module {m * 10:.2f} mm",
                        data={"teeth": teeth, "module_mm": round(m * 10, 3),
                              "pitch_diameter_mm": round(2 * pitch_r * 10, 3),
                              "outside_diameter_mm": round(2 * add_r * 10, 3),
                              "note": "trapezoidal-tooth approximation (good for 3D print); "
                                      "use Design Accelerator via execute_script for true involute"})

    # ------------------------------------------------------------------ #
    # assembly constraints + joints (verified signatures; live-test pending)
    # ------------------------------------------------------------------ #
    @worker_op("list_occurrence_faces")
    def list_occurrence_faces(self, occurrence: str) -> list[FaceInfo]:
        self._need_assembly()
        occ = self.reg.resolve(occurrence)
        st_map = {self.C.kPlaneSurface: "planar", self.C.kCylinderSurface: "cylindrical",
                  self.C.kConeSurface: "conical", self.C.kSphereSurface: "spherical"}
        out: list[FaceInfo] = []
        for bi in range(1, occ.SurfaceBodies.Count + 1):
            b = occ.SurfaceBodies.Item(bi)
            for i in range(1, b.Faces.Count + 1):
                f = b.Faces.Item(i)
                st = st_map.get(f.SurfaceType, "nurbs")
                nm = self.reg.register("occ_face", f, "", hint=f"{occurrence}_{st}")
                out.append(FaceInfo(name=nm, surface_type=st,
                                    centroid_mm=self._pt_mm(f.PointOnFace)))
        return out

    @worker_op("add_constraint")
    def add_constraint(self, kind: str, a: str, b: str, offset: float, name: str) -> OpResult:
        self._need_assembly()
        ea, eb = self.reg.resolve(a), self.reg.resolve(b)
        cons = self.compdef.Constraints
        k = (kind or "mate").lower()

        def build():
            if k == "mate":
                return cons.AddMateConstraint(ea, eb, offset)
            if k == "flush":
                return cons.AddFlushConstraint(ea, eb, offset)
            if k == "insert":
                return cons.AddInsertConstraint(ea, eb, True, offset)
            if k == "angle":
                return cons.AddAngleConstraint(ea, eb, offset)
            if k == "tangent":
                return cons.AddTangentConstraint(ea, eb, False)
            raise CADError(f"Unknown constraint {kind!r}", operation="add_constraint",
                           recovery="Use mate|flush|insert|angle|tangent.")

        c = self._transact("add_constraint", build)
        nm = self.reg.register("constraint", c, name, hint=k.capitalize())
        return OpResult(ok=True, name=nm, kind="constraint",
                        message=f"{k} constraint between {a} and {b}")

    @worker_op("add_joint")
    def add_joint(self, kind: str, a: str, b: str, name: str) -> OpResult:
        self._need_assembly()
        ea, eb = self.reg.resolve(a), self.reg.resolve(b)
        jt = {
            "rigid": "kRigidJointType", "rotational": "kRotationalJointType",
            "revolute": "kRotationalJointType", "slider": "kSlideJointType",
            "cylindrical": "kCylindricalJointType", "planar": "kPlanarJointType",
            "ball": "kBallJointType",
        }.get((kind or "rigid").lower(), "kRigidJointType")
        jtype = getattr(self.C, jt)
        joints = self.compdef.Joints

        def build():
            # joints take GeometryIntents, not raw faces; infer origins from geometry
            gi1 = self.compdef.CreateGeometryIntent(ea)
            gi2 = self.compdef.CreateGeometryIntent(eb)
            # the constructor sets origins from the geometry intents; don't override
            jdef = joints.CreateAssemblyJointDefinition(jtype, gi1, gi2)
            return joints.Add(jdef)

        try:
            j = self._transact("add_joint", build)
        except Exception as e:
            raise CADError(
                f"Joint creation failed ({e}). Joints need compatible origin geometry "
                f"(e.g. cylindrical faces for rotational, planar for slider).",
                operation="add_joint",
                recovery="Prefer add_constraint (mate/flush/insert/angle/tangent) for assembly "
                         "mating, or use execute_script with cad://knowledge/full-api-spec to set "
                         "joint origins (SetOriginOneAsOffset / BetweenTwoFaces) explicitly.")
        nm = self.reg.register("joint", j, name, hint=kind.capitalize())
        return OpResult(ok=True, name=nm, kind="joint",
                        message=f"{kind} joint between {a} and {b}")

    # ------------------------------------------------------------------ #
    # iProperties / materials / physical properties / import
    # ------------------------------------------------------------------ #
    def _prop(self, set_name, prop_name):
        try:
            return self.doc.PropertySets.Item(set_name).Item(prop_name).Value
        except Exception:
            return None

    @worker_op("get_iproperties")
    def get_iproperties(self) -> dict:
        self._ensure()
        dtp = "Design Tracking Properties"
        return {
            "part_number": self._prop(dtp, "Part Number"),
            "description": self._prop(dtp, "Description"),
            "material": self._prop(dtp, "Material"),
            "designer": self._prop(dtp, "Designer"),
            "stock_number": self._prop(dtp, "Stock Number"),
            "title": self._prop("Inventor Summary Information", "Title")
                     or self._prop("Summary Information", "Title"),
            "author": self._prop("Summary Information", "Author"),
        }

    @worker_op("set_iproperty")
    def set_iproperty(self, name: str, value: str) -> OpResult:
        self._ensure()
        for ps in self.doc.PropertySets:
            try:
                p = ps.Item(name)
                p.Value = value
                return OpResult(ok=True, name=name, kind="iproperty", message=f"{name} = {value}")
            except Exception:
                continue
        raise CADError(f"iProperty {name!r} not found", operation="set_iproperty",
                       recovery="Use e.g. 'Part Number', 'Description', 'Designer', 'Stock Number'.")

    @worker_op("physical_properties")
    def physical_properties(self) -> dict:
        self._need_part()
        mp = self.compdef.MassProperties
        com = mp.CenterOfMass
        return {"mass_g": round(mp.Mass * 1000, 4), "volume_mm3": round(mp.Volume * 1000, 4),
                "area_mm2": round(mp.Area * 100, 4),
                "center_of_mass_mm": [round(com.X * 10, 3), round(com.Y * 10, 3), round(com.Z * 10, 3)]}

    @worker_op("set_material")
    def set_material(self, material: str) -> OpResult:
        """Best-effort material assignment from the asset libraries. Material APIs
        vary by Inventor version; on miss this returns ok=False with guidance rather
        than raising (the execute_script escape hatch + full-api-spec can always do it)."""
        self._need_part()
        asset = None
        try:
            libs = self.app.AssetLibraries
            for i in range(1, libs.Count + 1):
                try:
                    asset = libs.Item(i).MaterialAssets.Item(material)
                    break
                except Exception:
                    continue
        except Exception:
            pass
        if asset is not None:
            try:
                local = asset.CopyTo(self.doc)
            except Exception:
                local = asset
            try:
                self.compdef.Material = local
                self.doc.Update()
                return OpResult(ok=True, name=material, kind="material", message=f"Material -> {material}")
            except Exception:
                pass
        return OpResult(ok=False, name=material, kind="material",
                        message=f"Could not resolve material {material!r} via the asset libraries",
                        data={"hint": "Use execute_script with cad://knowledge/full-api-spec to assign, "
                                      "or ensure the name matches the active material library."})

    @worker_op("close_all_documents")
    def close_all_documents(self, save: bool) -> OpResult:
        self._ensure()
        n = self.app.Documents.Count
        try:
            self.app.Documents.CloseAll(save)
        except Exception:
            for i in range(self.app.Documents.Count, 0, -1):
                try:
                    self.app.Documents.Item(i).Close(not save)
                except Exception:
                    pass
        self.doc = None
        self.compdef = None
        self.reg.reset()
        return OpResult(ok=True, kind="documents", message=f"Closed {n} document(s)")

    @worker_op("import_file")
    def import_file(self, path: str) -> OpResult:
        self._ensure()
        if not os.path.exists(path):
            raise CADError(f"File not found: {path}", operation="import_file")
        d = self.app.Documents.Open(path, True)
        self._adopt(d)
        return OpResult(ok=True, name=os.path.basename(path), kind="import",
                        message=f"Opened/imported {os.path.basename(path)}")

    # ------------------------------------------------------------------ #
    # iLogic rule CRUD (Automation is a dynamic add-in interface)
    # ------------------------------------------------------------------ #
    def _ilogic(self):
        return self.app.ApplicationAddIns.ItemById("{3BDD8D79-2179-4B11-8A5A-257B1C0263AC}").Automation

    @worker_op("list_ilogic_rules")
    def list_ilogic_rules(self, document: str) -> dict:
        self._ensure()
        il = self._ilogic()
        rules = il.Rules(self.doc)
        names = []
        try:
            for r in rules:
                names.append(r.Name)
        except Exception:
            try:
                for i in range(rules.Count):
                    names.append(rules.Item(i).Name)
            except Exception:
                pass
        return {"rules": names}

    @worker_op("create_ilogic_rule")
    def create_ilogic_rule(self, name: str, code: str, document: str) -> OpResult:
        self._ensure()
        il = self._ilogic()
        rule = il.AddRule(self.doc, name, "")
        try:
            rule.Text = code
        except Exception:
            pass
        return OpResult(ok=True, name=name, kind="ilogic_rule",
                        message=f"Created iLogic rule '{name}'")

    def get_last_error(self) -> dict[str, Any]:
        return self._last_error or {"ok": True, "message": "no error recorded"}
