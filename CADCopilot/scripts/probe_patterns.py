"""Pin down the exact RectangularPattern / CircularPattern signatures + enums."""
import traceback
import pythoncom
import win32com.client as win32

GUID = "{D98A091D-3A0F-4C3E-B36E-61F62068D488}"
def cm(mm): return mm/10.0


def main():
    pythoncom.CoInitialize()
    win32.gencache.EnsureModule(GUID, 0, 1, 0)
    C = win32.constants
    try:
        app = win32.GetActiveObject("Inventor.Application")
    except Exception:
        app = win32.gencache.EnsureDispatch("Inventor.Application"); app.Visible = True
    tg, tobj = app.TransientGeometry, app.TransientObjects

    print("Spacing/Compute constants:")
    for n in dir(C):
        if "Spacing" in n or "Compute" in n or ("Pattern" in n and "Type" in n):
            print("  ", n, "=", getattr(C, n))

    tmpl = app.FileManager.GetTemplateFile(C.kPartDocumentObject)
    doc = win32.CastTo(app.Documents.Add(C.kPartDocumentObject, tmpl, True), "PartDocument")
    cd = doc.ComponentDefinition
    ex = cd.Features.ExtrudeFeatures

    def plate_with_hole(x0, w, h):
        sk = cd.Sketches.Add(cd.WorkPlanes.Item(3))
        sk.SketchLines.AddAsTwoPointRectangle(tg.CreatePoint2d(cm(x0), 0), tg.CreatePoint2d(cm(x0+w), cm(h)))
        d = ex.CreateExtrudeDefinition(sk.Profiles.AddForSolid(), C.kNewBodyOperation)
        d.SetDistanceExtent(cm(6), C.kPositiveExtentDirection)
        body = ex.Add(d).SurfaceBodies.Item(1); doc.Update()
        tf = None
        for i in range(1, body.Faces.Count+1):
            f = body.Faces.Item(i)
            if f.SurfaceType == C.kPlaneSurface and round(f.Geometry.Normal.Z,3) == 1.0:
                tf = f
        hs = cd.Sketches.Add(tf)
        sp = hs.SketchPoints.Add(tg.CreatePoint2d(cm(4), cm(4)))
        oc = tobj.CreateObjectCollection(); oc.Add(sp)
        hf = cd.Features.HoleFeatures
        hole = hf.AddDrilledByThroughAllExtent(hf.CreateSketchPlacementDefinition(oc), cm(4), C.kNegativeExtentDirection)
        doc.Update()
        return hole

    # rectangular: try with explicit XSpacingType + YSpacingType
    print("\n--- rectangular ---")
    try:
        h = plate_with_hole(0, 40, 24)
        feats = tobj.CreateObjectCollection(); feats.Add(h)
        st = getattr(C, "kDefaultPatternSpacing", None)
        print("kDefaultPatternSpacing =", st)
        rp = cd.Features.RectangularPatternFeatures.Add(
            feats, cd.WorkAxes.Item(1), True, "4", "8 mm", st,
            cd.WorkAxes.Item(2), True, "3", "8 mm", st)
        doc.Update(); print("rect OK:", rp.Name)
    except Exception:
        print("rect FAIL:", traceback.format_exc().splitlines()[-1])

    # circular: try with Fit arg variants
    print("\n--- circular ---")
    for fit in (True, False):
        try:
            h = plate_with_hole(80 + (0 if fit else 60), 50, 50)
            feats = tobj.CreateObjectCollection(); feats.Add(h)
            cp = cd.Features.CircularPatternFeatures.Add(
                feats, cd.WorkAxes.Item(3), True, "6", "360 deg", fit)
            doc.Update(); print(f"circular OK (fit={fit}):", cp.Name); break
        except Exception:
            print(f"circular FAIL (fit={fit}):", traceback.format_exc().splitlines()[-1])

    print("\nDONE")


if __name__ == "__main__":
    main()
