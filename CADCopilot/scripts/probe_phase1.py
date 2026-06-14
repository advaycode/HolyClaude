"""Live validation of the Phase-1 Inventor COM pipeline. Launches Inventor,
builds a 20mm cube via the exact API the backend will use, prints the bounding
box, and leaves the part open for inspection. Run with the venv python."""

import sys
import pythoncom
import win32com.client as w
from win32com.client import gencache

GUID = "{D98A091D-3A0F-4C3E-B36E-61F62068D488}"


def cm(mm):
    return mm / 10.0


def main():
    pythoncom.CoInitialize()
    print("generating early-binding module (makepy)...", flush=True)
    gencache.EnsureModule(GUID, 0, 1, 0)
    from win32com.client import constants as C

    try:
        app = w.GetActiveObject("Inventor.Application")
        print("attached to running Inventor")
    except Exception:
        print("launching Inventor (this can take ~30-60s)...", flush=True)
        app = gencache.EnsureDispatch("Inventor.Application")
        app.Visible = True
    print("version:", app.SoftwareVersion.DisplayName)

    # --- new part document -------------------------------------------------- #
    tmpl = app.FileManager.GetTemplateFile(C.kPartDocumentObject)
    print("part template:", tmpl)
    doc = app.Documents.Add(C.kPartDocumentObject, tmpl, True)
    doc = w.CastTo(doc, "PartDocument")  # base Document -> PartDocument for ComponentDefinition
    compdef = doc.ComponentDefinition
    tg = app.TransientGeometry

    # --- sketch on XY plane (WorkPlanes item 3 = XY) ------------------------ #
    xy = compdef.WorkPlanes.Item(3)
    sk = compdef.Sketches.Add(xy)
    print("sketch:", sk.Name)

    # --- 20mm rectangle ----------------------------------------------------- #
    rect = sk.SketchLines.AddAsTwoPointRectangle(
        tg.CreatePoint2d(0, 0), tg.CreatePoint2d(cm(20), cm(20))
    )
    prof = sk.Profiles.AddForSolid()
    print("profile curves:", prof.Count)

    # --- extrude 20mm, new body -------------------------------------------- #
    extrudes = compdef.Features.ExtrudeFeatures
    edef = extrudes.CreateExtrudeDefinition(prof, C.kNewBodyOperation)
    edef.SetDistanceExtent(cm(20), C.kPositiveExtentDirection)
    ext = extrudes.Add(edef)
    print("extrude feature:", ext.Name)

    doc.Update()

    # --- inspect ------------------------------------------------------------ #
    bodies = compdef.SurfaceBodies
    print("body count:", bodies.Count)
    b = bodies.Item(1)
    rb = b.RangeBox
    mn, mx = rb.MinPoint, rb.MaxPoint
    dims_mm = [(mx.X - mn.X) * 10, (mx.Y - mn.Y) * 10, (mx.Z - mn.Z) * 10]
    print("body name:", b.Name)
    print("bbox dims (mm):", [round(d, 4) for d in dims_mm])
    print("faces:", b.Faces.Count, "edges:", b.Edges.Count)

    print("PROBE_OK")


if __name__ == "__main__":
    main()
