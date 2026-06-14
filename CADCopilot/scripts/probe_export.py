"""Enumerate Inventor translators (STL/STEP) and validate an export + iLogic addin."""
import os, traceback
import pythoncom
import win32com.client as win32
GUID = "{D98A091D-3A0F-4C3E-B36E-61F62068D488}"
def cm(mm): return mm/10.0
OUT = r"C:\Users\advay\Documents\CacheCAD\.cad_mcp"; os.makedirs(OUT, exist_ok=True)


def main():
    pythoncom.CoInitialize()
    win32.gencache.EnsureModule(GUID, 0, 1, 0)
    C = win32.constants
    try: app = win32.GetActiveObject("Inventor.Application")
    except Exception: app = win32.gencache.EnsureDispatch("Inventor.Application"); app.Visible = True
    tg = app.TransientGeometry

    print("=== translator add-ins ===")
    for i in range(1, app.ApplicationAddIns.Count + 1):
        a = app.ApplicationAddIns.Item(i)
        try:
            if a.AddInType == C.kTranslationApplicationAddIn:
                name = a.DisplayName
                if any(k in name for k in ("STL", "STEP", "IGES", "OBJ", "3D PDF", "Wavefront")):
                    print(f"  {name}  ->  {a.ClassIdString}")
        except Exception:
            pass

    print("\n=== iLogic addin ===")
    try:
        il = app.ApplicationAddIns.ItemById("{3BDD8D79-2179-4B11-8A5A-257B1C0263AC}")
        print("  iLogic addin found:", il.DisplayName, "Activated:", il.Activated)
        print("  has Automation:", hasattr(il, "Automation"))
    except Exception:
        print("  iLogic addin lookup failed:", traceback.format_exc().splitlines()[-1])

    # build a small part and export STL + STEP
    tmpl = app.FileManager.GetTemplateFile(C.kPartDocumentObject)
    doc = win32.CastTo(app.Documents.Add(C.kPartDocumentObject, tmpl, True), "PartDocument")
    cd = doc.ComponentDefinition
    sk = cd.Sketches.Add(cd.WorkPlanes.Item(3))
    sk.SketchCircles.AddByCenterRadius(tg.CreatePoint2d(0, 0), cm(10))
    d = cd.Features.ExtrudeFeatures.CreateExtrudeDefinition(sk.Profiles.AddForSolid(), C.kNewBodyOperation)
    d.SetDistanceExtent(cm(10), C.kPositiveExtentDirection)
    cd.Features.ExtrudeFeatures.Add(d); doc.Update()

    def export(label, clsid, path, set_opts=None):
        try:
            tr = win32.CastTo(app.ApplicationAddIns.ItemById(clsid), "TranslatorAddIn")
            ctx = app.TransientObjects.CreateTranslationContext()
            ctx.Type = C.kFileBrowseIOMechanism
            opts = app.TransientObjects.CreateNameValueMap()
            medium = app.TransientObjects.CreateDataMedium()
            medium.FileName = path
            if tr.HasSaveCopyAsOptions(doc, ctx, opts) and set_opts:
                set_opts(opts)
            tr.SaveCopyAs(doc, ctx, opts, medium)
            print(f"  {label} OK: {os.path.getsize(path)} bytes -> {path}")
        except Exception:
            print(f"  {label} FAIL:", traceback.format_exc().splitlines()[-1])

    print("\n=== exports ===")
    export("STL", "{533E9A98-FC3B-11D4-8E7E-0010B541CD80}", os.path.join(OUT, "probe.stl"))
    export("STEP", "{90AF7F40-0C01-11D5-8E83-0010B541CD80}", os.path.join(OUT, "probe.stp"))
    print("\nDONE")


if __name__ == "__main__":
    main()
