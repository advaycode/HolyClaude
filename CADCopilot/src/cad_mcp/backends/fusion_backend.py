"""Fusion 360 backend — a thin TCP/JSON client to the in-Fusion add-in.

The add-in (fusion_addin/cad-mcp-fusion-addin) runs inside Fusion and is the only
place adsk APIs are touched; it marshals every call onto Fusion's MAIN thread via a
CustomEvent. This client just serializes the unified calls and maps the responses
back into the shared dataclasses, so the same MCP tool bodies drive either engine.

Distances crossing this boundary are in CENTIMETRES, angles in RADIANS (the tool
layer already converted), matching Fusion's internal units.
"""

from __future__ import annotations

import json
import socket
from typing import Any, Optional

from .. import config
from .base import (
    Backend, CADError, OpResult, BodyInfo, FaceInfo, EdgeInfo,
    FeatureInfo, ParamInfo, MeasureResult,
)


class FusionBackend(Backend):
    name = "fusion"

    def __init__(self) -> None:
        self._last_error: dict = {}

    # ------------------------------------------------------------------ #
    # transport
    # ------------------------------------------------------------------ #
    def _rpc(self, command: str, **args) -> dict:
        payload = json.dumps({"command": command, "args": args}).encode("utf-8") + b"\n"
        try:
            with socket.create_connection((config.FUSION_HOST, config.FUSION_PORT), timeout=40) as s:
                s.sendall(payload)
                buf = b""
                while not buf.endswith(b"\n"):
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
        except OSError as e:
            err = CADError(f"Cannot reach the Fusion add-in on "
                           f"{config.FUSION_HOST}:{config.FUSION_PORT}: {e}",
                           operation=command,
                           recovery="Open Fusion 360 and enable the 'cad-mcp-fusion-addin' add-in (Utilities > Add-Ins).")
            self._last_error = err.to_dict()
            raise err
        try:
            resp = json.loads(buf.decode("utf-8"))
        except Exception:
            raise CADError("Malformed response from Fusion add-in", operation=command)
        if not resp.get("ok", False):
            err = CADError(resp.get("error", "unknown error"), operation=command,
                           recovery=resp.get("recovery", ""))
            self._last_error = err.to_dict()
            raise err
        return resp.get("result", {})

    def _op(self, command: str, **args) -> OpResult:
        r = self._rpc(command, **args)
        return OpResult(ok=True, name=r.get("name", ""), kind=r.get("kind", command),
                        message=r.get("message", ""), data=r.get("data", {}))

    # ------------------------------------------------------------------ #
    # connection
    # ------------------------------------------------------------------ #
    def connect(self) -> dict[str, Any]:
        return self._rpc("connect")

    # ------------------------------------------------------------------ #
    # documents / sketch
    # ------------------------------------------------------------------ #
    def new_document(self, doc_type, name, output_path=""):
        return self._op("new_document", doc_type=doc_type, name=name, output_path=output_path)

    def save_document(self, path):
        return self._op("save_document", path=path)

    def create_sketch(self, plane, name):
        return self._op("create_sketch", plane=plane, name=name)

    def add_rectangle(self, sketch, x1, y1, x2, y2, name):
        return self._op("add_rectangle", sketch=sketch, x1=x1, y1=y1, x2=x2, y2=y2, name=name)

    def add_circle(self, sketch, cx, cy, radius, name):
        return self._op("add_circle", sketch=sketch, cx=cx, cy=cy, radius=radius, name=name)

    def add_line(self, sketch, points, closed, name):
        return self._op("add_line", sketch=sketch, points=points, closed=closed, name=name)

    def add_point(self, sketch, x, y, name):
        return self._op("add_point", sketch=sketch, x=x, y=y, name=name)

    def add_axis_line(self, sketch, x1, y1, x2, y2, name):
        return self._op("add_axis_line", sketch=sketch, x1=x1, y1=y1, x2=x2, y2=y2, name=name)

    # ------------------------------------------------------------------ #
    # features
    # ------------------------------------------------------------------ #
    def create_extrude(self, profile, distance, operation, direction, taper_deg, name):
        return self._op("create_extrude", profile=profile, distance=distance,
                        operation=operation, direction=direction, taper=taper_deg, name=name)

    def create_revolve(self, profile, axis, angle, operation, name):
        return self._op("create_revolve", profile=profile, axis=axis, angle=angle,
                        operation=operation, name=name)

    def create_hole(self, sketch, diameter, depth, through_all, flip, name):
        return self._op("create_hole", sketch=sketch, diameter=diameter, depth=depth,
                        through_all=through_all, flip=flip, name=name)

    def create_fillet(self, edges, radius, name):
        return self._op("create_fillet", edges=edges, radius=radius, name=name)

    def create_chamfer(self, edges, distance, angle, name):
        return self._op("create_chamfer", edges=edges, distance=distance, name=name)

    def create_shell(self, faces_to_remove, thickness, inside, name):
        return self._op("create_shell", faces=faces_to_remove, thickness=thickness,
                        inside=inside, name=name)

    def pattern_rectangular(self, features, dir1, count1, spacing1, dir2, count2, spacing2, name):
        return self._op("pattern_rectangular", features=features, dir1=dir1, count1=count1,
                        spacing1=spacing1, dir2=dir2, count2=count2, spacing2=spacing2, name=name)

    def pattern_circular(self, features, axis, count, angle, fill360, name):
        return self._op("pattern_circular", features=features, axis=axis, count=count,
                        angle=angle, fill360=fill360, name=name)

    def mirror_feature(self, features, plane, operation, name):
        return self._op("mirror_feature", features=features, plane=plane, name=name)

    def boolean_combine(self, target_body, tool_bodies, operation, name):
        return self._op("boolean_combine", target=target_body, tools=tool_bodies,
                        operation=operation, name=name)

    def add_workplane(self, kind, refs, value, name):
        return self._op("add_workplane", kind=kind, refs=refs, value=value, name=name)

    # ------------------------------------------------------------------ #
    # parameters
    # ------------------------------------------------------------------ #
    def set_parameter(self, name, expression, comment, mode):
        return self._op("set_parameter", name=name, expression=expression, comment=comment, mode=mode)

    def get_parameters(self):
        return [ParamInfo(**p) for p in self._rpc("get_parameters").get("items", [])]

    # ------------------------------------------------------------------ #
    # inspection
    # ------------------------------------------------------------------ #
    def list_features(self, body):
        return [FeatureInfo(**f) for f in self._rpc("list_features", body=body).get("items", [])]

    def list_bodies(self):
        return [BodyInfo(**b) for b in self._rpc("list_bodies").get("items", [])]

    def list_faces(self, body):
        return [FaceInfo(**f) for f in self._rpc("list_faces", body=body).get("items", [])]

    def list_edges(self, body, face):
        return [EdgeInfo(**e) for e in self._rpc("list_edges", body=body, face=face).get("items", [])]

    def measure(self, entity_a, entity_b, what):
        return MeasureResult(**self._rpc("measure", entity_a=entity_a, entity_b=entity_b, what=what))

    def bounding_box(self, body):
        return MeasureResult(**self._rpc("bounding_box", body=body))

    def screenshot_png(self, width, height):
        import base64
        r = self._rpc("screenshot_png", width=width, height=height)
        return base64.b64decode(r["png_b64"])

    # ------------------------------------------------------------------ #
    # export / escape hatch
    # ------------------------------------------------------------------ #
    def export(self, fmt, output_path, body, options):
        return self._op("export", fmt=fmt, output_path=output_path, body=body, options=options or {})

    def run_ilogic_rule(self, document, rule, external):
        raise CADError("iLogic is Inventor-only", operation="run_ilogic_rule",
                       recovery="Use parameters / execute_script in Fusion instead.")

    def eval_native(self, code, scope):
        return self._rpc("eval_native", code=code).get("result")

    def insert_component(self, source, name, position, rotation, grounded):
        return self._op("insert_component", source=source, name=name,
                        position=position, rotation=rotation, grounded=grounded)

    def get_last_error(self):
        return self._last_error or {"ok": True, "message": "no error recorded"}
