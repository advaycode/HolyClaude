"""Find a robust hole-placement approach: origin-plane vs face-sketch, and test
PlanarSketch.ModelToSketchSpace for world-coordinate placement on a face."""
import traceback
import pythoncom
import win32com.client as win32
GUID = "{D98A091D-3A0F-4C3E-B36E-61F62068D488}"
def cm(mm): return mm/10.0


def main():
    pythoncom.CoInitialize()
    win32.gencache.EnsureModule(GUID, 0, 1, 0)
    C = win32.constants
    try: app = win32.GetActiveObject("Inventor.Application")
    except Exception: app = win32.gencache.EnsureDispatch("Inventor.Application"); app.Visible = True
    tg, tobj = app.TransientGeometry, app.TransientObjects
    tmpl = app.FileManager.GetTemplateFile(C.kPartDocumentObject)
    doc = win32.CastTo(app.Documents.Add(C.kPartDocumentObject, tmpl, True), "PartDocument")
    cd = doc.ComponentDefinition
    ex = cd.Features.ExtrudeFeatures

    # plate on XY z0..5
    sk = cd.Sketches.Add(cd.WorkPlanes.Item(3))
    sk.SketchLines.AddAsTwoPointRectangle(tg.CreatePoint2d(0, 0), tg.CreatePoint2d(cm(80), cm(40)))
    d = ex.CreateExtrudeDefinition(sk.Profiles.AddForSolid(), C.kNewBodyOperation)
    d.SetDistanceExtent(cm(5), C.kPositiveExtentDirection)
    body = ex.Add(d).SurfaceBodies.Item(1); doc.Update()

    def sec(t, fn):
        print(f"\n=== {t} ===", flush=True)
        try: fn()
        except Exception: print("FAIL:", traceback.format_exc().splitlines()[-1])

    # A) hole on XY origin plane, flip True
    def origin_flipT():
        hs = cd.Sketches.Add(cd.WorkPlanes.Item(3))
        sp = hs.SketchPoints.Add(tg.CreatePoint2d(cm(8), cm(8)))
        oc = tobj.CreateObjectCollection(); oc.Add(sp)
        hf = cd.Features.HoleFeatures
        h = hf.AddDrilledByThroughAllExtent(hf.CreateSketchPlacementDefinition(oc), cm(4), C.kPositiveExtentDirection)
        doc.Update(); print("origin flip+ OK", h.Name)
    sec("hole origin plane +Z", origin_flipT)

    # B) hole on XY origin plane, flip False
    def origin_flipF():
        hs = cd.Sketches.Add(cd.WorkPlanes.Item(3))
        sp = hs.SketchPoints.Add(tg.CreatePoint2d(cm(16), cm(8)))
        oc = tobj.CreateObjectCollection(); oc.Add(sp)
        hf = cd.Features.HoleFeatures
        h = hf.AddDrilledByThroughAllExtent(hf.CreateSketchPlacementDefinition(oc), cm(4), C.kNegativeExtentDirection)
        doc.Update(); print("origin flip- OK", h.Name)
    sec("hole origin plane -Z", origin_flipF)

    # C) top face sketch + ModelToSketchSpace world->sketch coords
    def face_world():
        top = None
        for i in range(1, body.Faces.Count+1):
            f = body.Faces.Item(i)
            if f.SurfaceType == C.kPlaneSurface and f.PointOnFace.Z > cm(4):
                top = f
        hs = cd.Sketches.Add(top)
        print("has ModelToSketchSpace:", hasattr(hs, "ModelToSketchSpace"))
        world = tg.CreatePoint(cm(40), cm(20), cm(5))   # world center of top face
        sp2d = hs.ModelToSketchSpace(world)
        print("world(40,20,5)mm -> sketch", round(sp2d.X*10,2), round(sp2d.Y*10,2))
        sp = hs.SketchPoints.Add(sp2d)
        oc = tobj.CreateObjectCollection(); oc.Add(sp)
        hf = cd.Features.HoleFeatures
        h = hf.AddDrilledByThroughAllExtent(hf.CreateSketchPlacementDefinition(oc), cm(4), C.kNegativeExtentDirection)
        doc.Update(); print("face world-coord hole OK", h.Name)
    sec("face sketch + ModelToSketchSpace", face_world)

    print("\nDONE")


if __name__ == "__main__":
    main()
