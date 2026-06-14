"""Nail working rectangular-pattern and revolve formulations empirically."""
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

    # plate + centered hole
    sk = cd.Sketches.Add(cd.WorkPlanes.Item(3))
    sk.SketchLines.AddAsTwoPointRectangle(tg.CreatePoint2d(0, 0), tg.CreatePoint2d(cm(80), cm(40)))
    d = ex.CreateExtrudeDefinition(sk.Profiles.AddForSolid(), C.kNewBodyOperation)
    d.SetDistanceExtent(cm(5), C.kPositiveExtentDirection)
    ex.Add(d); doc.Update()
    hs = cd.Sketches.Add(cd.WorkPlanes.Item(3))
    hs.SketchPoints.Add(tg.CreatePoint2d(cm(40), cm(20)))
    oc = tobj.CreateObjectCollection(); oc.Add(hs.SketchPoints.Item(hs.SketchPoints.Count))
    hf = cd.Features.HoleFeatures
    hole = hf.AddDrilledByThroughAllExtent(hf.CreateSketchPlacementDefinition(oc), cm(4), C.kPositiveExtentDirection)
    doc.Update()
    print("PatternComputeTypeEnum:", [n for n in dir(C) if "Compute" in n], "->",
          {n: getattr(C, n) for n in dir(C) if "Compute" in n})

    rpf = cd.Features.RectangularPatternFeatures
    xax, yax = cd.WorkAxes.Item(1), cd.WorkAxes.Item(2)

    def feats():
        c = tobj.CreateObjectCollection(); c.Add(hole); return c

    def t(label, fn):
        try:
            r = fn(); doc.Update(); print("OK   ", label, "->", r.Name)
            try: r.Delete()  # clean for next attempt
            except Exception: pass
            return True
        except Exception:
            print("FAIL ", label, ":", traceback.format_exc().splitlines()[-1]); return False

    t("1D positional minimal", lambda: rpf.Add(feats(), xax, True, "3", "8 mm"))
    t("1D kw + XSpacingType kDefault", lambda: rpf.Add(ParentFeatures=feats(), XDirectionEntity=xax,
        NaturalXDirection=True, XCount="3", XSpacing="8 mm", XSpacingType=C.kDefault))
    t("2D positional w/ all args", lambda: rpf.Add(feats(), xax, True, "3", "8 mm", C.kDefault,
        win32.VARIANT(pythoncom.VT_EMPTY, None), yax, True, "2", "8 mm"))
    t("1D via CreateDefinition+AddByDefinition", lambda: rpf.AddByDefinition(
        rpf.CreateDefinition(feats(), xax, True, "3", "8 mm")))

    # revolve formulations
    print("\n--- revolve ---")
    rv = cd.Features.RevolveFeatures
    # profile + dedicated axis line on the same sketch (XY plane), revolve around that line
    rs = cd.Sketches.Add(cd.WorkPlanes.Item(3))
    rs.SketchLines.AddAsTwoPointRectangle(tg.CreatePoint2d(cm(110), cm(0)), tg.CreatePoint2d(cm(120), cm(30)))
    axisline = rs.SketchLines.AddByTwoPoints(tg.CreatePoint2d(cm(100), cm(0)), tg.CreatePoint2d(cm(100), cm(30)))
    try: axisline.Construction = True
    except Exception: pass
    rprof = rs.Profiles.AddForSolid()
    def tr(label, fn):
        try: r = fn(); doc.Update(); print("OK   ", label, "->", r.Name)
        except Exception: print("FAIL ", label, ":", traceback.format_exc().splitlines()[-1])
    tr("AddFull around sketch line", lambda: rv.AddFull(rprof, axisline, C.kNewBodyOperation))

    print("\nDONE")


if __name__ == "__main__":
    main()
