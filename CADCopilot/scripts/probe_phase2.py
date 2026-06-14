"""Phase-2 probe v2: each op on its own fresh body; screenshot before risky ops;
learn exact signatures for face inspection, hole, chamfer, patterns, shell."""

import os, traceback
import pythoncom
import win32com.client as win32

GUID = "{D98A091D-3A0F-4C3E-B36E-61F62068D488}"
def cm(mm): return mm / 10.0
OUT = r"C:\Users\advay\Documents\CacheCAD\.cad_mcp"; os.makedirs(OUT, exist_ok=True)


def main():
    pythoncom.CoInitialize()
    win32.gencache.EnsureModule(GUID, 0, 1, 0)
    C = win32.constants
    try:
        app = win32.gencache.EnsureDispatch(pythoncom.GetActiveObject("Inventor.Application"))
    except Exception:
        app = win32.gencache.EnsureDispatch("Inventor.Application"); app.Visible = True
    tg, tobj = app.TransientGeometry, app.TransientObjects
    print("version", app.SoftwareVersion.DisplayName)
    tmpl = app.FileManager.GetTemplateFile(C.kPartDocumentObject)
    doc = win32.CastTo(app.Documents.Add(C.kPartDocumentObject, tmpl, True), "PartDocument")
    cd = doc.ComponentDefinition
    ex = cd.Features.ExtrudeFeatures

    def plate(x0, y0, w, h, t):
        sk = cd.Sketches.Add(cd.WorkPlanes.Item(3))
        sk.SketchLines.AddAsTwoPointRectangle(tg.CreatePoint2d(cm(x0), cm(y0)), tg.CreatePoint2d(cm(x0+w), cm(y0+h)))
        p = sk.Profiles.AddForSolid()
        d = ex.CreateExtrudeDefinition(p, C.kNewBodyOperation)
        d.SetDistanceExtent(cm(t), C.kPositiveExtentDirection)
        f = ex.Add(d); doc.Update()
        return f.SurfaceBodies.Item(1)

    def top_face(body):
        best, bz = None, -1e9
        for i in range(1, body.Faces.Count + 1):
            f = body.Faces.Item(i)
            if f.SurfaceType == C.kPlaneSurface:
                z = f.Geometry.RootPoint.Z
                if z > bz and round(f.Geometry.Normal.Z, 3) == 1.0:
                    bz, best = z, f
        return best

    def sec(t, fn):
        print(f"\n=== {t} ===", flush=True)
        try: fn()
        except Exception: print("FAIL:", traceback.format_exc().splitlines()[-1])

    # ---- face inspection (PointOnFace + Geometry) ----
    def faces():
        b = plate(0, 0, 40, 40, 5)
        st_map = {C.kPlaneSurface:"planar", C.kCylinderSurface:"cylindrical", C.kConeSurface:"conical",
                  C.kSphereSurface:"spherical", C.kTorusSurface:"toroidal"}
        f = b.Faces.Item(1)
        print("has PointOnFace:", hasattr(f, "PointOnFace"))
        pof = f.PointOnFace
        print("PointOnFace mm:", round(pof.X*10,2), round(pof.Y*10,2), round(pof.Z*10,2))
        tf = top_face(b)
        print("top face normal:", round(tf.Geometry.Normal.Z,3), "root z mm:", round(tf.Geometry.RootPoint.Z*10,2))
        # area attempt
        try:
            print("Evaluator.Area:", round(f.Evaluator.Area*100, 3), "mm^2")  # cm^2 -> mm^2
        except Exception as e:
            print("no Evaluator.Area:", str(e)[:70])
        return b
    sec("face inspection", faces)

    # ---- screenshot (before risky ops) ----
    def shot():
        path = os.path.join(OUT, "probe_shot.png")
        try:
            app.ActiveView.SaveAsBitmap(path, 800, 600)
            print("ActiveView.SaveAsBitmap ok:", os.path.getsize(path))
        except Exception as e:
            print("ActiveView.SaveAsBitmap fail:", str(e)[:70])
            cam = app.ActiveView.Camera
            cam.SaveAsBitmap(path, 800, 600, win32.VARIANT(pythoncom.VT_DISPATCH, None) if False else None)
            print("Camera.SaveAsBitmap ok:", os.path.getsize(path))
    sec("screenshot", shot)

    # ---- chamfer on fresh body ----
    def chamfer():
        b = plate(60, 0, 30, 30, 8)
        coll = tobj.CreateEdgeCollection(); coll.Add(b.Edges.Item(1))
        ch = cd.Features.ChamferFeatures.AddUsingDistance(coll, cm(2)); doc.Update()
        print("chamfer ok:", ch.Name)
    sec("chamfer", chamfer)

    # ---- hole on fresh plate top face ----
    def hole():
        b = plate(120, 0, 40, 40, 6)
        tf = top_face(b)
        hs = cd.Sketches.Add(tf)
        # place a sketch point at face center via transform-aware coords:
        # the sketch coordinate origin maps to the face; use a point near middle.
        sp = hs.SketchPoints.Add(tg.CreatePoint2d(cm(20), cm(20)))
        coll = tobj.CreateObjectCollection(); coll.Add(sp)
        hf = cd.Features.HoleFeatures
        print("HoleFeatures methods present:", [m for m in ("CreateSketchPlacementDefinition","AddDrilledByThroughAllExtent","AddDrilledByDistanceExtent") if hasattr(hf,m)])
        placement = hf.CreateSketchPlacementDefinition(coll)
        h = hf.AddDrilledByThroughAllExtent(placement, cm(5), C.kNegativeExtentDirection)
        doc.Update()
        print("hole ok:", h.Name, "-> body faces now", b.Faces.Count)
        return b, h
    sec("hole", hole)

    # ---- rectangular pattern of a hole ----
    def rectpat():
        b = plate(180, 0, 40, 24, 6)
        tf = top_face(b)
        hs = cd.Sketches.Add(tf)
        sp = hs.SketchPoints.Add(tg.CreatePoint2d(cm(4), cm(4)))
        coll = tobj.CreateObjectCollection(); coll.Add(sp)
        hf = cd.Features.HoleFeatures
        h = hf.AddDrilledByThroughAllExtent(hf.CreateSketchPlacementDefinition(coll), cm(4), C.kNegativeExtentDirection)
        doc.Update()
        feats = tobj.CreateObjectCollection(); feats.Add(h)
        xaxis = cd.WorkAxes.Item(1); yaxis = cd.WorkAxes.Item(2)
        rp = cd.Features.RectangularPatternFeatures.Add(
            feats, xaxis, True, "4", "8 mm", yaxis, True, "3", "8 mm")
        doc.Update()
        print("rect pattern ok:", rp.Name)
    sec("rectangular pattern", rectpat)

    # ---- circular pattern of a hole around Z ----
    def circpat():
        b = plate(240, 0, 50, 50, 6)
        tf = top_face(b)
        hs = cd.Sketches.Add(tf)
        sp = hs.SketchPoints.Add(tg.CreatePoint2d(cm(10), cm(25)))  # offset from center
        coll = tobj.CreateObjectCollection(); coll.Add(sp)
        hf = cd.Features.HoleFeatures
        h = hf.AddDrilledByThroughAllExtent(hf.CreateSketchPlacementDefinition(coll), cm(4), C.kNegativeExtentDirection)
        doc.Update()
        feats = tobj.CreateObjectCollection(); feats.Add(h)
        zaxis = cd.WorkAxes.Item(3)
        cp = cd.Features.CircularPatternFeatures.Add(feats, zaxis, True, "6", "360 deg")
        doc.Update()
        print("circular pattern ok:", cp.Name)
    sec("circular pattern", circpat)

    # ---- shell a cylinder ----
    def shell():
        sk = cd.Sketches.Add(cd.WorkPlanes.Item(3))
        sk.SketchCircles.AddByCenterRadius(tg.CreatePoint2d(cm(320), cm(0)), cm(15))
        p = sk.Profiles.AddForSolid()
        d = ex.CreateExtrudeDefinition(p, C.kNewBodyOperation)
        d.SetDistanceExtent(cm(20), C.kPositiveExtentDirection)
        cyl = ex.Add(d); doc.Update()
        cb = cyl.SurfaceBodies.Item(1)
        tf = top_face(cb)
        fcoll = tobj.CreateFaceCollection(); fcoll.Add(tf)
        sf = cd.Features.ShellFeatures
        print("ShellFeatures has CreateShellDefinition:", hasattr(sf, "CreateShellDefinition"))
        sdef = sf.CreateShellDefinition(fcoll, cm(2), C.kInsideShellDirection)
        sh = sf.Add(sdef); doc.Update()
        print("shell ok:", sh.Name)
    sec("shell", shell)

    print("\nPROBE2_DONE")


if __name__ == "__main__":
    main()
