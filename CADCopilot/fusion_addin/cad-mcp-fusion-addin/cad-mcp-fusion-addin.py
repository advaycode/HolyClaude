"""CADCopilot Fusion 360 add-in.

Bridges the external CADCopilot MCP server (FusionBackend) to Fusion's API. A
background socket-listener thread accepts one JSON command per connection but NEVER
calls adsk directly — it fires a CustomEvent carrying the command, and the
CustomEventHandler.notify() (which runs on Fusion's MAIN thread) does the actual
adsk work and signals a threading.Event the listener is blocked on. Calling adsk
off the main thread crashes Fusion, so this marshaling is non-negotiable.

Protocol: client sends {"command","args"}\n ; we reply {"ok",result|error}\n .
Distances arrive in CENTIMETRES, angles in RADIANS (Fusion's internal units).
"""

import adsk.core
import adsk.fusion
import base64
import json
import math
import os
import socket
import threading
import traceback

HOST, PORT = "127.0.0.1", 9876
EVENT_ID = "cadMcpCommand"

_app = None
_ui = None
_handlers = []          # keep handler refs alive
_custom_event = None
_server_thread = None
_stop = threading.Event()

# main-thread <-> socket-thread handoff
_lock = threading.Lock()
_pending = {}           # request id -> {"event":Event, "payload":dict, "result":dict}
_counter = 0

# named entity registry (name -> adsk object), mirrors the Inventor backend
_reg = {}
_counters = {}


# --------------------------------------------------------------------------- #
# registry helpers (main thread)
# --------------------------------------------------------------------------- #
def _name(kind, hint=""):
    _counters[kind] = _counters.get(kind, 0) + 1
    base = kind.capitalize()
    return f"{base}_{hint}_{_counters[kind]:03d}" if hint else f"{base}_{_counters[kind]:03d}"


def _register(kind, obj, name="", hint=""):
    if not name:
        name = _name(kind, hint)
    elif name in _reg:
        i = 2
        while f"{name}_{i}" in _reg:
            i += 1
        name = f"{name}_{i}"
    _reg[name] = obj
    return name


def _design():
    d = adsk.fusion.Design.cast(_app.activeProduct)
    if not d:
        raise RuntimeError("No active Fusion design. Switch to the Design workspace.")
    return d


def _plane(name):
    root = _design().rootComponent
    key = (name or "xy").lower()
    planes = {"xy": root.xYConstructionPlane, "xz": root.xZConstructionPlane,
              "yz": root.yZConstructionPlane}
    if key in planes:
        return planes[key]
    if name in _reg:
        return _reg[name]
    raise RuntimeError(f"Unknown plane {name!r}")


def _op_enum(operation):
    fo = adsk.fusion.FeatureOperations
    return {"join": fo.JoinFeatureOperation, "cut": fo.CutFeatureOperation,
            "intersect": fo.IntersectFeatureOperation,
            "new_body": fo.NewBodyFeatureOperation}.get((operation or "new_body").lower(),
                                                        fo.NewBodyFeatureOperation)


def _pt(x, y, z=0.0):
    return adsk.core.Point3D.create(x, y, z)


def _vi(real):
    return adsk.core.ValueInput.createByReal(real)


# --------------------------------------------------------------------------- #
# command dispatch (ALL runs on the MAIN thread)
# --------------------------------------------------------------------------- #
def dispatch(command, a):
    root = None
    try:
        root = _design().rootComponent
    except Exception:
        if command not in ("connect", "new_document", "eval_native"):
            raise

    if command == "connect":
        return {"connected": True, "app": "Autodesk Fusion 360",
                "version": _app.version, "active_document": (_app.activeDocument.name if _app.activeDocument else None)}

    if command == "new_document":
        docs = _app.documents
        docs.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        _reg.clear(); _counters.clear()
        return {"name": a.get("name", ""), "kind": "part", "message": "New Fusion design"}

    if command == "save_document":
        path = a["path"]
        _app.activeDocument.saveAs(os.path.splitext(os.path.basename(path))[0],
                                   _app.data.activeProject.rootFolder, "", "")
        return {"name": os.path.basename(path), "message": "Saved (Fusion cloud project)"}

    if command == "create_sketch":
        sk = root.sketches.add(_plane(a["plane"]))
        nm = _register("sketch", sk, a.get("name", ""))
        sk.name = nm
        return {"name": nm, "kind": "sketch"}

    if command == "add_rectangle":
        sk = _reg[a["sketch"]]
        sk.sketchCurves.sketchLines.addTwoPointRectangle(_pt(a["x1"], a["y1"]), _pt(a["x2"], a["y2"]))
        return {"name": a["sketch"], "kind": "sketch_geometry", "message": "rectangle"}

    if command == "add_circle":
        sk = _reg[a["sketch"]]
        sk.sketchCurves.sketchCircles.addByCenterRadius(_pt(a["cx"], a["cy"]), a["radius"])
        return {"name": a["sketch"], "kind": "sketch_geometry", "message": "circle"}

    if command == "add_line":
        sk = _reg[a["sketch"]]
        pts = a["points"]
        seq = pts + ([pts[0]] if a.get("closed") and len(pts) > 2 else [])
        lines = sk.sketchCurves.sketchLines
        for p, q in zip(seq[:-1], seq[1:]):
            lines.addByTwoPoints(_pt(p[0], p[1]), _pt(q[0], q[1]))
        return {"name": a["sketch"], "kind": "sketch_geometry", "message": "polyline"}

    if command == "add_point":
        sk = _reg[a["sketch"]]
        sk.sketchPoints.add(_pt(a["x"], a["y"]))
        return {"name": a["sketch"], "kind": "sketch_geometry", "message": "point"}

    if command == "create_extrude":
        sk = _reg[a["profile"]]
        prof = sk.profiles.item(0)
        feats = root.features.extrudeFeatures
        inp = feats.createInput(prof, _op_enum(a["operation"]))
        dist = a["distance"]
        direction = (a.get("direction") or "pos").lower()
        if direction == "symmetric":
            inp.setSymmetricExtent(_vi(dist), True)
        else:
            inp.setDistanceExtent(False, _vi(-dist if direction in ("neg", "negative") else dist))
        ext = feats.add(inp)
        nm = _register("feature", ext, a.get("name", ""), "Extrude")
        return {"name": nm, "kind": "extrude", "data": {"bodies": _body_names()}}

    if command == "create_revolve":
        sk = _reg[a["profile"]]
        prof = sk.profiles.item(0)
        axis = _axis(a["axis"], sk)
        feats = root.features.revolveFeatures
        inp = feats.createInput(prof, axis, _op_enum(a["operation"]))
        inp.setAngleExtent(False, _vi(a["angle"]))
        rev = feats.add(inp)
        nm = _register("feature", rev, a.get("name", ""), "Revolve")
        return {"name": nm, "kind": "revolve", "data": {"bodies": _body_names()}}

    if command == "create_fillet":
        edges = adsk.core.ObjectCollection.create()
        for en in a["edges"]:
            edges.add(_reg[en])
        feats = root.features.filletFeatures
        inp = feats.createInput()
        inp.addConstantRadiusEdgeSet(edges, _vi(a["radius"]), True)
        f = feats.add(inp)
        nm = _register("feature", f, a.get("name", ""), "Fillet")
        return {"name": nm, "kind": "fillet"}

    if command == "create_hole":
        # simple round cut: build a circle on the sketch points and cut through-all
        sk = _reg[a["sketch"]]
        cut_sk = root.sketches.add(sk.referencePlane)
        for sp in sk.sketchPoints:
            if sp.geometry.distanceTo(_pt(0, 0, 0)) >= 0:  # include all
                cut_sk.sketchCurves.sketchCircles.addByCenterRadius(sp.geometry, a["diameter"] / 2.0)
        feats = root.features.extrudeFeatures
        inp = feats.createInput(cut_sk.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
        ext = adsk.fusion.ThroughAllExtentDefinition.create() if a.get("through_all", True) else None
        if ext:
            inp.setOneSideExtent(ext, adsk.fusion.ExtentDirections.NegativeExtentDirection)
        else:
            inp.setDistanceExtent(False, _vi(-a.get("depth", a["diameter"])))
        f = feats.add(inp)
        nm = _register("feature", f, a.get("name", ""), "Hole")
        return {"name": nm, "kind": "hole"}

    if command == "boolean_combine":
        target = _reg[a["target"]]
        tools = adsk.core.ObjectCollection.create()
        for tn in a["tools"]:
            tools.add(_reg[tn])
        feats = root.features.combineFeatures
        inp = feats.createInput(target, tools)
        co = {"union": 0, "subtract": 1, "intersect": 2}.get((a.get("operation") or "union").lower(), 0)
        inp.operation = [adsk.fusion.FeatureOperations.JoinFeatureOperation,
                         adsk.fusion.FeatureOperations.CutFeatureOperation,
                         adsk.fusion.FeatureOperations.IntersectFeatureOperation][co]
        feats.add(inp)
        return {"name": a.get("name", ""), "kind": "combine", "data": {"bodies": _body_names()}}

    if command == "set_parameter":
        d = _design()
        ups = d.userParameters
        existing = ups.itemByName(a["name"])
        if existing and a.get("mode") != "create":
            existing.expression = a["expression"]
            p = existing
        else:
            p = ups.add(a["name"], adsk.core.ValueInput.createByString(a["expression"]),
                        d.unitsManager.defaultLengthUnits, a.get("comment", ""))
        return {"name": p.name, "kind": "parameter", "data": {"value_mm": p.value * 10}}

    if command == "get_parameters":
        d = _design()
        items = []
        for p in d.allParameters:
            try:
                items.append({"name": p.name, "expression": p.expression, "value_mm": p.value * 10,
                              "unit": p.unit, "comment": p.comment or "",
                              "is_user": p.objectType == adsk.fusion.UserParameter.classType()})
            except Exception:
                pass
        return {"items": items}

    if command == "list_bodies":
        return {"items": _bodies_info()}

    if command == "bounding_box":
        return _bbox(a.get("body"))

    if command == "list_features":
        items = []
        tl = _design().timeline
        for i in range(tl.count):
            try:
                e = tl.item(i).entity
                items.append({"name": getattr(e, "name", f"feature_{i}"),
                              "feature_type": e.objectType.split("::")[-1], "suppressed": False, "health": "ok"})
            except Exception:
                pass
        return {"items": items}

    if command == "screenshot_png":
        path = os.path.join(os.environ.get("TEMP", "."), "cad_mcp_fusion_view.png")
        _app.activeViewport.saveAsImageFile(path, int(a.get("width", 1024)), int(a.get("height", 768)))
        with open(path, "rb") as fh:
            return {"png_b64": base64.b64encode(fh.read()).decode("ascii")}

    if command == "export":
        return _export(a)

    if command == "eval_native":
        g = {"adsk": adsk, "app": _app, "ui": _ui, "design": _design(),
             "root": _design().rootComponent, "math": math, "cm": lambda mm: mm / 10.0,
             "reg": _reg, "result": None}
        exec(a["code"], g)
        out = g.get("result")
        return {"result": out if isinstance(out, (str, int, float, bool, list, dict, type(None))) else str(out)}

    raise RuntimeError(f"Command {command!r} is not implemented in the Fusion backend yet")


# --------------------------------------------------------------------------- #
# inspection helpers (main thread)
# --------------------------------------------------------------------------- #
def _axis(axis, sk):
    root = _design().rootComponent
    a = (axis or "z").lower()
    base = {"x": root.xConstructionAxis, "y": root.yConstructionAxis, "z": root.zConstructionAxis}
    if a in base:
        return base[a]
    return _reg.get(axis, root.zConstructionAxis)


def _body_names():
    return [n for n, o in _reg.items() if o.objectType == adsk.fusion.BRepBody.classType()] or \
           [b.name for b in _design().rootComponent.bRepBodies]


def _bodies_info():
    out = []
    for b in _design().rootComponent.bRepBodies:
        bb = b.boundingBox
        out.append({"name": b.name, "face_count": b.faces.count, "edge_count": b.edges.count,
                    "volume_mm3": round(b.volume * 1000, 4), "area_mm2": round(b.area * 100, 4),
                    "bbox_mm": [bb.minPoint.x * 10, bb.minPoint.y * 10, bb.minPoint.z * 10,
                               bb.maxPoint.x * 10, bb.maxPoint.y * 10, bb.maxPoint.z * 10]})
    return out


def _bbox(body):
    root = _design().rootComponent
    bodies = [b for b in root.bRepBodies if (not body or b.name == body)]
    if not bodies:
        raise RuntimeError("No bodies to measure")
    xs, ys, zs = [], [], []
    for b in bodies:
        bb = b.boundingBox
        xs += [bb.minPoint.x * 10, bb.maxPoint.x * 10]
        ys += [bb.minPoint.y * 10, bb.maxPoint.y * 10]
        zs += [bb.minPoint.z * 10, bb.maxPoint.z * 10]
    lo, hi = [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]
    dims = [hi[i] - lo[i] for i in range(3)]
    return {"what": "bounding_box", "value": round(max(dims), 4), "unit": "mm",
            "extra": {"min_mm": lo, "max_mm": hi, "dimensions_mm": dims}}


def _export(a):
    fmt = (a.get("fmt") or "stl").lower()
    path = a["output_path"]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    em = _design().exportManager
    root = _design().rootComponent
    if fmt == "stl":
        opts = em.createSTLExportOptions(root, path)
        opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    elif fmt in ("step", "stp"):
        opts = em.createSTEPExportOptions(path, root)
    elif fmt in ("iges", "igs"):
        opts = em.createIGESExportOptions(path, root)
    else:
        raise RuntimeError(f"Unsupported export format {fmt!r}")
    em.execute(opts)
    size = os.path.getsize(path) if os.path.exists(path) else 0
    return {"name": os.path.basename(path), "kind": "export",
            "message": f"Exported {fmt.upper()} ({size} bytes)",
            "data": {"path": path, "bytes": size, "format": fmt}}


# --------------------------------------------------------------------------- #
# CustomEvent handler — runs on the MAIN thread
# --------------------------------------------------------------------------- #
class _CommandHandler(adsk.core.CustomEventHandler):
    def notify(self, args):
        rid = args.additionalInfo
        with _lock:
            slot = _pending.get(rid)
        if not slot:
            return
        try:
            result = dispatch(slot["payload"]["command"], slot["payload"].get("args", {}))
            slot["result"] = {"ok": True, "result": result}
        except Exception as e:  # noqa: BLE001
            slot["result"] = {"ok": False, "error": str(e),
                              "recovery": traceback.format_exc().splitlines()[-1]}
        finally:
            slot["event"].set()


# --------------------------------------------------------------------------- #
# socket listener — runs on a BACKGROUND thread (no adsk calls here!)
# --------------------------------------------------------------------------- #
def _serve():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(5)
    srv.settimeout(1.0)
    global _counter
    while not _stop.is_set():
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        try:
            buf = b""
            conn.settimeout(40)
            while not buf.endswith(b"\n"):
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf += chunk
            payload = json.loads(buf.decode("utf-8"))
            with _lock:
                _counter += 1
                rid = str(_counter)
                slot = {"event": threading.Event(), "payload": payload, "result": None}
                _pending[rid] = slot
            _app.fireCustomEvent(EVENT_ID, rid)         # hop to main thread
            if not slot["event"].wait(38):
                resp = {"ok": False, "error": "Fusion main-thread timeout"}
            else:
                resp = slot["result"]
            with _lock:
                _pending.pop(rid, None)
            conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
        except Exception as e:  # noqa: BLE001
            try:
                conn.sendall((json.dumps({"ok": False, "error": str(e)}) + "\n").encode("utf-8"))
            except Exception:
                pass
        finally:
            conn.close()
    srv.close()


# --------------------------------------------------------------------------- #
# add-in lifecycle
# --------------------------------------------------------------------------- #
def run(context):
    global _app, _ui, _custom_event, _server_thread
    _app = adsk.core.Application.get()
    _ui = _app.userInterface
    try:
        _app.unregisterCustomEvent(EVENT_ID)
    except Exception:
        pass
    _custom_event = _app.registerCustomEvent(EVENT_ID)
    handler = _CommandHandler()
    _custom_event.add(handler)
    _handlers.append(handler)
    _stop.clear()
    _server_thread = threading.Thread(target=_serve, name="cad-mcp-fusion", daemon=True)
    _server_thread.start()
    _ui.messageBox(f"CADCopilot add-in listening on {HOST}:{PORT}")


def stop(context):
    _stop.set()
    try:
        _app.unregisterCustomEvent(EVENT_ID)
    except Exception:
        pass
    _handlers.clear()
