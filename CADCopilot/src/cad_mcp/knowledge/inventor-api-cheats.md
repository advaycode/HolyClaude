# Inventor COM API cheats (validated live, for the execute_script escape hatch)

`execute_script` runs with these in scope: `app`, `doc` (PartDocument), `compdef`
(ComponentDefinition), `tg` (TransientGeometry), `tobj` (TransientObjects), `C`
(constants), `reg` (entity registry), `math`, `cm(mm)→cm`. Set `result` to return.
Everything is in **cm / radians**; use `cm(20)` for 20 mm.

## Verified idioms
- New part doc: `Documents.Add(C.kPartDocumentObject, app.FileManager.GetTemplateFile(C.kPartDocumentObject), True)` then `win32.CastTo(doc, "PartDocument")`.
- Origin planes: `compdef.WorkPlanes.Item(1)`=YZ, `Item(2)`=XZ, `Item(3)`=XY.
  Origin axes: `WorkAxes.Item(1)`=X, `(2)`=Y, `(3)`=Z.
- Sketch + rectangle: `sk = compdef.Sketches.Add(plane)`;
  `sk.SketchLines.AddAsTwoPointRectangle(tg.CreatePoint2d(x1,y1), tg.CreatePoint2d(x2,y2))`.
- Circle: `sk.SketchCircles.AddByCenterRadius(tg.CreatePoint2d(cx,cy), r)`.
- Profile: `prof = sk.Profiles.AddForSolid()` (uses all closed loops; construction excluded).
- **Extrude:** `ex = compdef.Features.ExtrudeFeatures`;
  `d = ex.CreateExtrudeDefinition(prof, C.kNewBodyOperation)`;
  `d.SetDistanceExtent(dist, C.kPositiveExtentDirection)`; `ex.Add(d)`  ← it's `.Add`, not AddByDefinition.
  Operations: `kJoinOperation/kCutOperation/kIntersectOperation/kNewBodyOperation`.
  Directions: `kPositiveExtentDirection/kNegativeExtentDirection/kSymmetricExtentDirection`.
- **Revolve:** axis must be a **sketch construction line** (a work axis often errors).
  `compdef.Features.RevolveFeatures.AddFull(prof, axisLine, op)` (360) or
  `AddByAngle(prof, axisLine, angle_rad, C.kPositiveExtentDirection, op)`.
- **Hole:** sketch points → `pts = tobj.CreateObjectCollection()` add `sk.SketchPoints`;
  `hf=compdef.Features.HoleFeatures`; `pl = hf.CreateSketchPlacementDefinition(pts)`;
  `hf.AddDrilledByThroughAllExtent(pl, dia, C.kNegativeExtentDirection)`. Drilling INTO
  the body is usually **kNegativeExtentDirection**; check `feat.HealthStatus == C.kUpToDateHealth`
  and retry the other direction if it errors.
- **Fillet:** `coll = tobj.CreateEdgeCollection()`; `coll.Add(edge)`;
  `compdef.Features.FilletFeatures.AddSimple(coll, radius)`.
- **Chamfer:** `ChamferFeatures.AddUsingDistance(edgeColl, dist)`.
- **Shell:** `coll = tobj.CreateFaceCollection()`; `sf=compdef.Features.ShellFeatures`;
  `sf.Add(sf.CreateShellDefinition(coll, thickness, C.kInsideShellDirection))`.
- **Patterns (use the DEFINITION form — the collection `.Add()` overload is unreliable):**
  `rpf=compdef.Features.RectangularPatternFeatures`;
  `d=rpf.CreateDefinition(featColl, xAxis, True, "4", "8 mm")`; set `d.YDirectionEntity`,
  `d.NaturalYDirection`, `d.YCount`, `d.YSpacing` for 2D; `rpf.AddByDefinition(d)`.
  `cpf=compdef.Features.CircularPatternFeatures`;
  `cpf.AddByDefinition(cpf.CreateDefinition(featColl, axis, True, "6", "360 deg", True))`.
- **Mirror:** `compdef.Features.MirrorFeatures.Add(featColl, planeEntity, False)`.
- **Boolean:** `compdef.Features.CombineFeatures.Add(baseBody, toolBodyColl, C.kJoinOperation)`
  (or kCutOperation / kIntersectOperation).
- **Face geometry:** `face.SurfaceType` (`C.kPlaneSurface/kCylinderSurface/...`);
  planar → `face.Geometry.Normal` (plane normal — orient outward by sign of
  dot(normal, faceCenter−bodyCenter)); cylinder → `face.Geometry.Radius`; a point on the
  face → `face.PointOnFace`; area → `face.Evaluator.Area` (cm²). Faces have **no RangeBox**.
- **Edge geometry:** `edge.GeometryType` (`C.kLineSegmentCurve/kCircleCurve/...`),
  `edge.StartVertex.Point` / `StopVertex.Point`; length via
  `ev=edge.Evaluator; ext=ev.GetParamExtents(); ev.GetLengthAtParam(ext[0], ext[1])`.
- **Params:** `compdef.Parameters.UserParameters.AddByExpression(name, "40 mm", C.kMillimeterLengthUnits)`;
  `param.Value` is cm, `param.Expression` the text.
- **Body RangeBox:** `b.RangeBox.MinPoint/MaxPoint` (.X/.Y/.Z in cm).
- **Export:** translator add-ins via `win32.CastTo(app.ApplicationAddIns.ItemById(clsid), "TranslatorAddIn")`;
  STL `{533E9A98-FC3B-11D4-8E7E-0010B541CD80}`, STEP `{90AF7F40-0C01-11D5-8E83-0010B541CD80}`,
  OBJ `{F539FB09-FC01-4260-A429-1818B14D6BAC}`. Then CreateTranslationContext (kFileBrowseIOMechanism)
  + CreateNameValueMap + CreateDataMedium(FileName) → `tr.SaveCopyAs(doc, ctx, opts, medium)`.
- **iLogic:** `app.ApplicationAddIns.ItemById("{3BDD8D79-2179-4B11-8A5A-257B1C0263AC}").Automation.RunRule(doc, ruleName)`.

## Gotchas
- COM is STA — all of this runs on the backend's single worker thread (the harness
  handles it; inside execute_script you're already there).
- `Documents.Add` returns a base `Document`; CastTo the specific interface for
  `ComponentDefinition`.
- After any feature that changes a body, old face/edge handles go stale — re-query.
