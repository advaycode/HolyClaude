# Inventor + Fusion full API spec (for execute_script)
Exact signatures for every feature, extracted from the makepy type library + Fusion docs.
Use these in `execute_script` for anything without a dedicated tool.

## sketch-geometry
### sketch_arc_add_center_start_end
- params: sketch (PlanarSketch), center_point (Point2d), start_point (Point2d), end_point (Point2d), counter_clockwise (bool, default=True) -> SketchArc
- Inventor: SketchArcs.AddByCenterStartEndPoint(CenterPoint, StartPoint, EndPoint, CounterClockwise=True) -> SketchArc. InvokeTypes(83897345, LCID, 1, (9,0), ((9,1),(9,1),(9,1),(11,49))). Radius calculated from center to start. CounterClockwise default True.
- Fusion: sketch.sketchCurves.sketchArcs.addByCenterStartEndPoint(center_point: Point3D, start_point: Point3D, end_point: Point3D, counter_clockwise: bool) -> SketchArc. In Fusion, arcs are 3D but constrained to sketch plane.
### sketch_arc_add_three_points
- params: sketch (PlanarSketch), start_point (Point2d), mid_point (Point2d), end_point (Point2d) -> SketchArc
- Inventor: SketchArcs.AddByThreePoints(StartPoint, MidPoint, EndPoint) -> SketchArc. InvokeTypes(83897347, LCID, 1, (9,0), ((9,1),(9,1),(9,1))). Three points define arc uniquely; arc passes through all three.
- Fusion: sketch.sketchCurves.sketchArcs.addByThreePoints(start_point: Point3D, through_point: Point3D, end_point: Point3D) -> SketchArc
### sketch_arc_add_fillet
- params: sketch (PlanarSketch), entity_one (SketchEntity), entity_two (SketchEntity), radius (double cm), point_on_entity_one (Point2d), point_on_entity_two (Point2d) -> SketchArc
- Inventor: SketchArcs.AddByFillet(EntityOne, EntityTwo, Radius, PointOnEntityOne, PointOnEntityTwo) -> SketchArc. InvokeTypes(83897348, LCID, 1, (9,0), ((9,1),(9,1),(12,1),(9,1),(9,1))). Radius is VT_CY (currency/double). Points define which side of each entity to fillet.
- Fusion: sketch.sketchCurves.sketchArcs.addFillet(geometryOne: SketchEntity, geometryTwo: SketchEntity, radius: float) -> SketchArc. Fusion does not require explicit points; infers from constraint context.
### sketch_circle_add_center_radius
- params: sketch (PlanarSketch), center_point (Point2d), radius (double cm) -> SketchCircle
- Inventor: SketchCircles.AddByCenterRadius(CenterPoint, Radius) -> SketchCircle. InvokeTypes(83898369, LCID, 1, (9,0), ((9,1),(5,1))). Radius is VT_R4 (float/double).
- Fusion: sketch.sketchCurves.sketchCircles.addByCenterRadius(center: Point3D, radius: float) -> SketchCircle
### sketch_circle_add_three_points
- params: sketch (PlanarSketch), point_one (Point2d), point_two (Point2d), point_three (Point2d) -> SketchCircle
- Inventor: SketchCircles.AddByThreePoints(PointOne, PointTwo, PointThree) -> SketchCircle. InvokeTypes(83898370, LCID, 1, (9,0), ((9,1),(9,1),(9,1))). Three non-collinear points define circle uniquely.
- Fusion: sketch.sketchCurves.sketchCircles.addByThreePoints(point_one: Point3D, point_two: Point3D, point_three: Point3D) -> SketchCircle
### sketch_ellipse_add
- params: sketch (PlanarSketch), center_point (Point2d), major_axis_vector (Vector2d), major_radius (double cm), minor_radius (double cm) -> SketchEllipse
- Inventor: SketchEllipses.Add(CenterPoint, MajorAxisVector, MajorRadius, MinorRadius) -> SketchEllipse. InvokeTypes(83898113, LCID, 1, (9,0), ((9,1),(9,1),(5,1),(5,1))). MajorAxisVector defines orientation; both radii are VT_R4.
- Fusion: sketch.sketchCurves.sketchEllipses.add(center: Point3D, major_axis_direction: Vector3D, major_radius: float, minor_radius: float) -> SketchEllipse
### sketch_spline_add
- params: sketch (PlanarSketch), fit_points (array of Point2d), fit_method (int, default=26370) -> SketchSpline
- Inventor: SketchSplines.Add(FitPoints, FitMethod=26370) -> SketchSpline. InvokeTypes(83897858, LCID, 1, (9,0), ((9,1),(3,49))). FitPoints is VT_DISPATCH array. FitMethod default 26370 (kDefaultFitMethod).
- Fusion: sketch.sketchCurves.sketchSplines.add(fit_points: list[Point3D], fit_method: int = FitMethod.CubicBSpline) -> SketchSpline
### sketch_polygon_add
- params: sketch (PlanarSketch), num_sides (int), center_point (Point2d), circumference_point (Point2d), inscribed (bool) -> SketchEntitiesEnumerator
- Inventor: SketchLines.AddAsPolygon(NumberOfSides, CenterPoint, CircumferencePoint, Inscribed) -> SketchEntitiesEnumerator. InvokeTypes(83896324, LCID, 1, (9,0), ((3,1),(9,1),(9,1),(11,1))). Inscribed=true: vertices on circle; false: sides tangent to circle.
- Fusion: sketch.sketchCurves.sketchLines.addPolygon(center: Point3D, vertex_point: Point3D, number_of_sides: int) -> SketchEntitiesEnumerator. Fusion infers inscribed/circumscribed from context.
### sketch_point_add
- params: sketch (PlanarSketch), point (Point2d), hole_center (bool, default=True) -> SketchPoint
- Inventor: SketchPoints.Add(Point, HoleCenter=True) -> SketchPoint. InvokeTypes(83896833, LCID, 1, (9,0), ((9,1),(11,49))). HoleCenter marks point as datum hole center if true.
- Fusion: sketch.sketchPoints.add(point: Point3D) -> SketchPoint. Fusion does not expose hole center as API parameter; use constraints instead.
### sketch_line_add_two_points
- params: sketch (PlanarSketch), start_point (Point2d), end_point (Point2d) -> SketchLine
- Inventor: SketchLines.AddByTwoPoints(StartPoint, EndPoint) -> SketchLine. InvokeTypes(83896321, LCID, 1, (9,0), ((9,1),(9,1))). Returns single SketchLine entity.
- Fusion: sketch.sketchCurves.sketchLines.addByTwoPoints(start_point: Point3D, end_point: Point3D) -> SketchLine
### sketch_line_add_midpoint_end
- params: sketch (PlanarSketch), mid_point (Point2d), end_point (Point2d) -> SketchLine
- Inventor: SketchLines.AddByMidEndPoints(MidPoint, EndPoint) -> SketchLine. InvokeTypes(83896327, LCID, 1, (9,0), ((9,1),(9,1))). Computes other endpoint from midpoint symmetry.
- Fusion: n/a - Fusion does not expose midpoint/endpoint construction directly; use construction geometry + coincident constraints
### sketch_rectangle_two_point
- params: sketch (PlanarSketch), corner_one (Point2d), corner_two (Point2d) -> SketchEntitiesEnumerator
- Inventor: SketchLines.AddAsTwoPointRectangle(CornerPointOne, CornerPointTwo) -> SketchEntitiesEnumerator. InvokeTypes(83896322, LCID, 1, (9,0), ((9,1),(9,1))). Returns 4 lines; axis-aligned to sketch XY.
- Fusion: sketch.sketchCurves.sketchLines.addAsTwoPointRectangle(corner_one: Point3D, corner_two: Point3D) -> SketchEntitiesEnumerator
### sketch_rectangle_three_point
- params: sketch (PlanarSketch), base_point_one (Point2d), base_point_two (Point2d), height_point (Point2d) -> SketchEntitiesEnumerator
- Inventor: SketchLines.AddAsThreePointRectangle(BasePointOne, BasePointTwo, HeightPoint) -> SketchEntitiesEnumerator. InvokeTypes(83896323, LCID, 1, (9,0), ((9,1),(9,1),(9,1))). BasePointOne-BasePointTwo define base; HeightPoint defines height and orientation.
- Fusion: sketch.sketchCurves.sketchLines.addAsThreePointRectangle(base_point_one: Point3D, base_point_two: Point3D, height_point: Point3D) -> SketchEntitiesEnumerator
### sketch_rectangle_centered
- params: sketch (PlanarSketch), center_point (Point2d), corner_point (Point2d) -> SketchEntitiesEnumerator
- Inventor: SketchLines.AddAsTwoPointCenteredRectangle(CenterPoint, CornerPoint) -> SketchEntitiesEnumerator. InvokeTypes(83896325, LCID, 1, (9,0), ((9,1),(9,1))). Axis-aligned; corner defines half-dimensions.
- Fusion: sketch.sketchCurves.sketchLines.addAsTwoPointCenteredRectangle(center: Point3D, corner: Point3D) -> SketchEntitiesEnumerator
### sketch_rectangle_three_point_centered
- params: sketch (PlanarSketch), center_point (Point2d), edge_point (Point2d), width_point (Point2d) -> SketchEntitiesEnumerator
- Inventor: SketchLines.AddAsThreePointCenteredRectangle(CenterPoint, EdgePoint, WidthPoint) -> SketchEntitiesEnumerator. InvokeTypes(83896326, LCID, 1, (9,0), ((9,1),(9,1),(9,1))). Center + one edge direction + perpendicular width.
- Fusion: sketch.sketchCurves.sketchLines.addAsThreePointCenteredRectangle(center: Point3D, edge_point: Point3D, width_point: Point3D) -> SketchEntitiesEnumerator
### sketch_slot_straight_center_to_center
- params: sketch (PlanarSketch), start_point (Point2d), end_point (Point2d), width (double cm) -> SketchEntitiesEnumerator
- Inventor: PlanarSketch.AddStraightSlotByCenterToCenter(StartPoint, EndPoint, Width) -> SketchEntitiesEnumerator. InvokeTypes(83890732, LCID, 1, (9,0), ((9,1),(9,1),(5,1))). Returns composite line + arcs.
- Fusion: sketch.sketchCurves.sketchLines.addSlot(center_start: Point3D, center_end: Point3D, width: float, slot_type: SlotType.CenterToCenter) -> SketchEntitiesEnumerator
### sketch_slot_straight_overall
- params: sketch (PlanarSketch), start_point (Point2d), end_point (Point2d), width (double cm) -> SketchEntitiesEnumerator
- Inventor: PlanarSketch.AddStraightSlotByOverall(StartPoint, EndPoint, Width) -> SketchEntitiesEnumerator. InvokeTypes(83890733, LCID, 1, (9,0), ((9,1),(9,1),(5,1))). Points define overall slot extent.
- Fusion: sketch.sketchCurves.sketchLines.addSlot(start: Point3D, end: Point3D, width: float, slot_type: SlotType.Overall) -> SketchEntitiesEnumerator
### sketch_slot_straight_slot_center
- params: sketch (PlanarSketch), center_point (Point2d), end_point (Point2d), width (double cm) -> SketchEntitiesEnumerator
- Inventor: PlanarSketch.AddStraightSlotBySlotCenter(CenterPoint, EndPoint, Width) -> SketchEntitiesEnumerator. InvokeTypes(83890734, LCID, 1, (9,0), ((9,1),(9,1),(5,1))). CenterPoint is slot midpoint.
- Fusion: sketch.sketchCurves.sketchLines.addSlot(center: Point3D, end_point: Point3D, width: float, slot_type: SlotType.SlotCenter) -> SketchEntitiesEnumerator
### sketch_slot_arc_three_point
- params: sketch (PlanarSketch), start_point (Point2d), mid_point (Point2d), end_point (Point2d), width (double cm) -> SketchEntitiesEnumerator
- Inventor: PlanarSketch.AddArcSlotByThreePointArc(StartPoint, MidPoint, EndPoint, Width) -> SketchEntitiesEnumerator. InvokeTypes(83890735, LCID, 1, (9,0), ((9,1),(9,1),(9,1),(5,1))). Three points define arc centerline.
- Fusion: sketch.sketchCurves.sketchLines.addArcSlot(start: Point3D, mid: Point3D, end: Point3D, width: float, slot_type: SlotType.ThreePointArc) -> SketchEntitiesEnumerator
### sketch_slot_arc_center_point
- params: sketch (PlanarSketch), center_point (Point2d), start_point (Point2d), sweep_angle (double degrees), width (double cm) -> SketchEntitiesEnumerator
- Inventor: PlanarSketch.AddArcSlotByCenterPointArc(CenterPoint, StartPoint, SweepAngle, Width) -> SketchEntitiesEnumerator. InvokeTypes(83890736, LCID, 1, (9,0), ((9,1),(9,1),(5,1),(5,1))). SweepAngle in degrees.
- Fusion: sketch.sketchCurves.sketchLines.addArcSlot(center: Point3D, start: Point3D, sweep_angle_degrees: float, width: float) -> SketchEntitiesEnumerator
### sketch_equation_curve_add
- params: sketch (PlanarSketch), equation_type (int), coordinate_system_type (int), x_or_radius (string expr), y_or_theta (string expr), min_value (double), max_value (double) -> SketchEquationCurve
- Inventor: SketchEquationCurves.Add(EquationType, CoordinateSystemType, XValueOrRadius, YValueOrTheta, MinValue, MaxValue) -> SketchEquationCurve. InvokeTypes(84019201, LCID, 1, (9,0), ((3,1),(3,1),(8,1),(8,1),(12,1),(12,1))). EquationType: 0=Cartesian, 1=Polar. CoordinateSystemType enums. X/Y are string expressions (e.g., 't', 't^2').
- Fusion: sketch.sketchCurves.sketchEquationCurves.add(expression_type: ExpressionType, coordinate_type: CoordinateType, x_equation: str, y_equation: str, min_value: float, max_value: float) -> SketchEquationCurve
### sketch_offset_distance
- params: sketch (PlanarSketch), sketch_entities (array SketchEntity), offset_distance (double cm), natural_offset_direction (bool), include_connected (bool, default=False), create_offset_constraints (bool, default=True) -> SketchEntitiesEnumerator
- Inventor: PlanarSketch.OffsetSketchEntitiesUsingDistance(SketchEntities, OffsetDistance, NaturalOffsetDirection, IncludeConnectedEntities=False, CreateOffsetConstraints=True) -> SketchEntitiesEnumerator. InvokeTypes(83890721, LCID, 1, (9,0), ((9,1),(5,1),(11,1),(11,49),(11,49))). NaturalOffsetDirection: true=outward from curve. Returns new offset entities.
- Fusion: sketch.sketchCurves.offsetSketchEntities(entities: list[SketchEntity], offset_distance: float) -> SketchEntitiesEnumerator. Fusion infers direction from geometry.
### sketch_offset_point
- params: sketch (PlanarSketch), sketch_entities (array SketchEntity), offset_point (Point2d), include_connected (bool, default=False), create_offset_constraints (bool, default=True) -> SketchEntitiesEnumerator
- Inventor: PlanarSketch.OffsetSketchEntitiesUsingPoint(SketchEntities, OffsetPoint, IncludeConnectedEntities=False, CreateOffsetConstraints=True) -> SketchEntitiesEnumerator. InvokeTypes(83890722, LCID, 1, (9,0), ((9,1),(9,1),(11,49),(11,49))). OffsetPoint defines offset magnitude and direction.
- Fusion: n/a - Fusion does not support point-based offset; use distance-based with computed offset.
### sketch_project_geometry
- params: sketch (PlanarSketch), entity (3D entity: Edge, Face, WireEdge, etc.) -> SketchEntity (reference)
- Inventor: PlanarSketch.AddByProjectingEntity(Entity) -> SketchEntity. InvokeTypes(83890723, LCID, 1, (9,0), ((9,1),)). Projects edge/curve onto sketch plane along plane normal. Result is reference (construction) geometry.
- Fusion: sketch.project(entity: BRepEdge) -> SketchEntity. Returns projected reference entity.
### sketch_project_silhouette
- params: sketch (PlanarSketch), face (Face), proximity_point (Point2d) -> SketchEntity
- Inventor: PlanarSketch.AddBySilhouette(Face, ProximityPoint) -> SketchEntity. InvokeTypes(83924740, LCID, 1, (9,0), ((9,1),(9,1))). ProximityPoint selects which silhouette if multiple. Returns reference geometry.
- Fusion: sketch.projectSilhouette(face: BRepFace) -> SketchEntity. Fusion automatically selects silhouette nearest to current view.
### sketch_project_cuts
- params: sketch (PlanarSketch) -> ProjectedCut
- Inventor: ProjectedCuts.Add() -> ProjectedCut. InvokeTypes(84005377, LCID, 1, (9,0), ()). Access via sketch.ProjectedCuts.Add(). Creates all intersection curves as reference geometry.
- Fusion: sketch.projectCutEdges() -> SketchEntitiesEnumerator. Automatically projects all cut edges.
### sketch_rectangular_pattern
- params: sketch (PlanarSketch), geometries (array SketchEntity), x_direction_entity (SketchEntity axis), x_count (int), x_spacing (double cm), y_direction_entity (SketchEntity), y_count (int), y_spacing (double cm), natural_x_dir (bool, default=None), x_symmetric (bool, default=None), natural_y_dir (bool, default=None), y_symmetric (bool, default=None), associative (bool, default=None), fitted (bool, default=None) -> SketchRectangularPattern
- Inventor: SketchRectangularPatterns.CreateDefinition(Geometries, XDirectionEntity, XCount, NaturalXDirection, XDirectionSymmetric, XSpacing, YDirectionEntity, YCount, NaturalYDirection, YDirectionSymmetric, YSpacing, Associative, Fitted, ...) -> SketchRectangularPatternDefinition; then .Add(Definition) -> SketchRectangularPattern. InvokeTypes(84085762, LCID, 1, (9,0), ((9,1),(9,1),(12,1),(12,17),...)).
- Fusion: sketch.sketchRectangularPatterns.add(rect_pattern_definition) where definition.geometries, direction_1, quantity_1, spacing_1, direction_2, quantity_2, spacing_2 set pattern parameters.
### sketch_circular_pattern
- params: sketch (PlanarSketch), geometries (array SketchEntity), axis_entity (SketchEntity), count (int), angle (double degrees), symmetric (bool, default=None), associative (bool, default=None), fitted (bool, default=None), natural_axis_direction (bool, default=None) -> SketchCircularPattern
- Inventor: SketchCircularPatterns.CreateDefinition(Geometries, AxisEntity, NaturalAxisDirection, Count, Angle, Symmetric, Associative, Fitted, ...) -> SketchCircularPatternDefinition; then .Add(Definition) -> SketchCircularPattern. InvokeTypes(84087042, LCID, 1, (9,0), ((9,1),(9,1),(12,17),(12,17),...)).
- Fusion: sketch.sketchCircularPatterns.add(circ_pattern_definition) where definition.geometries, axis_entity, quantity, angle_between_occurrences, is_symmetric.
### sketch_textbox_add_fitted
- params: sketch (PlanarSketch), position (Point2d), formatted_text (string), text_style (TextStyle, optional) -> TextBox
- Inventor: TextBoxes.AddFitted(Position, FormattedText, TextStyle=None) -> TextBox. InvokeTypes(117445633, LCID, 1, (9,0), ((9,1),(8,1),(12,17))). FormattedText can include HTML/rich formatting.
- Fusion: sketch.sketchTexts.add(point: Point3D, text_string: str) -> SketchText. Fusion does not expose rich text formatting via API.
### sketch_textbox_add_rectangle
- params: sketch (PlanarSketch), corner_one (Point2d), corner_two (Point2d), formatted_text (string), text_style (TextStyle, optional) -> TextBox
- Inventor: TextBoxes.AddByRectangle(CornerOne, CornerTwo, FormattedText, TextStyle=None) -> TextBox. InvokeTypes(117445634, LCID, 1, (9,0), ((9,1),(9,1),(8,1),(12,17))).
- Fusion: n/a - Fusion text uses fixed size; rectangle-bounded text not available via API.
### sketch3d_create
- params: component_def (ComponentDefinition) -> Sketch3D
- Inventor: ComponentDefinition.Sketches3D.Add() -> Sketch3D. Access via compdef.Sketches3D (collection). No parameters; creates empty 3D sketch.
- Fusion: design.rootComponent.sketches.add(plane) where plane can be XY/XZ/YZ workplane or custom plane. Always requires reference plane.
### sketch3d_line_add
- params: sketch3d (Sketch3D), start_point (Point3d), end_point (Point3d), use_auto_bend (bool, default=True), bend_radius (double cm, optional) -> SketchLine3D
- Inventor: Sketch3D.SketchLines3D.AddByTwoPoints(StartPoint, EndPoint, UseAutoBend=True, BendRadius=None) -> SketchLine3D. InvokeTypes(83937537, LCID, 1, (9,0), ((9,1),(9,1),(11,49),(12,17))). UseAutoBend auto-adds bends at corners if true. BendRadius optional.
- Fusion: sketch.sketchCurves.sketchLines.addByTwoPoints(start_point: Point3D, end_point: Point3D) -> SketchLine3D. Fusion does not expose auto-bend via API.
### sketch3d_point_add
- params: sketch3d (Sketch3D), point (Point3d), hole_center (bool, default=True) -> SketchPoint3D
- Inventor: Sketch3D.SketchPoints3D.Add(Point, HoleCenter=True) -> SketchPoint3D. InvokeTypes(83938049, LCID, 1, (9,0), ((9,1),(11,49))).
- Fusion: sketch.sketchPoints.add(point: Point3D) -> SketchPoint3D (in 3D sketch context)
### sketch3d_circle_add
- params: sketch3d (Sketch3D), center_point (Point3d), normal_vector (Vector3d), radius (double cm) -> SketchCircle3D
- Inventor: Sketch3D.SketchCircles3D.AddByCenterRadius(CenterPoint, Normal, Radius) -> SketchCircle3D. InvokeTypes(83940865, LCID, 1, (9,0), ((9,1),(9,1),(5,1))). Normal defines plane of circle.
- Fusion: sketch.sketchCurves.sketchCircles.addByCenterRadius(center: Point3D, radius: float) -> SketchCircle3D. Normal inferred from sketch plane.
### sketch3d_arc_add_center_start_end
- params: sketch3d (Sketch3D), center_point (Point3d), start_point (Point3d), end_point (Point3d), normal_vector (Vector3d), counter_clockwise (bool, default=False) -> SketchArc3D
- Inventor: Sketch3D.SketchArcs3D.AddByCenterStartEndPoint(CenterPoint, StartPoint, EndPoint, Normal, CounterClockwise=False) -> SketchArc3D. InvokeTypes(83938562, LCID, 1, (9,0), ((9,1),(9,1),(9,1),(12,17),(11,49))).
- Fusion: sketch.sketchCurves.sketchArcs.addByCenterStartEndPoint(center: Point3D, start: Point3D, end: Point3D, counter_clockwise: bool = False) -> SketchArc3D
### sketch3d_spline_add
- params: sketch3d (Sketch3D), fit_points (array Point3d), fit_method (int, default=26370) -> SketchSpline3D
- Inventor: Sketch3D.SketchSplines3D.Add(FitPoints, FitMethod=26370) -> SketchSpline3D. InvokeTypes(83940097, LCID, 1, (9,0), ((9,1),(3,49))). Same as 2D spline but points are 3D.
- Fusion: sketch.sketchCurves.sketchSplines.add(fit_points: list[Point3D], fit_method: int = FitMethod.CubicBSpline) -> SketchSpline3D (in 3D sketch)
### sketch3d_equation_curve_add
- params: sketch3d (Sketch3D), coordinate_system_type (int), x_or_radius (string expr), y_or_theta (string expr), z_or_phi (string expr), min_value (double), max_value (double) -> SketchEquationCurve3D
- Inventor: Sketch3D.SketchEquationCurves3D.Add(CoordinateSystemType, XValueOrRadius, YValueOrTheta, ZValueOrPhi, MinValue, MaxValue) -> SketchEquationCurve3D. InvokeTypes(84019713, LCID, 1, (9,0), ((3,1),(8,1),(8,1),(8,1),(12,1),(12,1))). CoordinateSystemType: 0=Cartesian, 1=Cylindrical, 2=Spherical.
- Fusion: sketch.sketchCurves.sketchEquationCurves.add(coordinate_type: CoordinateType, x_equation: str, y_equation: str, z_equation: str, min_value: float, max_value: float) -> SketchEquationCurve3D (in 3D sketch)

**enums:** SketchEntityType: kSketchLineType=1, kSketchArcType=2, kSketchCircleType=3, kSketchEllipseType=5, kSketchEllipticalArcType=6, kSketchSplineType=7, kSketchPointType=8, kSketchConstructionLineType=9, kSketchOffsetSplineType=10, kSketchEquationCurveType=11; FitMethod: kDefaultFitMethod=26370, kAutoFitMethod=26368, kMaxCurvatureFitMethod=26369; EquationType (2D): kCartesian=0, kPolar=1; CoordinateSystemType (3D): kCartesian=0, kCylindrical=1, kSpherical=2; SketchPointType: kDefault=0, kHoleCenter=1; LineType: kNormalLineType=0, kConstructionLineType=1, kReferenceLineType=2; OffsetDirection: kNaturalOffsetDirection=True, kReverseOffsetDirection=False

## sketch-constraints-dims
### add_geometric_constraint_coincident
- params: EntityOne: SketchEntity, EntityTwo: SketchEntity → CoincidentConstraint
- Inventor: GeometricConstraints.AddCoincident(EntityOne, EntityTwo) → CoincidentConstraint (DISPID 83899905). Parameters are 9,1 (object required). Accepts SketchPoint, SketchLine, SketchCircle, etc. No enum needed.

Example:
constraint = sketch.GeometricConstraints.AddCoincident(point1, point2)
constraint = sketch.GeometricConstraints.AddCoincident(pointOnLine, line)
- Fusion: sketch.geometricConstraints.addCoincidentConstraint(SketchEntity, SketchEntity) → GeometricConstraint (Fusion 360 API docs: geometry.constraints.addCoincident)
### add_geometric_constraint_collinear
- params: EntityOne: SketchEntity, EntityTwo: SketchEntity, UseEllipseOneMajorAxis: bool=true, UseEllipseTwoMajorAxis: bool=true → CollinearConstraint
- Inventor: GeometricConstraints.AddCollinear(EntityOne, EntityTwo, UseEllipseOneMajorAxis, UseEllipseTwoMajorAxis) → CollinearConstraint (DISPID 83899906). Entity params are 9,1 (object required). Ellipse params are 11,49 (bool, optional default true). Example:
constraint = sketch.GeometricConstraints.AddCollinear(line1, line2)
constraint = sketch.GeometricConstraints.AddCollinear(ellipse1Axis, ellipse2Axis, True, False)
- Fusion: sketch.geometricConstraints.addCollinearConstraint(SketchEntity, SketchEntity) → GeometricConstraint
### add_geometric_constraint_concentric
- params: EntityOne: SketchEntity, EntityTwo: SketchEntity → ConcentricConstraint
- Inventor: GeometricConstraints.AddConcentric(EntityOne, EntityTwo) → ConcentricConstraint (DISPID 83899907). Entities must have centers (circles, arcs, ellipses). Example:
constraint = sketch.GeometricConstraints.AddConcentric(circle1, circle2)
constraint = sketch.GeometricConstraints.AddConcentric(point, arc)
- Fusion: sketch.geometricConstraints.addConcentricConstraint(SketchEntity, SketchEntity) → GeometricConstraint
### add_geometric_constraint_equal_length
- params: LineOne: SketchEntity, LineTwo: SketchEntity → EqualLengthConstraint
- Inventor: GeometricConstraints.AddEqualLength(LineOne, LineTwo) → EqualLengthConstraint (DISPID 83899908). Parameters are 9,1 (object required). Both inputs must be SketchLine. Example:
constraint = sketch.GeometricConstraints.AddEqualLength(line1, line2)
- Fusion: sketch.geometricConstraints.addEqualLengthConstraint(SketchLine, SketchLine) → GeometricConstraint
### add_geometric_constraint_equal_radius
- params: EntityOne: SketchEntity, EntityTwo: SketchEntity → EqualRadiusConstraint
- Inventor: GeometricConstraints.AddEqualRadius(EntityOne, EntityTwo) → EqualRadiusConstraint (DISPID 83899909). Parameters are 9,1 (object required). Both inputs must have radius (circles, arcs, ellipses). Example:
constraint = sketch.GeometricConstraints.AddEqualRadius(circle1, circle2)
constraint = sketch.GeometricConstraints.AddEqualRadius(arc1, arc2)
- Fusion: sketch.geometricConstraints.addEqualRadiusConstraint(SketchEntity, SketchEntity) → GeometricConstraint
### add_geometric_constraint_ground
- params: Entity: SketchEntity → GroundConstraint
- Inventor: GeometricConstraints.AddGround(Entity) → GroundConstraint (DISPID 83899910). Parameter is 9,1 (object required). Can apply to any SketchEntity. Example:
constraint = sketch.GeometricConstraints.AddGround(line1)
constraint = sketch.GeometricConstraints.AddGround(point1)
- Fusion: sketch.geometricConstraints.addFixedConstraint(SketchEntity) → GeometricConstraint
### add_geometric_constraint_horizontal
- params: Entity: SketchEntity, UseEllipseMajorAxis: bool=true → HorizontalConstraint
- Inventor: GeometricConstraints.AddHorizontal(Entity, UseEllipseMajorAxis) → HorizontalConstraint (DISPID 83899911). Entity is 9,1 (object required). UseEllipseMajorAxis is 11,49 (bool, optional default true). Example:
constraint = sketch.GeometricConstraints.AddHorizontal(line1)
constraint = sketch.GeometricConstraints.AddHorizontal(ellipse1, True)
- Fusion: sketch.geometricConstraints.addHorizontalConstraint(SketchEntity) → GeometricConstraint
### add_geometric_constraint_horizontal_align
- params: PointOne: SketchPoint, PointTwo: SketchPoint → HorizontalAlignConstraint
- Inventor: GeometricConstraints.AddHorizontalAlign(PointOne, PointTwo) → HorizontalAlignConstraint (DISPID 83899912). Parameters are 9,1 (object required). Both must be SketchPoint. Example:
constraint = sketch.GeometricConstraints.AddHorizontalAlign(point1, point2)
- Fusion: sketch.geometricConstraints.addHorizontalConstraint on two points (use symmetry or alignment constraint)
### add_geometric_constraint_midpoint
- params: Point: SketchPoint, Line: SketchEntity → MidpointConstraint
- Inventor: GeometricConstraints.AddMidpoint(Point, Line) → MidpointConstraint (DISPID 83899913). Parameters are 9,1 (object required). Point is SketchPoint, Line is SketchLine. Example:
constraint = sketch.GeometricConstraints.AddMidpoint(point1, line1)
- Fusion: sketch.geometricConstraints.addMidpointConstraint(SketchPoint, SketchLine) → GeometricConstraint
### add_geometric_constraint_midpoint_arc
- params: Point: SketchPoint, Arc: SketchEntity → MidpointConstraint
- Inventor: GeometricConstraints.AddMidPointToArc(Point, Arc) → MidpointConstraint (DISPID 83899922). Parameters are 9,1 (object required). Point is SketchPoint, Arc is SketchArc. Example:
constraint = sketch.GeometricConstraints.AddMidPointToArc(point1, arc1)
- Fusion: sketch.geometricConstraints.addMidpointConstraint(SketchPoint, SketchArc) → GeometricConstraint
### add_geometric_constraint_parallel
- params: EntityOne: SketchEntity, EntityTwo: SketchEntity, UseEllipseOneMajorAxis: bool=true, UseEllipseTwoMajorAxis: bool=true → ParallelConstraint
- Inventor: GeometricConstraints.AddParallel(EntityOne, EntityTwo, UseEllipseOneMajorAxis, UseEllipseTwoMajorAxis) → ParallelConstraint (DISPID 83899914). Entity params are 9,1 (object required). Ellipse params are 11,49 (bool, optional default true). Example:
constraint = sketch.GeometricConstraints.AddParallel(line1, line2)
constraint = sketch.GeometricConstraints.AddParallel(ellipse1Axis, ellipse2Axis)
- Fusion: sketch.geometricConstraints.addParallelConstraint(SketchEntity, SketchEntity) → GeometricConstraint
### add_geometric_constraint_perpendicular
- params: EntityOne: SketchEntity, EntityTwo: SketchEntity, UseEllipseOneMajorAxis: bool=true, UseEllipseTwoMajorAxis: bool=true → PerpendicularConstraint
- Inventor: GeometricConstraints.AddPerpendicular(EntityOne, EntityTwo, UseEllipseOneMajorAxis, UseEllipseTwoMajorAxis) → PerpendicularConstraint (DISPID 83899915). Entity params are 9,1 (object required). Ellipse params are 11,49 (bool, optional default true). Example:
constraint = sketch.GeometricConstraints.AddPerpendicular(line1, line2)
- Fusion: sketch.geometricConstraints.addPerpendicularConstraint(SketchEntity, SketchEntity) → GeometricConstraint
### add_geometric_constraint_smooth
- params: EntityOne: SketchEntity, EntityTwo: SketchEntity, ProximityPoint: Point2d (optional) → SmoothConstraint
- Inventor: GeometricConstraints.AddSmooth(EntityOne, EntityTwo, ProximityPoint) → SmoothConstraint (DISPID 83899921). Entity params are 9,1 (object required). ProximityPoint is 12,17 (variant, optional). ProximityPoint used to resolve ambiguity on curves with multiple intersection points. Example:
constraint = sketch.GeometricConstraints.AddSmooth(spline1, line1)
constraint = sketch.GeometricConstraints.AddSmooth(arc1, spline1, proximityPt)
- Fusion: sketch.geometricConstraints.addSmoothConstraint(SketchEntity, SketchEntity) → GeometricConstraint
### add_geometric_constraint_symmetry
- params: EntityOne: SketchEntity, EntityTwo: SketchEntity, SymmetryAxis: SketchEntity → SymmetryConstraint
- Inventor: GeometricConstraints.AddSymmetry(EntityOne, EntityTwo, SymmetryAxis) → SymmetryConstraint (DISPID 83899916). All params are 9,1 (object required). SymmetryAxis must be a SketchLine. Example:
constraint = sketch.GeometricConstraints.AddSymmetry(point1, point2, symmetryLine)
constraint = sketch.GeometricConstraints.AddSymmetry(line1, line2, axisLine)
- Fusion: sketch.geometricConstraints.addSymmetryConstraint(SketchEntity, SketchEntity, SketchEntity) → GeometricConstraint
### add_geometric_constraint_tangent
- params: EntityOne: SketchEntity, EntityTwo: SketchEntity, ProximityPoint: Point2d (optional) → TangentSketchConstraint
- Inventor: GeometricConstraints.AddTangent(EntityOne, EntityTwo, ProximityPoint) → TangentSketchConstraint (DISPID 83899920). Entity params are 9,1 (object required). ProximityPoint is 12,17 (variant, optional). ProximityPoint helps resolve multiple intersection points. Example:
constraint = sketch.GeometricConstraints.AddTangent(line1, circle1)
constraint = sketch.GeometricConstraints.AddTangent(arc1, spline1, proximityPt)
- Fusion: sketch.geometricConstraints.addTangentConstraint(SketchEntity, SketchEntity) → GeometricConstraint
### add_geometric_constraint_vertical
- params: Entity: SketchEntity, UseEllipseMajorAxis: bool=true → VerticalConstraint
- Inventor: GeometricConstraints.AddVertical(Entity, UseEllipseMajorAxis) → VerticalConstraint (DISPID 83899918). Entity is 9,1 (object required). UseEllipseMajorAxis is 11,49 (bool, optional default true). Example:
constraint = sketch.GeometricConstraints.AddVertical(line1)
constraint = sketch.GeometricConstraints.AddVertical(ellipse1, True)
- Fusion: sketch.geometricConstraints.addVerticalConstraint(SketchEntity) → GeometricConstraint
### add_geometric_constraint_vertical_align
- params: PointOne: SketchPoint, PointTwo: SketchPoint → VerticalAlignConstraint
- Inventor: GeometricConstraints.AddVerticalAlign(PointOne, PointTwo) → VerticalAlignConstraint (DISPID 83899919). Parameters are 9,1 (object required). Both must be SketchPoint. Example:
constraint = sketch.GeometricConstraints.AddVerticalAlign(point1, point2)
- Fusion: sketch.geometricConstraints.addVerticalConstraint on two points (use symmetry or alignment)
### add_dimension_arc_length
- params: Entity: SketchEntity, TextPoint: Point2d, Driven: bool=false → ArcLengthDimConstraint
- Inventor: DimensionConstraints.AddArcLength(Entity, TextPoint, Driven) → ArcLengthDimConstraint (DISPID 83905290). Entity is 9,1 (object required, must be SketchArc). TextPoint is 9,1 (object required, Point2d for label position). Driven is 11,49 (bool, optional default false = driving, true = driven/reference). Access Parameter property to change value: dim.Parameter.Value = 5.0 (in cm). Example:
dim = sketch.DimensionConstraints.AddArcLength(arc1, textPt)
dim.Parameter.Value = 3.5
dim.Driven = True
- Fusion: sketch.sketchDimensions.addArcLengthDimension(SketchArc, Point2d) → SketchDimension
### add_dimension_diameter
- params: Entity: SketchEntity, TextPoint: Point2d, Driven: bool=false → DiameterDimConstraint
- Inventor: DimensionConstraints.AddDiameter(Entity, TextPoint, Driven) → DiameterDimConstraint (DISPID 83905285). Entity is 9,1 (object required, must be SketchCircle or SketchArc). TextPoint is 9,1 (object required, Point2d for label position). Driven is 11,49 (bool, optional default false). Example:
dim = sketch.DimensionConstraints.AddDiameter(circle1, textPt)
dim.Parameter.Value = 10.0  # in cm
dim.Driven = False
- Fusion: sketch.sketchDimensions.addDiameterDimension(SketchEntity, Point2d) → SketchDimension
### add_dimension_ellipse_radius
- params: Entity: SketchEntity, MajorRadius: bool, TextPoint: Point2d, PositiveSide: Point2d, Driven: bool=false → EllipseRadiusDimConstraint
- Inventor: DimensionConstraints.AddEllipseRadius(Entity, MajorRadius, TextPoint, PositiveSide, Driven) → EllipseRadiusDimConstraint (DISPID 83905288). Entity is 9,1 (must be SketchEllipse or SketchEllipticalArc). MajorRadius is 11,1 (bool required: true=major, false=minor). TextPoint is 9,1 (Point2d for label). PositiveSide is 12,17 (Point2d variant for direction). Driven is 11,49 (bool, optional default false). Example:
dim = sketch.DimensionConstraints.AddEllipseRadius(ellipse1, True, textPt, dirPt)
dim.Parameter.Value = 5.0
- Fusion: sketch.sketchDimensions.addEllipseRadiusDimension(SketchEntity, bool, Point2d) → SketchDimension
### add_dimension_offset
- params: Line: SketchEntity, Entity: SketchEntity, TextPoint: Point2d, LinearDiameter: bool, Driven: bool=false → OffsetDimConstraint
- Inventor: DimensionConstraints.AddOffset(Line, Entity, TextPoint, LinearDiameter, Driven) → OffsetDimConstraint (DISPID 83905281). Line is 9,1 (object required, SketchLine reference). Entity is 9,1 (object required, SketchLine/Circle/Arc to measure distance to). TextPoint is 9,1 (Point2d for label). LinearDiameter is 11,1 (bool required: true=diameter, false=linear distance). Driven is 11,49 (bool, optional default false). GOTCHA: Despite AddTwoLineDistance not existing, AddOffset with LinearDiameter=false provides line-to-line distance. Example:
dim = sketch.DimensionConstraints.AddOffset(refLine, targetLine, textPt, False)
dim = sketch.DimensionConstraints.AddOffset(refLine, circle1, textPt, False)
dim.Parameter.Value = 2.5
- Fusion: sketch.sketchDimensions.addOffsetDimension(SketchLine, SketchEntity, Point2d) → SketchDimension
### add_dimension_offset_spline
- params: Line: SketchEntity, TextPoint: Point2d, Driven: bool=false → OffsetSplineDimConstraint
- Inventor: DimensionConstraints.AddOffsetSpline(Line, TextPoint, Driven) → OffsetSplineDimConstraint (DISPID 83905289). Line is 9,1 (object required, offset SketchSpline). TextPoint is 9,1 (Point2d for label). Driven is 11,49 (bool, optional default false). Example:
dim = sketch.DimensionConstraints.AddOffsetSpline(offsetSpline, textPt)
dim.Parameter.Value = 1.0
- Fusion: sketch.sketchDimensions.addOffsetDimension(SketchSpline, ...) → SketchDimension
### add_dimension_radius
- params: Entity: SketchEntity, TextPoint: Point2d, Driven: bool=false → RadiusDimConstraint
- Inventor: DimensionConstraints.AddRadius(Entity, TextPoint, Driven) → RadiusDimConstraint (DISPID 83905286). Entity is 9,1 (object required, SketchCircle or SketchArc). TextPoint is 9,1 (Point2d for label position). Driven is 11,49 (bool, optional default false). Example:
dim = sketch.DimensionConstraints.AddRadius(circle1, textPt)
dim.Parameter.Value = 5.0  # in cm
- Fusion: sketch.sketchDimensions.addRadiusDimension(SketchEntity, Point2d) → SketchDimension
### add_dimension_tangent_distance
- params: EntityOne: SketchEntity, EntityTwo: SketchEntity, ProximityPointOne: Point2d, ProximityPointTwo: Point2d, TextPoint: Point2d, LinearDiameter: bool, Driven: bool=false → TangentDistanceDimConstraint
- Inventor: DimensionConstraints.AddTangentDistance(EntityOne, EntityTwo, ProximityPointOne, ProximityPointTwo, TextPoint, LinearDiameter, Driven) → TangentDistanceDimConstraint (DISPID 83905287). EntityOne/Two are 9,1 (object required). ProximityPointOne/Two are 9,1 (Point2d for resolving tangent points). TextPoint is 9,1 (Point2d for label). LinearDiameter is 11,1 (bool required). Driven is 11,49 (bool, optional default false). Example:
dim = sketch.DimensionConstraints.AddTangentDistance(line1, circle1, pt1, pt2, textPt, False)
dim.Parameter.Value = 3.0
- Fusion: sketch.sketchDimensions.addDistanceDimension(...) (Fusion uses different approach for tangent distance)
### add_dimension_three_point_angle
- params: PointOne: SketchPoint, PointTwo: SketchPoint (vertex), PointThree: SketchPoint, TextPoint: Point2d, Driven: bool=false → ThreePointAngleDimConstraint
- Inventor: DimensionConstraints.AddThreePointAngle(PointOne, PointTwo, PointThree, TextPoint, Driven) → ThreePointAngleDimConstraint (DISPID 83905284). All point params are 9,1 (object required, SketchPoint). TextPoint is 9,1 (Point2d for label). Driven is 11,49 (bool, optional default false). PointTwo is vertex of angle. Example:
dim = sketch.DimensionConstraints.AddThreePointAngle(pt1, vertex, pt3, textPt)
dim.Parameter.Value = 45.0  # in degrees
- Fusion: sketch.sketchDimensions.addAngularDimension(SketchPoint, SketchPoint, SketchPoint, Point2d) → SketchDimension
### add_dimension_two_line_angle
- params: LineOne: SketchEntity, LineTwo: SketchEntity, TextPoint: Point2d, Driven: bool=false → TwoLineAngleDimConstraint
- Inventor: DimensionConstraints.AddTwoLineAngle(LineOne, LineTwo, TextPoint, Driven) → TwoLineAngleDimConstraint (DISPID 83905283). Line params are 9,1 (object required, SketchLine). TextPoint is 9,1 (Point2d for label). Driven is 11,49 (bool, optional default false). Creates acute angle by default. Example:
dim = sketch.DimensionConstraints.AddTwoLineAngle(line1, line2, textPt)
dim.Parameter.Value = 60.0  # in degrees
- Fusion: sketch.sketchDimensions.addAngularDimension(SketchLine, SketchLine, Point2d) → SketchDimension
### add_dimension_two_point_distance
- params: PointOne: SketchPoint, PointTwo: SketchPoint, Orientation: int (enum DimensionOrientationEnum), TextPoint: Point2d, Driven: bool=false → TwoPointDistanceDimConstraint
- Inventor: DimensionConstraints.AddTwoPointDistance(PointOne, PointTwo, Orientation, TextPoint, Driven) → TwoPointDistanceDimConstraint (DISPID 83905282). Point params are 9,1 (object required, SketchPoint). Orientation is 3,1 (int required, enum: kAlignedDim=19203, kHorizontalDim=19201, kVerticalDim=19202). TextPoint is 9,1 (Point2d for label). Driven is 11,49 (bool, optional default false). Example:
dim = sketch.DimensionConstraints.AddTwoPointDistance(pt1, pt2, C.kAlignedDim, textPt)
dim = sketch.DimensionConstraints.AddTwoPointDistance(pt1, pt2, C.kHorizontalDim, textPt)
dim.Parameter.Value = 10.0  # in cm
- Fusion: sketch.sketchDimensions.addDistanceDimension(SketchPoint, SketchPoint, SketchDimensionType, Point2d) → SketchDimension
### dimension_constraint_parameter
- params: DimensionConstraint.Parameter → Parameter object with Value property (float, unit: cm for linear, degrees for angular)
- Inventor: All DimensionConstraint subclasses expose Parameter property (DISPID 83907843, return type 9,0 = object). Parameter is a Parameter COM object with Value, Expression, Units properties. GOTCHA: Value changes require sketch to be dirty/updated; Driven flag must be False to drive dimension. Example:
dim = sketch.DimensionConstraints.AddRadius(circle1, textPt)
param = dim.Parameter
param.Value = 5.0  # Modify radius to 5 cm
print(param.Expression)  # Get formula if any
print(param.Units)  # Check units string
dim.Driven = False  # Must be driving (not driven/reference)
- Fusion: sketchDimension.parameter.value = number; parameter.expression = 'formula'; parameter.unit (Fusion uses different unit handling per document settings)
### dimension_constraint_driven
- params: DimensionConstraint.Driven → bool (false=driving/parametric, true=driven/reference)
- Inventor: All DimensionConstraint subclasses have Driven property (DISPID 83907842, type 11,0 = bool). Setting to True makes dimension reference-only (no driving). Default is False (driving). Example:
dim = sketch.DimensionConstraints.AddRadius(circle1, textPt)
if not dim.Driven:
    dim.Parameter.Value = 5.0
dim.Driven = True  # Convert to reference dimension
- Fusion: sketchDimension.isConstruction (opposite logic in Fusion: construction=reference)

**enums:** DimensionOrientationEnum: kAlignedDim=19203, kHorizontalDim=19201, kVerticalDim=19202 (used in AddTwoPointDistance Orientation param); AngleConstraintSolutionTypeEnum (3D only): kDirectedSolution=78593, kUndirectedSolution=78594, kReferenceVectorSolution=78595; ArcDimensionTypeEnum: kRadialArcDimension=65537, kDiametricArcDimension=65538, kAngleArcDimension=65539, kArcLengthArcDimension=65540, kChordLengthArcDimension=65541

## solid-features-a
### add_loft_feature
- params: sections: ObjectCollection, operation: PartFeatureOperationEnum, start_section_condition: LoftSectionEndConditionEnum=kNatural(34305), start_section_impact: cm=0.0, start_section_angle: deg=0.0, end_section_condition: LoftSectionEndConditionEnum=kNatural(34305), end_section_impact: cm=0.0, end_section_angle: deg=0.0, closed: bool=False, rails: ObjectCollection (optional), map_point_curves: MapPointCurves (optional), centerline: Path (optional)
- Inventor: LoftFeatures.Add(Definition) or LoftFeatures._Add(Sections, Operation, StartSectionCondition, StartSectionImpact, StartSectionAngle, EndSectionCondition, EndSectionImpact, EndSectionAngle, Closed, Rails, MapPointCurves). See gen_py line 68374-68427 (Add signature at 83912963) and 21-60 (CoilFeatures shows pattern). CreateLoftDefinition(Sections, Operation) returns LoftDefinition {FBEBA281-9346-4AC6-B324-6CEB7318BEBE}. LoftDefinition properties: Sections (ObjectCollection), Centerline (Path), Closed (bool), FirstSectionCondition/Angle/Impact/TangentPlane, LastSectionCondition/Angle/Impact/TangentPlane, LoftRails (LoftRails {3E43E559-0053-402D-BE5F-4AC170C11A04}), LoftType (int), MapPointCurves, MergeTangentFaces (bool), Operation (int). Must use: doc.ComponentDefinition.Features.LoftFeatures.CreateLoftDefinition(...) then .Add(defn); loft_def.Sections.Add(...) for each section.
- Fusion: loftFeatures.createDefinition(profiles, operation, startCondition, startImpact, startAngle, endCondition, endImpact, endAngle, closed, rails, mapPointCurves) → LoftFeatureDefinition; then design.features.loftFeatures.createFeature(definition)
### add_sweep_feature
- params: profile: Profile, path: Path, operation: PartFeatureOperationEnum, sweep_type: SweepTypeEnum, profile_orientation: ProfileOrientationEnum=kProfileNormalToPath(59649), guide_rail: Path (optional), guide_surface: Face (optional), profile_scaling: ProfileScalingEnum=kCentroid(59393), taper_angle: deg=0.0, twist_angle: deg=0.0, section_twist_points: ObjectCollection (optional), section_twist_vectors: ObjectCollection (optional)
- Inventor: SweepFeatures.Add(Definition) or AddUsingPath(Profile, SweepPath, Operation, ProfileOrientation, TaperAngle) or AddUsingPathAndGuideRail(Profile, SweepPath, GuideRail, Operation, ProfileScaling) or AddUsingPathAndGuideSurface(...) or AddUsingPathAndSectionTwists(...). See gen_py line 121846-122005. CreateSweepDefinition(SweepType, Profile, Path, Operation) returns SweepDefinition {938C8A20-C60B-47C8-A9F4-CDAA7CE06095}. SweepDefinition properties: Profile (Profile {8006A03A-ECC4-11D4-8DE9-0010B541CAA8}), Path (Path {86338055-4538-47A0-BD9B-06A8C4BD8D93}), GuideRail, GuideSurface, Operation, ProfileOrientation (int), ProfileScaling (int), SweepType (int), TaperAngle, TwistAngle, GetSectionTwists/SetSectionTwists. Use: compdef.Features.SweepFeatures.CreateSweepDefinition(...) then Add(defn).
- Fusion: sweepFeatures.createDefinition(profile, path, operation, sweepType, profileOrientation, guideRail, guideSurface, taper) → SweepFeatureDefinition; then design.features.sweepFeatures.createFeature(definition)
### add_coil_feature
- params: profile: Profile, axis_entity: Edge/WorkAxis, operation: PartFeatureOperationEnum, pitch_or_revolution: cm/deg, height_or_revolution: cm/deg, axis_direction_reversed: bool=False, clockwise_rotation: bool=False, taper_angle: deg=0.0, flat_start_type: bool=False, start_transition_angle: deg (optional), start_flat_angle: deg (optional), flat_end_type: bool=False, end_transition_angle: deg (optional), end_flat_angle: deg (optional)
- Inventor: CoilFeatures.AddByPitchAndRevolution(Profile, AxisEntity, Pitch, Revolution, Operation, AxisDirectionReversed, ClockwiseRotation, TaperAngle, FlatStartType, StartTransitionAngle, StartFlatAngle, FlatEndType, EndTransitionAngle, EndFlatAngle) or AddByPitchAndHeight(...) or AddByRevolutionAndHeight(...) or AddSpiral(Profile, AxisEntity, Pitch, Revolution, Operation, AxisDirectionReversed, ClockwiseRotation). See gen_py line 21547-21644. No explicit CreateDefinition; methods return CoilFeature {B9036BF2-EBE0-4593-92B6-DBCD421C6BDF} directly. All params are REQUIRED (default for optional bools/angles shown). Use: compdef.Features.CoilFeatures.AddByPitchAndRevolution(profile, axis, pitch, revolutions, kJoin) directly.
- Fusion: coilFeatures.createDefinition(profile, axis, pitchOrRevolution, heightOrRevolution, operation, coilType, taper) → CoilFeatureDefinition; then design.features.coilFeatures.createFeature(definition)
### add_rib_feature
- params: profile_curves: ObjectCollection, is_rib: bool, direction_reversed: bool, thickness: cm, extent_type: RibExtentEnum (kToNextFace or kFiniteDistance), extent_distance: cm (if kFiniteDistance), draft_angle: deg=0.0, draft_profile_ends: bool=False, extend_profile: bool=False, thickness_direction: ThicknessDirectionEnum=kCenteredSymmetrically
- Inventor: RibFeatures.Add(Definition) or CreateDefinition(ProfileCurves, IsRib, DirectionReversed, Thickness) → RibDefinition {5B078EF2-5839-4B6A-97D1-BB8F5D9CFD78}. RibDefinition: ProfileCurves (ObjectCollection), IsRib (bool), DirectionReversed (bool), Thickness, ExtentType (int), ExtentDistance (variant), DraftAngle, DraftProfileEnds, ExtendProfile, ThicknessDirection (int), SetFiniteExtent(Distance), SetToNextExtent(). Properties settable after Create. Then: compdef.Features.RibFeatures.Add(rib_def). See gen_py line 101502-101567.
- Fusion: ribFeatures.createDefinition(sketchCurve, isRib, directionReversed, thickness, extentType, extentDistance) → RibFeatureDefinition; then design.features.ribFeatures.createFeature(definition)
### add_thread_feature
- params: face: Face, start_edge: Edge, thread_info: ThreadInfo {1470BE5E-D0B2-4177-A484-3528D6B0FC37}, direction_reversed: bool=False, full_depth: bool=True, thread_depth: cm (optional), thread_offset: cm (optional)
- Inventor: ThreadFeatures.Add(Face, StartEdge, ThreadInfo, DirectionReversed, FullDepth, ThreadDepth, ThreadOffset) or CreateThreadInfo(Internal, RightHanded, ThreadType, ThreadDesignation, Class='') → ThreadInfo {1470BE5E-D0B2-4177-A484-3528D6B0FC37} or CreateStandardThreadInfo(Internal, RightHanded, ThreadType, ThreadDesignation, Class) → StandardThreadInfo {B2CB30BD-4B68-4D6C-8A07-3122FE52E6B9} or CreateTaperedThreadInfo(Internal, RightHanded, ThreadType, ThreadDesignation) → TaperedThreadInfo {D4D0315D-6874-4E69-9BBB-6E3D28B9122A}. ThreadInfo properties: Internal, Metric, RightHanded, ThreadType, ThreadDesignation, CustomThreadDesignation, FullThreadDepth, ThreadBasePoints (ObjectsEnumerator), ThreadDirection (Vector). See gen_py line 125372-125520.
- Fusion: threadFeatures.createDefinition(threadInfo) → ThreadFeatureDefinition; then design.features.threadFeatures.createFeature(definition)
### add_emboss_feature
- params: profile: Profile, distance: cm or taper: deg, extent_direction: int (1=from face, 2=from plane, 3=symmetric), top_face_color: Color (optional), wrap_face: bool (optional)
- Inventor: EmbossFeatures.AddEmbossFromFace(Profile, Distance, ExtentDirection, TopFaceColor, WrapFace) or AddEngraveFromFace(Profile, Distance, ExtentDirection, TopFaceColor, WrapFace) or AddEmbossEngraveFromPlane(Profile, Taper, ExtentDirection, TopFaceColor). See gen_py line 46028-46104. Returns EmbossFeature {6A0A9BAD-53F2-4254-A34E-9262F980B5CE}. No Definition class; methods are direct-create.
- Fusion: embossFeatures.createDefinition(profile, operation, depth, distance, planarFace) → EmbossFeatureDefinition; then design.features.embossFeatures.createFeature(definition)
### add_decal_feature
- params: image: Image, face: Face, wrap_face: bool=False, chain_faces: bool=True
- Inventor: DecalFeatures.Add(Image, Face, WrapFace, ChainFaces) → DecalFeature {9C693BB0-7C99-4D06-961E-99936273C492}. See gen_py line 33575-33631. No Definition class; direct method creation.
- Fusion: decalFeatures.createDefinition(decalProperties) → DecalFeatureDefinition; then design.features.decalFeatures.createFeature(definition)

**enums:** PartFeatureOperationEnum: kJoin=0, kCut=1, kNewBody=2; LoftSectionEndConditionEnum: kNatural=34305, kVertexTangent=34306, kVertexCurvature=34307, kPlaneTangent=34308, kPlaneCurvature=34309; SweepTypeEnum: kPathAndProfileSweepType, kPathAndGuideRailSweepType, kPathAndGuideSurfaceSweepType, kPathAndSectionTwistSweepType; ProfileOrientationEnum: kProfileNormalToPath=59649, kAlongSketchNormal=59650, kAlongSurfaceNormal=59651; ProfileScalingEnum: kCentroid=59393, kFirstPoint=59394, kLastPoint=59395, kVertexFactor=59396; RibExtentEnum: kToNextFace, kFiniteDistance; ThicknessDirectionEnum: kCenteredSymmetrically, kOneDirection, kTwoDirection

## solid-features-b
### create_face_draft_feature
- params: faces: Face[], draftAngle: float (radians), fixedEdges: Edge[] | fixedPlane: Plane | pullDirection: Vector, directionReversed: bool (default False)
- Inventor: FaceDraftFeatures.Add(FaceDraftDefinition) or _AddFixedEdge(Faces, FixedEdges, DraftAngle, PullDirection, DirectionReversed=False) / _AddFixedPlane(Faces, DraftAngle, FixedPlane, DirectionReversed=False) / _AddTaperShadow(Faces, DraftAngle, PullDirection, DirectionReversed=False). Use CreateFaceDraftDefinition() to build definition object, then Add().
- Fusion: draftFeatures.createFeature(bodies[], draftAngle, pullDirection, fixedEdges/fixedPlane) - check docs.autodesk.com/fusion/API for exact signature
### split_body_by_tool
- params: splitTool: Surface/Body, body: Body
- Inventor: SplitFeatures.SplitBody(SplitTool, Body) -> SplitFeature. Original body consumed, two new bodies created.
- Fusion: splitBodyFeatures.createFeature(toolBody, targetBody) - splits and keeps both result bodies
### split_faces_by_tool
- params: splitTool: Surface/Body, splitAll: bool (default True), facesOrBody: Face[] (optional)
- Inventor: SplitFeatures.SplitFaces(SplitTool, SplitAll=True, FacesOrBody=None) -> SplitFeature. If FacesOrBody omitted, splits all faces.
- Fusion: splitFaceFeatures.createFeature(toolBody, faceSet, splitAll) - preserves original body
### trim_solid_by_tool
- params: splitTool: Surface/Body, body: Body, removePositiveSide: bool (default True)
- Inventor: SplitFeatures.TrimSolid(SplitTool, Body, RemovePositiveSide=True) -> SplitFeature. Specified portion removed.
- Fusion: splitBodyFeatures.createFeature(toolBody, targetBody, keepPositive=False)
### thicken_faces
- params: faces: Face[], distance: float (cm), extentDirection: int (20993=positive, 20994=negative, 20995=symmetric), operation: int (20481=join, 20482=cut, 20483=intersect, 20484=surface, 20485=newbody), automaticFaceChain: bool (default False), createVerticalSurfaces: bool (default False), automaticBlending: bool (default False)
- Inventor: ThickenFeatures.Add(Faces, Distance, ExtentDirection, Operation, AutomaticFaceChain=False, CreateVerticalSurfaces=False, AutomaticBlending=False) -> ThickenFeature. Distance in cm, ExtentDirection from PartFeatureExtentDirectionEnum, Operation from PartFeatureOperationEnum.
- Fusion: thickenFeatures.createFeature(faceSet, thickness, direction, operation) - direction is 'One', 'Symmetric', or 'Both'
### combine_bodies
- params: baseBody: Body, toolBodies: Body[], operation: int (20481=join, 20482=cut, 20483=intersect), keepToolBodies: bool (default False)
- Inventor: CombineFeatures.Add(BaseBody, ToolBodies, Operation, KeepToolBodies=False) -> CombineFeature. Operation from PartFeatureOperationEnum. KeepToolBodies preserves original tool bodies.
- Fusion: combineFeatures.createFeature(baseBody, toolBodies, operation, keepTools=false)
### delete_faces
- params: facesToDelete: Face[], heal: bool (default False)
- Inventor: DeleteFaceFeatures.Add(FacesToDelete, Heal=False) -> DeleteFaceFeature. Heal attempts to patch gaps left by deletion.
- Fusion: removeFeatures.createFeature(faceSet, healEdges=false)
### move_faces
- params: faces: Face[], moveType: int (direction_distance | planar | free), distance: float (cm) | points: Point[] | transform: Matrix, direction: Vector (optional), directionReversed: bool (default False)
- Inventor: MoveFaceFeatures.CreateDefinition(Faces) -> MoveFaceDefinition, then SetDirectionAndDistanceMoveType(Distance, Direction, DirectionReversed=False) or SetPlanarMoveType(PointOne, PointTwo, Plane=None) or SetFreeMoveType(Transformation), then Add(Definition) -> MoveFaceFeature.
- Fusion: moveFeatures.createFeature(faceSet, moveType, distance/points/transform, optional direction)
### add_nonparametric_base_feature
- params: surfaceBody: SurfaceBody, transform: Matrix (optional)
- Inventor: NonParametricBaseFeatures.Add(SurfaceBody, Transform=None) -> NonParametricBaseFeature OR CreateDefinition() -> NonParametricBaseFeatureDefinition, configure, then AddByDefinition(Definition).
- Fusion: baseFeatures.createFeature(surfaceBody, transform=None) - imports static geometry with no parametric links
### bend_part
- params: bendLine: Edge, bendPartType: int (83457=arcLength_angle, 83458=radius_angle, 83459=radius_arcLength), inputOne: float (angle/radius in radians/cm), inputTwo: float (arcLength/angle in radians/cm), bendSide: int (bend direction), bendInSketchNormalDirection: bool, body: Body (optional), bendMinimum: bool (default True)
- Inventor: BendPartFeatures.Add(BendLine, BendPartType, InputOne, InputTwo, BendSide, BendInSketchNormalDirection, Body=None, BendMinimum=True) -> BendPartFeature. BendPartType from BendPartTypeEnum. Requires sketch with bend line.
- Fusion: bendPartFeatures.createFeature(bendLine, bendType, input1, input2, bendSide, sketchNormal, body=None)
### create_boundary_patch
- params: definition: BoundaryPatchDefinition (edges: Edge[], conditions: int[] (63489=free, 63490=tangent, 63491=continuous), tangentWeights: float[])
- Inventor: BoundaryPatchFeatures.CreateBoundaryPatchDefinition() -> BoundaryPatchDefinition, then configure with boundary loops and conditions via CreateBoundaryPatchDefinition(), then Add(Definition) -> BoundaryPatchFeature.
- Fusion: boundaryPatchFeatures.createFeature(boundaryEdges, continuityType) - type: 'Free', 'Tangent', 'Curvature'
### mirror_features
- params: parentFeatures: Feature[], mirrorPlaneEntity: Plane, removeOriginal: bool (default False), computeType: int (47361=identical, 47362=adjustToModel, 47363=optimized)
- Inventor: MirrorFeatures.CreateDefinition(ParentFeatures, MirrorPlaneEntity, ComputeType=47363) -> MirrorFeatureDefinition, then AddByDefinition(Definition) -> MirrorFeature. Or Add(ParentFeatures, MirrorPlaneEntity, RemoveOriginal=False, ComputeType=47363).
- Fusion: mirrorFeatures.createFeature(featureSet, mirrorPlane, removeOriginal=false, computeType='Optimized')
### rectangular_pattern_features
- params: parentFeatures: Feature[], xDirectionEntity: Edge/Plane, naturalXDirection: bool, xCount: int, xSpacing: float (cm), xSpacingType: int (33537=distance), yDirectionEntity: Edge/Plane (optional), naturalYDirection: bool (default True), yCount: int (optional), ySpacing: float (optional), ySpacingType: int (33537), computeType: int (47361/47362/47363)
- Inventor: RectangularPatternFeatures.CreateDefinition(ParentFeatures, XDirectionEntity, NaturalXDirection, XCount, XSpacing, XSpacingType=33537) -> RectangularPatternFeatureDefinition, then Add() or AddByDefinition(). Simplified Add() omits Y direction for single-direction patterns.
- Fusion: rectangularPatternFeatures.createFeature(featureSet, xAxis, xCount, xSpacing, yAxis=None, yCount=1, ySpacing=0, computeType='Optimized')
### circular_pattern_features
- params: parentFeatures: Feature[], axisEntity: Edge/Axis, naturalAxisDirection: bool, count: int, angle: float (radians), fitWithinAngle: bool, computeType: int (47361/47362/47363)
- Inventor: CircularPatternFeatures.CreateDefinition(ParentFeatures, AxisEntity, NaturalAxisDirection, Count, Angle, FitWithinAngle=True) -> CircularPatternFeatureDefinition, then AddByDefinition(Definition) -> CircularPatternFeature.
- Fusion: circularPatternFeatures.createFeature(featureSet, axis, count, angle, fitWithinAngle=true, computeType='Optimized')
### sketch_driven_pattern_features
- params: parentFeatures: Feature[], sketch: Sketch, basePoint: Point (optional), referenceFaces: Face[] (optional)
- Inventor: SketchDrivenPatternFeatures.CreateDefinition(ParentFeatures, Sketch, BasePoint=None, ReferenceFaces=None) -> SketchDrivenPatternDefinition, then Add(Definition) -> SketchDrivenPatternFeature. Sketch points define pattern occurrences.
- Fusion: sketchDrivenPatternFeatures.createFeature(featureSet, sketch, basePoint=null, referenceFaces=null)
### add_derived_part_component
- params: definition: DerivedPartDefinition | DerivedPartTransformDef | DerivedPartCoordinateSystemDef | DerivedPartUniformScaleDef (from CreateDefinition/CreateTransformDef/CreateCoordinateSystemDef/CreateUniformScaleDef with fullDocumentName/fullFileName)
- Inventor: DerivedPartComponents.CreateDefinition(FullDocumentName) -> DerivedPartUniformScaleDef OR CreateTransformDef(FullFileName) -> DerivedPartTransformDef OR CreateCoordinateSystemDef(FullFileName) -> DerivedPartCoordinateSystemDef OR CreateUniformScaleDef(FullFileName) -> DerivedPartUniformScaleDef, configure filters (IncludeAll/ExcludeAll), then Add(Definition) -> DerivedPartComponent.
- Fusion: deriveseparately not directly exposed; use ComponentDefinition.ReferenceComponents for assembly-level derived parts

**enums:** BendPartTypeEnum: kArcLengthAndAngleBendPart=83457, kRadiusAndAngleBendPart=83458, kRadiusAndArcLengthBendPart=83459; PartFeatureOperationEnum: kJoinOperation=20481, kCutOperation=20482, kIntersectOperation=20483, kSurfaceOperation=20484, kNewBodyOperation=20485; PartFeatureExtentDirectionEnum: kPositiveExtentDirection=20993, kNegativeExtentDirection=20994, kSymmetricExtentDirection=20995; BoundaryPatchConditionEnum: kFreeBoundaryPatchCondition=63489, kTangentBoundaryPatchCondition=63490, kContinuousBoundaryPatchCondition=63491; PatternComputeTypeEnum: kIdenticalCompute=47361, kAdjustToModelCompute=47362, kOptimizedCompute=47363

## work-features
### create_work_plane_by_plane_and_offset
- params: plane: Plane, offset: float (cm)
- Inventor: WorkPlanes.AddByPlaneAndOffset(Plane, Offset, Construction=False) -> WorkPlane. Return type WorkPlane. Parameters: Plane (Object, face/plane entity), Offset (Double, cm, signed distance in plane normal direction). Gotcha: Offset is VT_R8 (double), Construction is VT_BOOL (optional, defaults False). Use: compdef.WorkPlanes.AddByPlaneAndOffset(plane_obj, offset_value, False)
- Fusion: constructionPlanes.createInput() returns ConstructionPlaneInput. Call setByOffsetFromPlane(planeInput, offset_cm). Returns ConstructionPlane on add(input). Signature: createInput() -> ConstructionPlaneInput; setByOffsetFromPlane(baseInput: ConstructionPlaneInput, offset: float) -> void
### create_work_plane_by_line_and_point
- params: line: Edge, point: Point
- Inventor: WorkPlanes.AddByLineAndPoint(Line, Point, Construction=False) -> WorkPlane. Parameters: Line (Object, edge/line entity), Point (Object, vertex/point). Return WorkPlane. Gotcha: Both inputs are Object (IDispatch), no validation signature — ensure correct geometry type (line must be edge/line, point must vertex/point). Use: compdef.WorkPlanes.AddByLineAndPoint(line_edge, point_obj, False)
- Fusion: constructionPlanes.createInput() -> ConstructionPlaneInput; call setByLineAndPoint(baseInput: ConstructionPlaneInput, line: Edge, point: Point) -> void; add(input) -> ConstructionPlane
### create_work_plane_by_line_plane_and_angle
- params: line: Edge, plane: Plane, angle: float (radians)
- Inventor: WorkPlanes.AddByLinePlaneAndAngle(Line, Plane, Angle, Construction=False) -> WorkPlane. Parameters: Line (Object), Plane (Object), Angle (Double, VT_R8 in radians). Return WorkPlane. Gotcha: Angle is in radians, not degrees. Use: compdef.WorkPlanes.AddByLinePlaneAndAngle(line_obj, plane_obj, angle_rad, False)
- Fusion: constructionPlanes.createInput() -> ConstructionPlaneInput; call setByLinePlaneAndAngle(baseInput: ConstructionPlaneInput, line: Edge, plane: Plane, angle: float) -> void; Angle in radians. add(input) -> ConstructionPlane
### create_work_plane_by_normal_to_curve
- params: curve: Edge, point: Point
- Inventor: WorkPlanes.AddByNormalToCurve(CurveEntity, Point, Construction=False) -> WorkPlane. Parameters: CurveEntity (Object, edge/curve), Point (Object). Return WorkPlane. Use: compdef.WorkPlanes.AddByNormalToCurve(curve_edge, point_obj, False)
- Fusion: constructionPlanes.createInput() -> ConstructionPlaneInput; call setByNormalToCurve(baseInput, curveEntity: Edge, point: Point) -> void; add(input) -> ConstructionPlane
### create_work_plane_by_plane_and_point
- params: plane: Plane, point: Point
- Inventor: WorkPlanes.AddByPlaneAndPoint(Plane, Point, Construction=False) -> WorkPlane. Parameters: Plane (Object), Point (Object). Return WorkPlane. Use: compdef.WorkPlanes.AddByPlaneAndPoint(plane_obj, point_obj, False)
- Fusion: constructionPlanes.createInput() -> ConstructionPlaneInput; call setByPlaneAndPoint(baseInput, plane: Plane, point: Point) -> void; add(input) -> ConstructionPlane
### create_work_plane_by_plane_and_tangent
- params: plane: Plane, face: Face, proximity_point: Point
- Inventor: WorkPlanes.AddByPlaneAndTangent(Plane, Face, ProximityPoint, Construction=False) -> WorkPlane. Parameters: Plane (Object), Face (Object, surface), ProximityPoint (Object, Point, used to select tangency solution). Return WorkPlane. Gotcha: ProximityPoint disambiguates multiple tangent solutions. Use: compdef.WorkPlanes.AddByPlaneAndTangent(plane_obj, face_obj, prox_point, False)
- Fusion: constructionPlanes.createInput() -> ConstructionPlaneInput; call setByPlaneAndTangent(baseInput, plane: Plane, face: Face, proximityPoint: Point) -> void; add(input) -> ConstructionPlane
### create_work_plane_by_point_and_tangent
- params: point: Point, face: Face
- Inventor: WorkPlanes.AddByPointAndTangent(Point, Face, Construction=False) -> WorkPlane. Parameters: Point (Object), Face (Object). Return WorkPlane. Use: compdef.WorkPlanes.AddByPointAndTangent(point_obj, face_obj, False)
- Fusion: constructionPlanes.createInput() -> ConstructionPlaneInput; call setByPointAndTangent(baseInput, point: Point, face: Face) -> void; add(input) -> ConstructionPlane
### create_work_plane_by_three_points
- params: point1: Point, point2: Point, point3: Point
- Inventor: WorkPlanes.AddByThreePoints(Point1, Point2, Point3, Construction=False) -> WorkPlane. Parameters: Point1, Point2, Point3 (Object). Return WorkPlane. Use: compdef.WorkPlanes.AddByThreePoints(p1, p2, p3, False)
- Fusion: constructionPlanes.createInput() -> ConstructionPlaneInput; call setByThreePoints(baseInput, point1: Point, point2: Point, point3: Point) -> void; add(input) -> ConstructionPlane
### create_work_plane_by_torus_mid_plane
- params: face: Face (torus face)
- Inventor: WorkPlanes.AddByTorusMidPlane(Face, Construction=False) -> WorkPlane. Parameters: Face (Object, must be torus surface). Return WorkPlane. Gotcha: Face must be a torus or will fail. Use: compdef.WorkPlanes.AddByTorusMidPlane(torus_face, False)
- Fusion: constructionPlanes.createInput() -> ConstructionPlaneInput; call setByTorusMidPlane(baseInput, face: Face) -> void; add(input) -> ConstructionPlane
### create_work_plane_by_two_lines
- params: line1: Edge, line2: Edge
- Inventor: WorkPlanes.AddByTwoLines(Line1, Line2, Construction=False) -> WorkPlane. Parameters: Line1, Line2 (Object, edges/lines). Return WorkPlane. Use: compdef.WorkPlanes.AddByTwoLines(line1_obj, line2_obj, False)
- Fusion: constructionPlanes.createInput() -> ConstructionPlaneInput; call setByTwoLines(baseInput, line1: Edge, line2: Edge) -> void; add(input) -> ConstructionPlane
### create_work_plane_by_two_planes
- params: plane1: Plane, plane2: Plane, quadrant_point: Point
- Inventor: WorkPlanes.AddByTwoPlanes(Plane1, Plane2, QuadrantPoint, Construction=False) -> WorkPlane. Parameters: Plane1, Plane2 (Object), QuadrantPoint (Object, Variant 12=VT_VARIANT for out-param, optional). Return WorkPlane. Gotcha: QuadrantPoint is (12, 17) = Variant ByRef optional, used to select which of 4 bisector planes. Use: compdef.WorkPlanes.AddByTwoPlanes(p1, p2, quad_pt, False)
- Fusion: constructionPlanes.createInput() -> ConstructionPlaneInput; call setByTwoPlanes(baseInput, plane1: Plane, plane2: Plane, quadrantPoint: Point=None) -> void; add(input) -> ConstructionPlane
### create_work_plane_fixed
- params: origin_point: Point, x_axis_point: Point, y_axis_point: Point
- Inventor: WorkPlanes.AddFixed(OriginPoint, XAxis, YAxis, Construction=False) -> WorkPlane. Parameters: OriginPoint, XAxis, YAxis (Object, all Points). Return WorkPlane. Use: compdef.WorkPlanes.AddFixed(origin, x_pt, y_pt, False)
- Fusion: constructionPlanes.createInput() -> ConstructionPlaneInput; call setByFixed(baseInput, origin: Point, xAxisPoint: Point, yAxisPoint: Point) -> void; add(input) -> ConstructionPlane
### create_work_axis_by_line
- params: line: Edge
- Inventor: WorkAxes.AddByLine(Line, Construction=False) -> WorkAxis. Parameters: Line (Object, edge/line). Return WorkAxis. Use: compdef.WorkAxes.AddByLine(line_obj, False)
- Fusion: constructionAxes.createInput() -> ConstructionAxisInput; call setByLine(baseInput, line: Edge) -> void; add(input) -> ConstructionAxis
### create_work_axis_by_two_points
- params: point1: Point, point2: Point
- Inventor: WorkAxes.AddByTwoPoints(Point1, Point2, Construction=False) -> WorkAxis. Parameters: Point1, Point2 (Object). Return WorkAxis. Use: compdef.WorkAxes.AddByTwoPoints(p1, p2, False)
- Fusion: constructionAxes.createInput() -> ConstructionAxisInput; call setByTwoPoints(baseInput, point1: Point, point2: Point) -> void; add(input) -> ConstructionAxis
### create_work_axis_by_line_and_plane
- params: line: Edge, plane: Plane
- Inventor: WorkAxes.AddByLineAndPlane(Line, Plane, Construction=False) -> WorkAxis. Parameters: Line (Object), Plane (Object). Return WorkAxis. Gotcha: Projects line orthogonally onto plane. Use: compdef.WorkAxes.AddByLineAndPlane(line_obj, plane_obj, False)
- Fusion: constructionAxes.createInput() -> ConstructionAxisInput; call setByLineAndPlane(baseInput, line: Edge, plane: Plane) -> void; add(input) -> ConstructionAxis
### create_work_axis_by_point_and_plane
- params: point: Point, plane: Plane
- Inventor: WorkAxes.AddByPointAndPlane(Point, Plane, Construction=False) -> WorkAxis. Parameters: Point (Object), Plane (Object). Return WorkAxis. Use: compdef.WorkAxes.AddByPointAndPlane(point_obj, plane_obj, False)
- Fusion: constructionAxes.createInput() -> ConstructionAxisInput; call setByPointAndPlane(baseInput, point: Point, plane: Plane) -> void; add(input) -> ConstructionAxis
### create_work_axis_by_normal_to_surface
- params: surface: Face, point: Point
- Inventor: WorkAxes.AddByNormalToSurface(Surface, Point, Construction=False) -> WorkAxis. Parameters: Surface (Object, face), Point (Object). Return WorkAxis. Use: compdef.WorkAxes.AddByNormalToSurface(face_obj, point_obj, False)
- Fusion: constructionAxes.createInput() -> ConstructionAxisInput; call setByNormalToSurface(baseInput, surface: Face, point: Point) -> void; add(input) -> ConstructionAxis
### create_work_axis_by_revolved_face
- params: face: Face (revolved surface)
- Inventor: WorkAxes.AddByRevolvedFace(Face, Construction=False) -> WorkAxis. Parameters: Face (Object, must be revolved surface). Return WorkAxis. Gotcha: Face must be from revolve feature. Use: compdef.WorkAxes.AddByRevolvedFace(revolved_face, False)
- Fusion: constructionAxes.createInput() -> ConstructionAxisInput; call setByRevolvedFace(baseInput, face: Face) -> void; add(input) -> ConstructionAxis
### create_work_axis_by_two_planes
- params: plane1: Plane, plane2: Plane
- Inventor: WorkAxes.AddByTwoPlanes(Plane1, Plane2, Construction=False) -> WorkAxis. Parameters: Plane1, Plane2 (Object). Return WorkAxis. Use: compdef.WorkAxes.AddByTwoPlanes(plane1_obj, plane2_obj, False)
- Fusion: constructionAxes.createInput() -> ConstructionAxisInput; call setByTwoPlanes(baseInput, plane1: Plane, plane2: Plane) -> void; add(input) -> ConstructionAxis
### create_work_axis_by_analytic_edge
- params: edge: Edge (analytic curve)
- Inventor: WorkAxes.AddByAnalyticEdge(Edge, Construction=False) -> WorkAxis. Parameters: Edge (Object, must be analytic edge like circle). Return WorkAxis. Gotcha: Only works with analytic curves (circle, ellipse, etc.), not splines. Use: compdef.WorkAxes.AddByAnalyticEdge(edge_obj, False)
- Fusion: constructionAxes.createInput() -> ConstructionAxisInput; call setByAnalyticEdge(baseInput, edge: Edge) -> void; add(input) -> ConstructionAxis
### create_work_axis_fixed
- params: point: Point, axis: Vector (direction)
- Inventor: WorkAxes.AddFixed(Point, Axis, Construction=False) -> WorkAxis. Parameters: Point (Object), Axis (Object, Vector). Return WorkAxis. Gotcha: Axis must be Vector object (from TransientGeometry), not Point. Use: compdef.WorkAxes.AddFixed(point_obj, vector_obj, False)
- Fusion: constructionAxes.createInput() -> ConstructionAxisInput; call setByFixed(baseInput, point: Point, direction: Vector) -> void; add(input) -> ConstructionAxis
### create_work_point_by_point
- params: point: Point
- Inventor: WorkPoints.AddByPoint(Point, Construction=False) -> WorkPoint. Parameters: Point (Object). Return WorkPoint. Use: compdef.WorkPoints.AddByPoint(point_obj, False)
- Fusion: constructionPoints.createInput() -> ConstructionPointInput; call setByPoint(baseInput, point: Point) -> void; add(input) -> ConstructionPoint
### create_work_point_by_three_planes
- params: plane1: Plane, plane2: Plane, plane3: Plane
- Inventor: WorkPoints.AddByThreePlanes(Plane1, Plane2, Plane3, Construction=False) -> WorkPoint. Parameters: Plane1, Plane2, Plane3 (Object). Return WorkPoint. Use: compdef.WorkPoints.AddByThreePlanes(p1, p2, p3, False)
- Fusion: constructionPoints.createInput() -> ConstructionPointInput; call setByThreePlanes(baseInput, plane1: Plane, plane2: Plane, plane3: Plane) -> void; add(input) -> ConstructionPoint
### create_work_point_by_curve_and_entity
- params: curve: Edge, entity: Face, proximity_point: Point (optional)
- Inventor: WorkPoints.AddByCurveAndEntity(Curve, Entity, ProximityPoint, Construction=False) -> WorkPoint. Parameters: Curve (Object, edge), Entity (Object, face/plane), ProximityPoint (Object, Variant 12,17=optional). Return WorkPoint. Gotcha: ProximityPoint disambiguates multiple intersections, passed as Variant ByRef optional. Use: compdef.WorkPoints.AddByCurveAndEntity(curve_obj, entity_obj, prox_pt, False)
- Fusion: constructionPoints.createInput() -> ConstructionPointInput; call setByCurveAndEntity(baseInput, curve: Edge, entity: Face, proximityPoint: Point=None) -> void; add(input) -> ConstructionPoint
### create_work_point_at_centroid
- params: entities: Edge|EdgeLoop|EdgeCollection
- Inventor: WorkPoints.AddAtCentroid(Entities, Construction=False) -> WorkPoint. Parameters: Entities (Object, Edge/EdgeLoop/EdgeCollection). Return WorkPoint. Use: compdef.WorkPoints.AddAtCentroid(entity_obj, False)
- Fusion: constructionPoints.createInput() -> ConstructionPointInput; call setAtCentroid(baseInput, entities: Edge|EdgeCollection) -> void; add(input) -> ConstructionPoint
### create_work_point_by_mid_point
- params: edge: Edge
- Inventor: WorkPoints.AddByMidPoint(Edge, Construction=False) -> WorkPoint. Parameters: Edge (Object). Return WorkPoint. Use: compdef.WorkPoints.AddByMidPoint(edge_obj, False)
- Fusion: constructionPoints.createInput() -> ConstructionPointInput; call setByMidPoint(baseInput, edge: Edge) -> void; add(input) -> ConstructionPoint
### create_work_point_by_two_lines
- params: line1: Edge, line2: Edge
- Inventor: WorkPoints.AddByTwoLines(Line1, Line2, Construction=False) -> WorkPoint. Parameters: Line1, Line2 (Object, edges/lines). Return WorkPoint. Use: compdef.WorkPoints.AddByTwoLines(line1_obj, line2_obj, False)
- Fusion: constructionPoints.createInput() -> ConstructionPointInput; call setByTwoLines(baseInput, line1: Edge, line2: Edge) -> void; add(input) -> ConstructionPoint
### create_work_point_by_sphere_center
- params: face: Face (sphere surface)
- Inventor: WorkPoints.AddBySphereCenterPoint(Face, Construction=False) -> WorkPoint. Parameters: Face (Object, must be sphere). Return WorkPoint. Gotcha: Face must be spherical surface. Use: compdef.WorkPoints.AddBySphereCenterPoint(sphere_face, False)
- Fusion: constructionPoints.createInput() -> ConstructionPointInput; call setBySphereCenterPoint(baseInput, face: Face) -> void; add(input) -> ConstructionPoint
### create_work_point_by_torus_center
- params: face: Face (torus surface)
- Inventor: WorkPoints.AddByTorusCenterPoint(Face, Construction=False) -> WorkPoint. Parameters: Face (Object, must be torus). Return WorkPoint. Gotcha: Face must be toroidal surface. Use: compdef.WorkPoints.AddByTorusCenterPoint(torus_face, False)
- Fusion: constructionPoints.createInput() -> ConstructionPointInput; call setByTorusCenterPoint(baseInput, face: Face) -> void; add(input) -> ConstructionPoint
### create_work_point_fixed
- params: point: Point
- Inventor: WorkPoints.AddFixed(Point, Construction=False) -> WorkPoint. Parameters: Point (Object). Return WorkPoint. Use: compdef.WorkPoints.AddFixed(point_obj, False)
- Fusion: constructionPoints.createInput() -> ConstructionPointInput; call setByPoint(baseInput, point: Point) -> void; add(input) -> ConstructionPoint
### create_user_coordinate_system
- params: origin: Point, x_direction_point: Point, y_direction_point: Point
- Inventor: UserCoordinateSystems.CreateDefinition() -> UserCoordinateSystemDefinition; definition.SetByThreePoints(Origin, XDirectionPoint, YDirectionPoint); UserCoordinateSystems.Add(definition) -> UserCoordinateSystem. Parameters: Origin, XDirectionPoint, YDirectionPoint (Object, Points). Return UserCoordinateSystem. Gotcha: Must use CreateDefinition + SetByThreePoints + Add pattern, not direct Add. Use: defn = compdef.UserCoordinateSystems.CreateDefinition(); defn.SetByThreePoints(origin_pt, x_pt, y_pt); ucs = compdef.UserCoordinateSystems.Add(defn)
- Fusion: userCoordinateSystems.createInput() -> UserCoordinateSystemInput; call setByThreePoints(baseInput, origin: Point, xDirectionPoint: Point, yDirectionPoint: Point) -> void; add(input) -> UserCoordinateSystem
### set_work_plane_by_plane_and_offset
- params: work_plane: WorkPlane, plane: Plane, offset: float (cm)
- Inventor: WorkPlane.SetByPlaneAndOffset(Plane, Offset) -> void. Parameters: Plane (Object), Offset (Double, cm). No return. Gotcha: Modifies plane in-place. Use: workplane_obj.SetByPlaneAndOffset(plane_obj, offset_value)
- Fusion: Not directly available as Set method on ConstructionPlane; use setByOffsetFromPlane(plane: Plane, offset: float) via edit pattern or recreate plane
### set_work_plane_by_line_and_point
- params: work_plane: WorkPlane, line: Edge, point: Point
- Inventor: WorkPlane.SetByLineAndPoint(Line, Point) -> void (not directly in sig, inferred from pattern). Available Set methods: SetByPlaneAndPoint, SetByThreePoints, SetByTwoLines, SetByTwoPlanes, SetFixed. No SetByLineAndPoint on WorkPlane object — use creation pattern instead.
- Fusion: Not available; must delete and recreate
### set_work_axis_by_line
- params: work_axis: WorkAxis, line: Edge
- Inventor: WorkAxis.SetByLine(Line) -> void. Parameters: Line (Object, edge). No return. Use: workaxis_obj.SetByLine(line_obj)
- Fusion: Not available as separate Set; must use edit or recreate
### set_work_point_by_point
- params: work_point: WorkPoint, point: Point
- Inventor: WorkPoint.SetByPoint(Point) -> void. Parameters: Point (Object). No return. Use: workpoint_obj.SetByPoint(new_point_obj)
- Fusion: setByPoint(point: Point) -> void on ConstructionPoint via edit pattern
### get_work_plane_position
- params: work_plane: WorkPlane
- Inventor: WorkPlane.GetPosition(Origin, XAxis, YAxis) -> void. Parameters: Origin, XAxis, YAxis (out-params, Variant 16393=VT_VECTOR|VT_BYREF). Returns by reference. Gotcha: Out-params must be passed as pythoncom.Missing or mutable container; result unpacked from return tuple. Use: origin, xaxis, yaxis = workplane_obj.GetPosition(pythoncom.Missing, pythoncom.Missing, pythoncom.Missing)
- Fusion: ConstructionPlane.geometry.origin, .xAxis, .yAxis properties; or getOrigin(), getXAxis(), getYAxis() methods
### get_work_plane_size
- params: work_plane: WorkPlane
- Inventor: WorkPlane.GetSize(Point1, Point2) -> void. Parameters: Point1, Point2 (out-params, Variant 16393=VT_VECTOR|VT_BYREF). Gotcha: Out-params via reference. Use: p1, p2 = workplane_obj.GetSize(pythoncom.Missing, pythoncom.Missing)
- Fusion: Not directly available; use plane bounds or geometry bounds
### delete_work_feature
- params: work_feature: WorkPlane|WorkAxis|WorkPoint, retain_dependents: bool
- Inventor: WorkPlane.Delete(RetainDependents=False) / WorkAxis.Delete(RetainDependents=False) / WorkPoint.Delete(RetainDependents=False) -> void. Parameters: RetainDependents (VT_BOOL, optional, defaults False). Gotcha: If False, deletion may fail if features depend on it. Use: workfeature_obj.Delete(True) to keep dependents
- Fusion: ConstructionPlane/Axis/Point.deleteMe() or Timeline delete; no direct retain option

**enums:** Construction=bool (0=false=Reference, 1=true=Construction geometry type in Inventor); RetainDependents=bool (0=fail if dependents exist, 1=keep dependents alive); DefinitionType=int (Inventor enum for UCS definition method, read-only); HealthStatus=int (Inventor feature health code, 0=Healthy, 1=Warning, 2=Error)

## assembly
### add_component_occurrence
- params: occurrence_file_path: str, position_matrix: Matrix (4x4 transformation matrix, cm units)
- Inventor: ComponentOccurrences.Add(FullDocumentName: str, Position: Matrix) -> ComponentOccurrence. Param (8,1)=str, (9,1)=Matrix. Returns 9,0. GOTCHA: Position is required and must be a valid Matrix object from transient geometry; if you only have a file path, call tg.CreateMatrix() with identity or use Part.Definition.ReferenceComponent.Transformation as starting point.
- Fusion: occurrences.addByInsert(fullPath: str, transform: adsk.core.Matrix3D) -> adsk.fusion.Occurrence; units cm; no separate occurrence factory.
### add_component_by_definition
- params: comp_definition: ComponentDefinition, position_matrix: Matrix
- Inventor: ComponentOccurrences.AddByComponentDefinition(CompDef: ComponentDefinition, Position: Matrix) -> ComponentOccurrence. Params (9,1)=(9,1). Used when part is already open in memory, avoids file I/O.
- Fusion: occurrences.addByInsert(fullPath, transform, skeletonOccurrence) with ComponentDefinition proxy passed as occurrence context.
### add_virtual_component
- params: component_name: str, position_matrix: Matrix
- Inventor: ComponentOccurrences.AddVirtual(Name: str, Position: Matrix) -> ComponentOccurrence. Params (8,1)=name, (9,1)=Position matrix. Creates internal VirtualComponent and adds occurrence.
- Fusion: Fusion does not expose virtual components; use a minimal placeholder part instead or API is n/a.
### set_occurrence_grounded
- params: occurrence: ComponentOccurrence, grounded: bool
- Inventor: ComponentOccurrence.Grounded (property, get/set). (11,0) bool. Set to True to ground, False to unground. Grounded components ignore constraints.
- Fusion: rigidGroups.add([occurrence]) to lock; no direct Grounded property; achieved via RigidGroup membership.
### add_mate_constraint
- params: entity_one: Entity, entity_two: Entity, offset: double (cm), entity_one_inferred_type: int = 24833, entity_two_inferred_type: int = 24833, bias_point_one: Point (opt), bias_point_two: Point (opt)
- Inventor: AssemblyConstraints.AddMateConstraint(EntityOne: Entity, EntityTwo: Entity, Offset: double, EntityOneInferredType: int=24833, EntityTwoInferredType: int=24833, BiasPointOne: Point=None, BiasPointTwo: Point=None) -> MateConstraint. Params (9,1), (9,1), (12,1), (3,49)=InferredType, (3,49), (12,17)=opt, (12,17)=opt. InferredType=24833=default auto-inference. Returns (9,0). GOTCHA: Requires geometry entities as Face/Edge/Vertex proxies scoped in assembly context; use occurrence.CreateGeometryProxy() if needed.
- Fusion: joints.add(jointInput) or constraints.addMateConstraint(entity1, entity2, offset) via adsk.fusion.MateMateConstraint.
### add_mate_constraint_with_solution
- params: entity_one: Entity, entity_two: Entity, offset: double, entity_one_inferred_type: int = 24833, entity_two_inferred_type: int = 24833, solution_type: int, bias_point_one: Point (opt), bias_point_two: Point (opt)
- Inventor: AssemblyConstraints.AddMateConstraint2(EntityOne, EntityTwo, Offset, EntityOneInferredType=24833, EntityTwoInferredType=24833, SolutionType=115457, BiasPointOne=None, BiasPointTwo=None) -> MateConstraint. Params (9,1), (9,1), (12,1), (3,49), (3,49), (3,49)=SolutionType. SolutionType: 115457=kOpposedSolutionType (default), 115458=kAlignedSolutionType, 115459=kUndirectedSolutionType, 115460=kNoSolutionType. GOTCHA: SolutionType controls mate direction resolution; use Opposed for faces pointing away, Aligned for same direction.
- Fusion: addMateConstraint(e1, e2, offset, solutionType: kAlignedSolution | kOpposedSolution | kUndirectedSolution).
### add_flush_constraint
- params: entity_one: Entity, entity_two: Entity, offset: double (cm), bias_point_one: Point (opt), bias_point_two: Point (opt)
- Inventor: AssemblyConstraints.AddFlushConstraint(EntityOne, EntityTwo, Offset, BiasPointOne=None, BiasPointTwo=None) -> FlushConstraint. Params (9,1), (9,1), (12,1), (12,17)=opt, (12,17)=opt. Offset in cm (0 = touching, positive = gap).
- Fusion: constraints.addFlushConstraint(entity1, entity2, offset).
### add_angle_constraint
- params: entity_one: Entity, entity_two: Entity, angle: double (radians), solution_type: int = 78593, reference_vector_entity: Entity (opt), bias_point_one: Point (opt), bias_point_two: Point (opt)
- Inventor: AssemblyConstraints.AddAngleConstraint(EntityOne, EntityTwo, Angle, SolutionType=78593, ReferenceVectorEntity=None, BiasPointOne=None, BiasPointTwo=None) -> AngleConstraint. Params (9,1), (9,1), (12,1), (3,49)=SolutionType, (12,17)=opt Entity, (12,17)=opt, (12,17)=opt. Angle in radians. SolutionType: 78593=kDirectedSolution, 78594=kUndirectedSolution, 78595=kReferenceVectorSolution. ReferenceVectorEntity for ambiguous angle cases (requires third entity for direction). GOTCHA: Angle sign/direction depends on SolutionType and entity normal orientation.
- Fusion: constraints.addAngleConstraint(entity1, entity2, angle, solutionType).
### add_tangent_constraint
- params: entity_one: Entity, entity_two: Entity, inside_tangency: bool, offset: double (cm), bias_point_one: Point (opt), bias_point_two: Point (opt)
- Inventor: AssemblyConstraints.AddTangentConstraint(EntityOne, EntityTwo, InsideTangency, Offset, BiasPointOne=None, BiasPointTwo=None) -> TangentConstraint. Params (9,1), (9,1), (11,1)=bool, (12,1), (12,17)=opt, (12,17)=opt. InsideTangency=True for inner tangency (cylinder inside hole), False for outer.
- Fusion: constraints.addTangentConstraint(entity1, entity2, insideTangency, offset).
### add_insert_constraint
- params: entity_one: Entity, entity_two: Entity, axes_opposed: bool, distance: double (cm), bias_point_one: Point (opt), bias_point_two: Point (opt)
- Inventor: AssemblyConstraints.AddInsertConstraint(EntityOne, EntityTwo, AxesOpposed, Distance, BiasPointOne=None, BiasPointTwo=None) -> InsertConstraint. Params (9,1), (9,1), (11,1)=bool AxesOpposed, (12,1), (12,17)=opt, (12,17)=opt. AxesOpposed=True if cylinder axes point in opposite directions. Distance along axis in cm. GOTCHA: Requires cylinder and planar geometry (e.g., hole edge + hole face).
- Fusion: constraints.addInsertConstraint(entity1, entity2, axesOpposed, distance).
### add_insert_constraint_lock_rotation
- params: entity_one: Entity, entity_two: Entity, axes_opposed: bool, distance: double (cm), lock_rotation: bool, bias_point_one: Point (opt), bias_point_two: Point (opt)
- Inventor: AssemblyConstraints.AddInsertConstraint2(EntityOne, EntityTwo, AxesOpposed, Distance, LockRotation=None, BiasPointOne=None, BiasPointTwo=None) -> InsertConstraint. Params (9,1), (9,1), (11,1), (12,1), (12,17)=LockRotation opt, (12,17)=opt, (12,17)=opt. LockRotation=True locks rotation around axis (bolt-in-hole), False allows rotation. GOTCHA: When LockRotation=True, additional constraints suppress rotational DOF around the axis.
- Fusion: addInsertConstraint2 or combination of AddInsertConstraint + rotation lock constraint.
### add_symmetry_constraint
- params: entity_one: Entity, entity_two: Entity, symmetry_plane: Entity (plane), entity_one_inferred_type: int = 24833, entity_two_inferred_type: int = 24833, normals_opposed: bool = True
- Inventor: AssemblyConstraints.AddSymmetryConstraint(EntityOne, EntityTwo, SymmetryPlane, EntityOneInferredType=24833, EntityTwoInferredType=24833, NormalsOpposed=True) -> AssemblySymmetryConstraint. Params (9,1), (9,1), (9,1)=plane, (3,49), (3,49), (11,49). NormalsOpposed: True if entity normals point in opposite directions (default for reflection), False if same. GOTCHA: SymmetryPlane must be a planar face/entity; EntityOne and EntityTwo are the symmetry pair.
- Fusion: constraints.addSymmetryConstraint(entity1, entity2, symmetryPlane, normalsOpposed).
### add_rotate_rotate_constraint
- params: entity_one: Entity (first axis), entity_two: Entity (second axis), ratio: double, forward_direction: bool, bias_point_one: Point (opt), bias_point_two: Point (opt)
- Inventor: AssemblyConstraints.AddRotateRotateConstraint(EntityOne, EntityTwo, Ratio, ForwardDirection, BiasPointOne=None, BiasPointTwo=None) -> RotateRotateConstraint. Params (9,1), (9,1), (12,1)=ratio, (11,1)=bool, (12,17)=opt, (12,17)=opt. Ratio: rotation of EntityTwo = Ratio × rotation of EntityOne. ForwardDirection=True uses natural axis direction, False reverses. Entities are typically cylinder axes (e.g., gears).
- Fusion: constraints.addRotateRotateConstraint(entity1, entity2, ratio, forwardDirection).
### add_rotate_translate_constraint
- params: entity_one: Entity (rotating axis), entity_two: Entity (translating axis), ratio: double (mm/revolution), forward_direction: bool, bias_point_one: Point (opt), bias_point_two: Point (opt)
- Inventor: AssemblyConstraints.AddRotateTranslateConstraint(EntityOne, EntityTwo, Ratio, ForwardDirection, BiasPointOne=None, BiasPointTwo=None) -> RotateTranslateConstraint. Params (9,1), (9,1), (12,1)=ratio, (11,1)=bool, (12,17)=opt, (12,17)=opt. Ratio: linear distance = Ratio × rotations (in user units, typically cm/radian or mm/revolution—check active document unit). ForwardDirection controls sign.
- Fusion: constraints.addRotateTranslateConstraint(entity1, entity2, ratio, forwardDirection).
### add_transitional_constraint
- params: face_one: Face, face_two: Face, bias_point_one: Point (opt), bias_point_two: Point (opt)
- Inventor: AssemblyConstraints.AddTransitionalConstraint(FaceOne, FaceTwo, BiasPointOne=None, BiasPointTwo=None) -> TransitionalConstraint. Params (9,1)=Face, (9,1)=Face, (12,17)=opt Point, (12,17)=opt Point. FaceOne and FaceTwo must be adjacent faces (share an edge). Ensures smooth C1 continuity across edge.
- Fusion: constraints.addTransitionalConstraint(face1, face2).
### create_assembly_joint_definition
- params: joint_type: int (kRigidJointType=102401, kRotationalJointType=102402, kSlideJointType=102403, kCylindricalJointType=102404, kPlanarJointType=102405, kBallJointType=102406), origin_one: GeometryIntent, origin_two: GeometryIntent
- Inventor: AssemblyJoints.CreateAssemblyJointDefinition(JointType: int, OriginOne: GeometryIntent, OriginTwo: GeometryIntent) -> AssemblyJointDefinition. Params (3,1)=JointType enum, (9,1)=GeometryIntent, (9,1)=GeometryIntent. Returned def is modified via SetOriginOneAs* / SetOriginTwoAs* methods, then passed to Joints.Add(). GOTCHA: JointType is immutable after creation; OriginOne/Two define local frames for joint axes (created via CreateGeometryIntent on faces/edges/axes).
- Fusion: jointDefinition = joints.createJointDefinition(occOne, occTwo, jointGeometry); jointInput.jointType = adsk.fusion.JointTypes.RigidJointType; etc.
### add_assembly_joint
- params: joint_definition: AssemblyJointDefinition
- Inventor: AssemblyJoints.Add(AssemblyJointDef: AssemblyJointDefinition) -> AssemblyJoint. Params (9,1). Adds configured joint to Joints collection and returns active joint object. GOTCHA: Joint must be fully configured (origins set, position/limits defined) before Add(); Add() triggers constraint solve.
- Fusion: joints.add(jointInput); returns adsk.fusion.Joint.
### set_joint_origin_infer
- params: joint_definition: AssemblyJointDefinition, origin_index: int (1 or 2)
- Inventor: AssemblyJointDefinition.SetOriginOneAsInfer() or SetOriginTwoAsInfer() (no params). Call one of these methods on the definition before Add(). Infers origin from occurrence geometry (e.g., center of a cylindrical face).
- Fusion: jointGeometry = adsk.fusion.JointGeometry.createByPlanarFace(face, ...); auto-infers axis direction.
### set_joint_origin_offset
- params: joint_definition: AssemblyJointDefinition, origin_index: int (1 or 2), x_offset: double (cm), y_offset: double (cm)
- Inventor: AssemblyJointDefinition.SetOriginOneAsOffset(XOffset: double, YOffset: double) or SetOriginTwoAsOffset(XOffset, YOffset). Params (12,1), (12,1). Offsets in user units (cm).
- Fusion: jointGeometry with offset applied via origin point parameter.
### set_joint_origin_between_faces
- params: joint_definition: AssemblyJointDefinition, origin_index: int (1 or 2), referenced_faces: FaceCollection
- Inventor: AssemblyJointDefinition.SetOriginOneAsBetweenTwoFaces(ReferencedFaces: FaceCollection) or SetOriginTwoAsBetweenTwoFaces(ReferencedFaces). Params (9,1)=collection. ReferencedFaces collected via FindUsingPoint or similar geometry queries.
- Fusion: n/a; Fusion computes joint origins via face normal and geometry intent.
### set_joint_linear_position
- params: joint_definition: AssemblyJointDefinition, position: double (cm), start_limit: double (cm, opt), end_limit: double (cm, opt)
- Inventor: AssemblyJointDefinition.LinearPosition (property, set). Params (12,0)=position value. Also: LinearPositionStartLimit, LinearPositionEndLimit, HasLinearPositionStartLimit, HasLinearPositionEndLimit (bool). Units in cm.
- Fusion: jointDefinition.linearDriveParameter.value = distance (adsk.fusion.DoubleParameter).
### set_joint_angular_position
- params: joint_definition: AssemblyJointDefinition, angle: double (radians), start_limit: double (radians, opt), end_limit: double (radians, opt)
- Inventor: AssemblyJointDefinition.AngularPosition (property, set). Params (12,0)=angle in radians. Also: AngularPositionStartLimit, AngularPositionEndLimit, HasAngularPositionLimits (bool).
- Fusion: jointDefinition.angularDriveParameter.value = angle (radians, adsk.fusion.DoubleParameter).
### set_joint_gap
- params: joint_definition: AssemblyJointDefinition, gap: double (cm)
- Inventor: AssemblyJointDefinition.Gap (property, set). Params (12,0). Gap in cm (negative = penetration). Common for sliding joints to set initial separation.
- Fusion: jointDefinition.offset.value for some joint types.
### add_rectangular_occurrence_pattern
- params: parent_components: ObjectCollection, column_entity: Entity (axis), column_natural_direction: bool, column_offset: double (cm), column_count: int, row_entity: Entity (axis), row_natural_direction: bool = True, row_offset: double (cm, opt), row_count: int (opt)
- Inventor: OccurrencePatterns.AddRectangularPattern(ParentComponents: ObjectCollection, ColumnEntity, ColumnEntityNaturalDirection: bool, ColumnOffset: double, ColumnCount: int, RowEntity, RowEntityNaturalDirection: bool=True, RowOffset: double=None, RowCount: int=None) -> RectangularOccurrencePattern. Params (9,1)=collection, (9,1)=entity, (11,1)=bool, (12,1), (12,1)=count, (12,17)=RowEntity, (11,49)=bool, (12,17)=opt, (12,17)=opt. ColumnEntity/RowEntity are work axes or edges defining pattern axes. ColumnNaturalDirection/RowNaturalDirection: True uses entity direction, False reverses. Offsets in cm between instances.
- Fusion: occurrences.createRectangularPattern(sourceOccurrence, direction1, spacing1, count1, direction2, spacing2, count2).
### add_circular_occurrence_pattern
- params: parent_components: ObjectCollection, axis_entity: Entity (axis for rotation), axis_natural_direction: bool, angle_offset: double (radians), count: int
- Inventor: OccurrencePatterns.AddCircularPattern(ParentComponents: ObjectCollection, AxisEntity, AxisEntityNaturalDirection: bool, AngleOffset: double, Count: int) -> CircularOccurrencePattern. Params (9,1)=collection, (9,1)=axis entity, (11,1)=bool, (12,1)=angle, (12,1)=count. AxisEntity work axis or edge. AngleOffset in radians (full circle = 2π). Count includes source (e.g., Count=4 makes 4 total instances).
- Fusion: occurrences.createCircularPattern(sourceOccurrence, axisOfRotation, angleSpacing, count).
### add_feature_based_occurrence_pattern
- params: parent_components: ObjectCollection, feature_pattern: FeaturePattern (from source component)
- Inventor: OccurrencePatterns.AddFeatureBasedPattern(ParentComponents: ObjectCollection, FeaturePattern) -> FeatureBasedOccurrencePattern. Params (9,1)=collection, (9,1)=feature pattern object from source definition. Replicates part's internal feature pattern at assembly level.
- Fusion: n/a; Fusion patterns at part level, not assembly level; feature patterns are internal to bodies.
### analyze_interference
- params: set1: ObjectCollection (occurrences/parts), set2: ObjectCollection (opt; if missing, set1 vs. all others)
- Inventor: AssemblyComponentDefinition.AnalyzeInterference(Set1: ObjectCollection, Set2: ObjectCollection=None) -> InterferenceResults. Params (9,1), (12,17)=opt. Returns results object with individual interference volumes, surfaces, and statistics. GOTCHA: Expensive operation; call sparingly. Set2=None compares Set1 against rest of assembly.
- Fusion: Design => Inspect => Interference Analysis (UI-only in 2024); API: adsk.fusion.DesignAttributes.interferences (read-only, no active compute).
### get_degrees_of_freedom
- params: occurrence: ComponentOccurrence
- Inventor: ComponentOccurrence.GetDegreesOfFreedom(out TranslationDegreesCount: int, out TranslationDegreesVectors: ObjectCollection, out RotationDegreesCount: int, out RotationDegreesVectors: ObjectCollection, out DOFCenter: Point). Params (16387,2)=count out, (16393,2)=vectors out, (16387,2)=count out, (16393,2)=vectors out, (16393,2)=point out. ByRef output parameters. Returns translation axes (e.g., 1 axis = slider), rotation axes, and center point. GOTCHA: ByRef parameters—use variable passing or _ApplyTypes_.
- Fusion: Joint.degreesOfFreedom property (e.g., joint.degreesOfFreedom.rotationalDegreesOfFreedom).
### suppress_unsuppress_occurrence
- params: occurrence: ComponentOccurrence, suppress: bool
- Inventor: ComponentOccurrence.Suppress(SkipDocumentSave: bool=False) -> void. Params (11,49). Also: Unsuppress() with no params. Suppressed occurrences hidden and excluded from constraint solving. GOTCHA: Suppress does not delete; unsuppress restores. Grounded occurrences cannot be suppressed.
- Fusion: occurrence.isVisible = False / True; or occurrence.isLightBulbOn for visibility control.
### replace_component
- params: occurrence: ComponentOccurrence, new_file_path: str, replace_all: bool
- Inventor: ComponentOccurrence.Replace(FileName: str, ReplaceAll: bool) -> void. Params (8,1), (11,1). ReplaceAll=True replaces all occurrences of old component; False replaces only this instance. FileName full path to new component file.
- Fusion: n/a; must delete and re-add occurrence.
### transform_occurrence
- params: occurrence: ComponentOccurrence, matrix: Matrix
- Inventor: ComponentOccurrence.SetTransformWithoutConstraints(Matrix: Matrix) -> void. Params (9,1). Matrix 4×4 transformation in assembly space (cm). GOTCHA: Ignores all constraints on next solver iteration; normal constraint solve will override. Use for temporary visualization or one-off moves.
- Fusion: occurrence.transform = adsk.core.Matrix3D (4×4, cm units).
### mirror_components
- params: parent_components: ObjectCollection, mirror_plane: Entity (planar face/work plane), reuse_source: bool (opt)
- Inventor: NOT directly exposed in AssemblyComponentDefinition; mirror pattern must be created via OccurrencePatterns or manual constraint setup. Workaround: Use AddSymmetryConstraint on each occurrence pair + manual placement, or script iFeature/iLogic pattern. COM does not have direct MirrorComponents method in assembly scope (MirrorFeature is part-level only).
- Fusion: occurrences.createMirrorPattern(sourceOccurrence, mirrorPlane) -> MirrorOccurrencePattern.

**enums:** AssemblyJointTypeEnum: kRigidJointType=102401, kRotationalJointType=102402, kSlideJointType=102403, kCylindricalJointType=102404, kPlanarJointType=102405, kBallJointType=102406; MateConstraintSolutionTypeEnum: kOpposedSolutionType=115457 (default), kAlignedSolutionType=115458, kUndirectedSolutionType=115459, kNoSolutionType=115460; AngleConstraintSolutionTypeEnum: kDirectedSolution=78593 (default), kUndirectedSolution=78594, kReferenceVectorSolution=78595

## generators-ilogic
### insert_ifeature
- params: doc_path: str, ifeature_path: str (e.g., 'C:\path\to\custom.ide'), inputs: dict (optional, maps iFeatureInput.Name -> entity_proxy), params: dict (optional, maps param_name -> value in cm/deg)
- Inventor: PartComponentDefinition.Features.iFeatures.Add(Definition) where Definition=iFeatures.CreateiFeatureDefinition(ifeature_path). Set inputs via iFeatureDefinition.iFeatureInputs collection. Snippet: doc=app.Documents.Open(doc_path); compdef=doc.ComponentDefinition; idef=compdef.iFeatures.CreateiFeatureDefinition(ifeature_path); ifeat=compdef.iFeatures.Add(idef). CastTo iFeatureDefinition from generic IDispatch. Must provide entity geometry (faces/edges/sketches) or iFeatureEntityInput.Entity will be null.
- Fusion: n/a - Fusion has no iFeature equivalent. Use Python add-ins with Component.features API.
### create_ifeature_definition
- params: ide_file_path: str (absolute path to .ide template file)
- Inventor: iFeatures.CreateiFeatureDefinition(FullFileName: str) -> iFeatureDefinition. Returns iFeatureDefinition CLSID={358B0B8E-D2C7-4D76-AAC6-33009864424E}. Snippet: idef=compdef.iFeatures.CreateiFeatureDefinition('C:\lib\MyHole.ide'); idef.iFeatureInputs; idef.iFeatureTable (if table-driven). Do NOT call Add() until all inputs/params are configured.
- Fusion: n/a
### configure_ifeature_inputs
- params: ifeature_def: iFeatureDefinition, input_map: dict {input_name: geometry_entity_proxy}
- Inventor: iFeatureDefinition.iFeatureInputs collection. Each iFeatureInput has Name, EntityType (flags from iFeatureEntityInputTypeEnum), Prompt. Set entity via iFeatureEntityInput.Entity = face/edge/sketch_entity. Snippet: for input in idef.iFeatureInputs: if input.Name=='SelectFace': input.Entity=selected_face. GOTCHA: Must CastTo iFeatureEntityInput if input has sub-entities; EntityType bitmasks (kiFeatureEntityInputTypePlanarFace=4096, kiFeatureEntityInputTypeCircularEdge=32, etc.) filter what geometry is valid.
- Fusion: n/a
### set_ifeature_table_parameters
- params: ifeature_def: iFeatureDefinition, table_row_index: int, param_values: dict {col_name: value}
- Inventor: iFeatureDefinition.IsTableDriven returns bool. If true: iFeatureDefinition.iFeatureTable.Rows(row_index); iFeatureTableRow.Cells(col_name) = value. Snippet: if idef.IsTableDriven: table=idef.iFeatureTable; table.ActiveTableRow=table.Rows(1); for col in table.Columns: table.ActiveTableRow.Cells(col.Name).Value=my_value. GOTCHA: ActiveTableRow must be set before reading/writing cell values; column types enforce numeric/string constraints.
- Fusion: n/a
### place_content_center_part
- params: doc_path: str (assembly), content_id: str (family identifier), member_params: dict (optional, property->value), placement: dict {origin: [x,y,z], matrix: 3x3 rotation}
- Inventor: ContentCenter.GetContentObject(ContentIdentifier: str) -> ContentFamily/ContentTableRow. For assembly: assembly_doc.ComponentDefinition.Occurrences.Add(member_part_path, placement_matrix). To retrieve/refresh: ContentCenter.RefreshStandardComponents(DocumentObject, Recursive=True). Snippet: cc=app.ContentCenter; content=cc.GetContentObject('Fastener|Bolt|M8'); member=content.GetMember(params_dict); place_occ(assembly_doc, member.FilePath, placement). GOTCHA: Member.FilePath is temp; must add to assembly before closing. ContentCenter.GetTableOfContents() returns XML schema of all families.
- Fusion: n/a
### query_content_center_family
- params: query_string: str (e.g., 'Bolt', 'M8'), category_filter: str (optional)
- Inventor: ContentCenter.Query (returns ContentQuery IDispatch). ContentCenter.FamilyManager; CategoryManager; LibraryManager for hierarchical access. GetTableOfContents(ReturnAs=0, LibraryId='') -> XML variant. Snippet: toc_xml=cc.GetTableOfContents(0); cc.TreeViewTopNode for UI-style browse. For direct query: families=cc.FamilyManager to iterate ContentFamily objects. No direct LINQ-style search; must parse XML or iterate collections.
- Fusion: n/a
### access_ilogic_addin
- params: app: Application
- Inventor: iLogic is accessed via Application.GetInterfaceObject('Autodesk.iLogic.Automation'). Returns IDispatch with methods like RunRule, RunExternalRule, AddRule, ParametersTable, Forms. Snippet: ilogic_app=app.GetInterfaceObject('Autodesk.iLogic.Automation'); ilogic_app.RunRule(doc, rule_name, rule_file). GOTCHA: This is NOT in gen_py; iLogic is a separate add-in. Return type is opaque IDispatch; no type info in public COM. Rule must exist in document or external .iLogicVb file.
- Fusion: n/a - Fusion Design Scripts API does not have iLogic. Use Python API with Component.modelParameters for parameterization.
### configure_ilogic_options
- params: event_filter: int (enum iLogicEventTriggersFilterEnum), external_rule_dirs: list[str], excel_engine: int (enum iLogicExcelEngineTypeEnum), enable_security: bool
- Inventor: Application.iLogicOptions (property). Properties: EventTriggersFilter (kAllEventsEnabled=119809, kNoEventsEnabled=119811, kAllEventsEnabledExceptAfterOpenAndClose=119810), ExternalRuleDirectories (collection variant), ExternalRuleFileNames (collection variant), ExcelEngineType (kInternalExcelEngine=119553, kCOMExcelEngine=119554), EnableRuleSecurityInspection (bool), CustomAddInDirectory. Snippet: app.iLogicOptions.EventTriggersFilter=119811; app.iLogicOptions.ExcelEngineType=119553. GOTCHA: ExternalRuleDirectories is a read-only collection; to add directories, retrieve, modify, reassign.
- Fusion: n/a
### design_accelerator_workaround
- params: generator_type: str (e.g., 'SpurGear', 'BoltedConnection'), target_doc: Document, parameters: dict
- Inventor: NO DIRECT API. Alternatives: (1) Create .ide iFeature templates in Inventor, then insert via insert_ifeature tool. (2) Use iLogic: write VB.NET rule that calls Design Accelerator UI programmatically (requires user interaction or macro replay). (3) Manually model geometry via PartFeatures (add sketches, extrude, pattern). Snippet: For gears: create involute sketch (parametric), extrude, circular pattern. For bolted connections: reference component via ComponentOccurrences.Add(), apply constraints in assembly. GOTCHA: Design Accelerator is UI-only in Inventor 2024+; no COM exposure. Must fall back to iLogic or manual geometry.
- Fusion: Fusion has GearGenerator add-in (open-source); use Python add-in to call gear geometry functions.

**enums:** iFeatureEntityInputTypeEnum: kiFeatureEntityInputTypeUnknown=0, kiFeatureEntityInputTypeVertex=1, kiFeatureEntityInputTypeSketchPoint=2, kiFeatureEntityInputTypeGenericEdge=8, kiFeatureEntityInputTypeLinearEdge=16, kiFeatureEntityInputTypeCircularEdge=32, kiFeatureEntityInputTypeWorkAxis=64, kiFeatureEntityInputTypeGenericSketchCurve=128, kiFeatureEntityInputTypeLinearSketchCurve=256, kiFeatureEntityInputTypeCircularSketchCurve=512, kiFeatureEntityInputTypeEllipticalSketchCurve=1024, kiFeatureEntityInputTypeSplineSketchCurve=2048, kiFeatureEntityInputTypePlanarFace=4096, kiFeatureEntityInputTypeWorkPlane=8192, kiFeatureEntityInputTypeGenericSurface=16384, kiFeatureEntityInputTypeCylindricalSurface=32768, kiFeatureEntityInputTypeConicalSurface=65536, kiFeatureEntityInputTypeSphericalSurface=131072, kiFeatureEntityInputTypeToroidalSurface=262144; iFeatureParamLimitTypeEnum: kParamLimitNone=33281, kParamLimitRange=33282, kParamLimitList=33283; iLogicEventTriggersFilterEnum: kAllEventsEnabled=119809, kAllEventsEnabledExceptAfterOpenAndClose=119810, kNoEventsEnabled=119811; iLogicExcelEngineTypeEnum: kInternalExcelEngine=119553, kCOMExcelEngine=119554; ContentCenterAccessOptionEnum: kVaultServerAccess=81152, kInventorDesktopAccess=81153, kVaultOrProductstreamServerAccess=81154; ContentCenterInstanceStatusEnum: kOlder=1, kNewer=2, kUpToDate=4, kNotFound=8

## Parameters, Properties, Materials, Export/Import
### add_user_parameter
- params: name: str, value_or_expr: Union[float, str, bool], units_spec: str, is_expression: bool = True
- Inventor: UserParameters.AddByExpression(Name: str, Expression: str, UnitsSpecifier: str) -> UserParameter | AddByValue(Name: str, Value: Variant, UnitsSpecifier: str) -> UserParameter. In code: doc = app.ActiveDocument; asm_def = doc.ComponentDefinition; params = asm_def.Parameters; user_params = params.UserParameters; param = user_params.AddByExpression('myParam', '10mm', 'mm'); param.Expression = '20mm' to update.
- Fusion: userParameters.add() method on part body, returns UserParameter object; set expression via parameter.expression = '10cm'. NOTE: Fusion uses cm internally, not mm.
### set_parameter_tolerance
- params: param_name: str, tolerance_type: str (basic, deviation, fits, limits, minmax, symmetric, reference), upper: float = None, lower: float = None, fits_type: str = None
- Inventor: Parameter.Tolerance: Tolerance object. Methods: SetToDefault(), SetToDeviation(UpperTolerance, LowerTolerance), SetToFits(FitsToleranceType: int, HoleTolerance: str, ShaftTolerance: str), SetToLimits(LimitsToleranceType: int, Upper, Lower), SetToMinMax(MinMaxToleranceType: int, DeviationValue), SetToSymmetric(Tolerance), SetToBasic(), SetToMin(), SetToMax(), SetToReference(). Property: ToleranceType: int. Example: param.Tolerance.SetToDeviation(0.5, -0.5) or param.Tolerance.SetToFits(C.kH7Fit, 'h6', 'H7'). Gotcha: must CastTo Tolerance from parameter.Tolerance property.
- Fusion: parameter.tolerance object; set via parameter.tolerance.setToDeviation(upper, lower) or other setter methods. Less extensive enum support than Inventor.
### add_model_parameter
- params: name: str, value_or_expr: Union[float, str], units_spec: str, is_expression: bool = True
- Inventor: ModelParameters.AddByExpression(Expression: str, UnitsSpecifier: str, Name: str = '') -> ModelParameter | AddByValue(Value: Variant, UnitsSpecifier: str, Name: str = ''). Code: doc = app.ActiveDocument; compdef = doc.ComponentDefinition; params = compdef.Parameters; model_params = params.ModelParameters; mp = model_params.AddByExpression('10 + my_user_param', 'mm', 'calculated_height'). Returns ModelParameter object with same properties as Parameter base class (Expression, Value, Tolerance, etc.).
- Fusion: modelParameters.add() on part; similar to user parameters but tagged as model-driven. Fusion does not strongly distinguish; use parameter naming convention.
### read_document_iproperties
- params: property_set_name: str (e.g., 'Design Tracking Properties', 'Inventor Summary Information'), property_name: str
- Inventor: Document.PropertySets: PropertySets collection. Get PropertySet by name: pset = doc.PropertySets('Design Tracking Properties'); then iterate Property objects or use Item(name). Standard set names: 'Design Tracking Properties', 'Inventor Summary Information'. Read: prop_value = pset('Author').Value; Write: pset('Author').Value = 'Engineer Name'; must call doc.PropertySets.FlushToFile() to persist. Gotcha: some props are read-only in summary set; use PropertySet.Add() for custom properties, but design tracking props must exist before edit.
- Fusion: document.properties dictionary; access via doc.properties['Author'] = 'Name'. Limited to subset of common properties; no PropertySets collection equivalent. Material must be set via component definition (see set_part_material tool).
### set_part_material
- params: material_name: str (e.g., 'Steel-Mild', 'Aluminum 6061-T6'), is_local_copy: bool = False
- Inventor: PartComponentDefinition.Material: Material object. Code: doc = app.ActiveDocument; compdef = doc.ComponentDefinition; doc.Materials returns Materials collection (all available); assign: compdef.Material = doc.Materials('Steel Stainless'); or to copy from global: new_mat = doc.Materials('Aluminum').Copy('MyLocalAl'); compdef.Material = new_mat. Material properties (read-write): Density, YoungsModulus, PoissonsRatio, YieldStrength, UltimateTensileStrength, ThermalConductivity, LinearExpansion, SpecificHeat. Gotcha: must use Material object, not string name.
- Fusion: body.material = app.materials.itemByName('Steel-Mild') or create new Material(). Properties: density, youngModulus, etc. Fusion automatically updates MassProperties.
### get_mass_properties
- params: accuracy: str (Low, Medium, High, VeryHigh) = 'Medium', include_cosm_welds: bool = True, include_qty_overrides: bool = False
- Inventor: PartComponentDefinition.MassProperties: MassProperties object. Properties: Volume, Mass, Area, CenterOfMass (Point), Accuracy (int), AvailableAccuracy. Methods: XYZMomentsOfInertia(Ixx, Iyy, Izz, Ixy, Iyz, Ixz out-params), PrincipalMomentsOfInertia(I1, I2, I3), RadiusOfGyration(Kx, Ky, Kz), RotationToPrincipal(Rx, Ry, Rz), AchievedAccuracy(Area, Volume out). Code: mp = compdef.MassProperties; mp.Accuracy = C.kHigh; vol = mp.Volume; mass = mp.Mass; center_pt = mp.CenterOfMass; Ixx, Iyy, Izz = None, None, None; mp.XYZMomentsOfInertia(Ixx, Iyy, Izz, None, None, None). Gotcha: out-parameters are ByRef; pass list/array references; set CacheResultsOnCompute=False if updated design.
- Fusion: body.physicalProperties returns object with mass, volume, centerOfMass (Vector3), principalMomentsOfInertia array, etc. Read-only; computed automatically on body update.
### export_file
- params: file_path: str, file_format: str (step, iges, sat, 3mf, jt, dwg, dxf, stl, obj, pdf), options: Dict[str, Any] = None
- Inventor: PartDocument.SaveAs2(FullFileName: str, SaveCopyAs: bool, Options: Variant = None) -> void for .ipt native. For translation: use document.SaveAsWithOptions(FileName, Options). Typical: doc.SaveAs('path.ipt', False) or doc.SaveAs2('path.ipt', True, None). Translators (STEP, IGES, SAT, etc.) invoked via SaveAsWithOptions with format-specific Options object (VB/iLogic construct, not easily exposed via COM; alternative: use command-line Inventor or iLogic macro). For drawing: use DrawingDocument.SaveAs(). Gotcha: COM does not directly expose translator options object type; recommend SaveAs for native format only, use Inventor scripting/iLogic for export, or use Autodesk Inventor SDK (C++ DLL).
- Fusion: exportManager.export() on document. Format enum: exportManager.export(body, 'step') or .export(..., 'iges', options). Supports step, iges, sat, 3mf, jt, stl, obj, dwg (drawings), pdf, usdz. Options passed as dict (e.g., {'singleFile': True}).
### import_file
- params: file_path: str, file_format: str = 'auto', import_mode: str (reference, link, embedded) = 'reference'
- Inventor: Application.Documents.Open(FileName: str, FullFileName: bool = True) -> Document for opening STEP/IGES files natively. For import as geometry into active part: use iFeature or Desktop.ImportData (not standard COM API). Alternative: SaveCopyAs + Open pattern. Gotcha: no direct 'import as reference' COM method; must use iLogic/Macro or open file as separate document and link via assembly constraints.
- Fusion: importManager.importToTarget() or importManager.importFile(). Supports formats listed in exportManager. Returns geometry proxy objects. Options control placement and feature generation.
### list_parameters
- params: filter_by_type: str = 'all' (user, model, reference, all), as_table: bool = False
- Inventor: Parameters (base collection): Parameters.UserParameters (UserParameters), Parameters.ModelParameters (ModelParameters), Parameters.ReferenceParameters (ReferenceParameters). Iterate: for i in range(1, doc.ComponentDefinition.Parameters.UserParameters.Count + 1): param = doc.ComponentDefinition.Parameters.UserParameters(i); print(param.Name, param.Expression, param.Value). Export to XML: doc.ComponentDefinition.Parameters.ExportToXML(filePath, options=None). Import: Parameters.ImportFromXML(filePath).
- Fusion: userParameters collection on part body; iterate with for param in body.userParameters: print(param.name, param.expression, param.value). No built-in XML export; construct manually or use export manager.
### manage_parameter_table
- params: table_file_path: str, start_cell: str = 'A1', linked: bool = True
- Inventor: Parameters.ParameterTables (ParameterTables collection). Add table: tbl = params.ParameterTables.Add(fileName, startCell='A1', linked=True); returns ParameterTable object. Properties: FileName, StartCell, Linked (bool). Methods: Export(FileName, FileFormat: int, Options). Gotcha: ParameterTable does NOT directly create a live link to Inventor features; it is a reference object for manual syncing. Use iLogic or Design Studio for parametric table-to-model automation.
- Fusion: No direct parameter table equivalent. Use parameter spreadsheet asset or external Python script to read table and call setUserParameters().
### get_component_appearances
- params: include_material_appearances: bool = True
- Inventor: Document.MaterialAssets (AssetsEnumerator): enumerate all material assets (not same as Material physical props). Appearances: Document.ActiveAppearance (current), ActiveAppearanceOverride, AppearanceSourceType. For component: compdef.Document.Appearances (not directly on compdef). Code: for i in range(1, doc.MaterialAssets.Count + 1): asset = doc.MaterialAssets(i); print(asset.Name). Gotcha: Appearances and Materials are separate (appearance is visual, material is physical); confusing in UI.
- Fusion: appearanceAssets collection on document; iterate to list all appearances. component.appearance = asset or component.material to apply. appearance.color, .texture, .bumpMap properties.
### set_custom_property
- params: property_name: str, property_value: Union[str, float, int], property_set_name: str = 'Custom'
- Inventor: PropertySet.Add(PropValue: Variant, Name: str = None, PropId: int = None) -> Property. Code: pset = doc.PropertySets('Custom') if doc.PropertySets.PropertySetExists('Custom') else doc.PropertySets.Add('Custom'); prop = pset.Add('Value123', 'MyField'); or direct access: pset('MyField').Value = 'NewValue'; doc.PropertySets.FlushToFile(). Gotcha: standard sets ('Design Tracking Properties') do not allow Add; only pre-defined properties can be written. Create custom PropertySet first via PropertySets.Add(name, internal_name).
- Fusion: No PropertySets; use document.properties dict (limited) or custom attributes on objects via attributeSets. Less flexible than Inventor.

**enums:** AccuracyEnum: kLow=69377, kMedium=69378, kHigh=69379, kVeryHigh=69380; ParameterTypeEnum: (not in gen_py; inferred from Parameter.ParameterType property); ToleranceTypeEnum: kDefault, kDeviation, kFits, kLimits, kMinMax, kSymmetric, kBasic, kMin, kMax, kReference, kShowFits (specific int values in Tolerance class methods, not enumerated as constants); FileFormatEnum (ParameterTable export): kMicrosoftExcelFormat=74498, kTextFileCommaDelimitedFormat=74502, kTextFileTabDelimitedFormat=74501, kUnicodeTextFileCommaDelimitedFormat=74504, kUnicodeTextFileTabDelimitedFormat=74503; DWGFileVersionEnum: kAutoCAD2000=86529, kAutoCAD2004=86530, kAutoCAD2007=86531, kAutoCAD2010=86532, kAutoCAD2013=86533, kAutoCAD2018=86534

## drawings-sheetmetal-surfaces
### add_drawing_sheet
- params: sheet_size (enum: A4,A3,A2,A1,A0,ANSI_A,ANSI_B), orientation (enum: portrait, landscape), sheet_name (str), width_cm (opt float), height_cm (opt float)
- Inventor: Sheets.Add(Size, Orientation, SheetName, Width, Height) returns Sheet. Size enums: kANSI_A=9989, kANSI_B=9990, etc. Orientation: kPortrait=10242, kLandscape=10243. Python: sheets = drawing_doc.Sheets; new_sheet = sheets.Add(C.kANSI_A, C.kPortrait, 'Sheet1', width, height)
- Fusion: Not available via public API. Must create sheets via UI or use legacy export. Fusion focuses on modeling, not drawing creation natively.
### add_base_view
- params: model (document/body), position (Point2d in cm), scale (float, 1.0=full size), view_orientation (enum: front,top,right,isometric), view_style (enum: hidden_line,shaded,wireframe)
- Inventor: DrawingViews.AddBaseView(Model, Position, Scale, ViewOrientation, ViewStyle, ModelViewName, ArbitraryCamera, AdditionalOptions) returns DrawingView. ViewOrientation: kFront=1, kTop=2, kRight=3, kIsometric=7. Signature: view = sheet.DrawingViews.AddBaseView(model, tg.CreatePoint2d(5, 5), 1.0, C.kFront, C.kHiddenLine); model is Document, Position is Point2d via TransientGeometry.
- Fusion: drawings.createView(document, viewConfiguration) - limited; Fusion prioritizes 3D models. Use sketches for drawing-like 2D content.
### add_projected_view
- params: parent_view (DrawingView), position (Point2d in cm), view_style (enum), scale_factor (opt float)
- Inventor: DrawingViews.AddProjectedView(ParentView, Position, ViewStyle, Scale) returns DrawingView. ViewStyle enum: kHiddenLine=0, kShaded=1, kWireframe=2. Example: projected = sheet.DrawingViews.AddProjectedView(base_view, tg.CreatePoint2d(10, 5), C.kHiddenLine, 1.0)
- Fusion: Must manually position views or use sketch layout references.
### add_section_view
- params: parent_view (DrawingView), section_line_sketch (Sketch on sheet), position (Point2d), view_style (enum), scale (opt float), show_label (bool), full_depth (bool), section_depth (opt float)
- Inventor: DrawingViews.AddSectionView(ParentView, SectionLineSketch, Position, ViewStyle, Scale, ShowLabel, Name, Reserved, FullDepth, SectionDepth) or AddSectionView2(...). SectionLineSketch is a PlanarSketch on the sheet with a line or spline defining cut plane. Example: section = sheet.DrawingViews.AddSectionView(base_view, sketch, tg.CreatePoint2d(12, 5), C.kHiddenLine, 1.0, True, 'Section A-A', True, True)
- Fusion: No native section view API. Use sketch-based geometry to simulate.
### add_detail_view
- params: parent_view (DrawingView), position (Point2d for detail location), view_style (enum), fence_is_circular (bool), fence_center_or_corner (Point2d), fence_radius_or_corner2 (float or Point2d), scale (float), show_label (bool)
- Inventor: DrawingViews.AddDetailView(ParentView, Position, ViewStyle, CircularFence, FenceCenterOrCornerOne, FenceRadiusOrCornerTwo, AttachPoint, Scale, ShowLabel, Name, Reserved). If CircularFence=True, radius is double; if False, corner2 is Point2d. Example: detail = sheet.DrawingViews.AddDetailView(base_view, tg.CreatePoint2d(15, 10), C.kHiddenLine, True, tg.CreatePoint2d(5, 5), 2.0, None, 2.5, True, 'Detail A')
- Fusion: Not available. Create detail via sketch markup.
### add_linear_dimension
- params: text_origin (Point2d for label placement in cm), intent_one (GeometryIntent on line/point), intent_two (GeometryIntent on line/point), dimension_type (enum: horizontal,vertical,aligned), arrowheads_inside (bool), dimension_style (opt DimensionStyle), layer (opt Layer)
- Inventor: GeneralDimensions.AddLinear(TextOrigin, IntentOne, IntentTwo, DimensionType, ArrowheadsInside, DimensionStyle, Layer) returns LinearGeneralDimension. DimensionType: 60161 (kAlignedDimensionType), 60162 (kHorizontalDimensionType), 60163 (kVerticalDimensionType). Intent created via DrawingView.CreateGeometryIntent(entity, point/None). Example: dim = sheet.GeneralDimensions.AddLinear(tg.CreatePoint2d(7, 3), intent1, intent2, 60163, True); intent1 = view.CreateGeometryIntent(edge1); intent2 = view.CreateGeometryIntent(edge2)
- Fusion: sketches.createDimension(...) on sketch constraints; not for drawing dimensions. Drawing dimensions require manual placement in Fusion.
### add_diameter_dimension
- params: text_origin (Point2d in cm), intent (GeometryIntent on arc/circle), arrowheads_inside (bool), leader_from_center (bool), single_dimension_line (bool), dimension_style (opt), layer (opt)
- Inventor: GeneralDimensions.AddDiameter(TextOrigin, Intent, ArrowheadsInside, LeaderFromCenter, SingleDimensionLine, DimensionStyle, Layer) returns DiameterGeneralDimension. Example: dim = sheet.GeneralDimensions.AddDiameter(tg.CreatePoint2d(8, 4), intent, False, False, True); intent = view.CreateGeometryIntent(circle_edge)
- Fusion: sketch.sketchCircles.addByCenter(...) for modeling; no drawing-level diameter dimension API.
### add_radius_dimension
- params: text_origin (Point2d in cm), intent (GeometryIntent on arc/circle), arrowheads_inside (bool), leader_from_center (bool), jogged (bool), dimension_style (opt), layer (opt)
- Inventor: GeneralDimensions.AddRadius(TextOrigin, Intent, ArrowheadsInside, LeaderFromCenter, Jogged, DimensionStyle, Layer) returns RadiusGeneralDimension. Example: dim = sheet.GeneralDimensions.AddRadius(tg.CreatePoint2d(9, 5), intent, False, False, False)
- Fusion: No direct drawing API; use sketch constraints.
### add_parts_list
- params: view_or_model (DrawingView or Document assembly), placement_point (Point2d in cm), level (enum: structured, parts_only, standard), numbering_scheme (BalloonValueSet opt), num_sections (int), wrap_left (bool)
- Inventor: PartsLists.Add(ViewOrModel, PlacementPoint, Level, NumberingScheme, NumberOfSections, WrapLeft) returns PartsList. Level enum: 46593 (kStructured), 46594 (kPartsOnly), 46595 (kStandard). Example: bom = sheet.PartsLists.Add(assembly_doc, tg.CreatePoint2d(1, 1), C.kStructured, None, 1, True); Result object has columns, rows, style properties.
- Fusion: No native BOM/parts list API. Must integrate external data or use metadata workarounds.
### add_balloon
- params: leader_points (list of Point2d for leader line waypoints in cm), virtual_component (Component opt), level (int opt), numbering_scheme (BalloonValueSet opt), balloon_style (BalloonStyle opt), layer (Layer opt)
- Inventor: Balloons.Add(LeaderPoints, VirtualComponent, Level, NumberingScheme, BalloonStyle, Layer) returns Balloon. LeaderPoints is an ObjectCollection of Point2d. Example: pts = app.TransientObjects.CreateObjectCollection(); pts.Add(tg.CreatePoint2d(5, 5)); pts.Add(tg.CreatePoint2d(6, 6)); balloon = sheet.Balloons.Add(pts, component_occ, 1, None, balloon_style); Balloon has methods: Delete(), and properties: Text, Position, Style, LeaderPoints.
- Fusion: No native balloon/annotation API for assemblies in drawing context.
### create_flange
- params: edges (Edge collection), flange_angle_or_reference (float degrees or Plane), flange_angle_reference_type (enum: angle_value, reference_plane), flange_placement_type (enum: parallel, perpendicular opt), distance (float cm, optional, for reference plane types)
- Inventor: SheetMetalComponentDefinition.Features.FlangeFeatures.CreateDefinition(Edges, FlangeAngleReferenceType, FlangeAngleOrFlangeAngleReferencePlane, FlangePlacementType, Distance, Options) or simpler CreateFlangeDefinition(Edges, Angle/Plane, Distance) returns FlangeDefinition. Then FlangeFeatures.Add(FlangeDefinition) returns FlangeFeature. FlangeAngleReferenceType: 0 (kAngle)=angle value, 1 (kReferencePlane)=use plane. Example: edges = app.TransientObjects.CreateObjectCollection(); edges.Add(body_face.Edges(1)); flange_def = compdef.Features.FlangeFeatures.CreateFlangeDefinition(edges, 90.0, 1.0); flange = compdef.Features.FlangeFeatures.Add(flange_def). Gotcha: Edges must be boundary of base or previous flange. Definition and Add must be separate.
- Fusion: flangeFeatures.createDefinition(edgeOrFace, direction, offset, angle, options) returns FlangeDefinition; flangeFeatures.add(definition) creates feature. Syntax: flange_def = design.activeComponent.bRepBodies[0].features.flangeFeatures.createDefinition(...); flange = design.activeComponent.bRepBodies[0].features.flangeFeatures.add(flange_def)
### create_bend
- params: edges (Edge collection), bend_radius (float cm, optional from style), multi_facet_corner (bool opt), bend_options (dict opt with angle_override, relief_type, transition_type, etc.)
- Inventor: SheetMetalComponentDefinition.Features.BendFeatures.CreateBendDefinition(Edges) returns BendDefinition. Then BendFeatures.Add(BendDefinition) returns BendFeature. Edges are boundary or internal fold lines. Example: edges = app.TransientObjects.CreateObjectCollection(); edges.Add(edge); bend_def = compdef.Features.BendFeatures.CreateBendDefinition(edges); bend = compdef.Features.BendFeatures.Add(bend_def). Properties accessible on Definition: Edges, BendRadius (read-only), etc. Gotcha: Bend must connect flanges; improper edge selection fails silently.
- Fusion: bendFeatures.createDefinition(edges, bendAngle, bendRadius, options) or bendFeatures.createBendDefinition(...). Then bendFeatures.add(bendDef). Syntax similar to flange.
### create_hem
- params: edges (Edge collection), hem_width (float cm, optional), hem_options (dict opt with direction, flat_length, etc.)
- Inventor: SheetMetalComponentDefinition.Features.HemFeatures.CreateHemDefinition(Edges) returns HemDefinition. Then HemFeatures.Add(HemDefinition) returns HemFeature. Example: hem_def = compdef.Features.HemFeatures.CreateHemDefinition(edges); hem = compdef.Features.HemFeatures.Add(hem_def)
- Fusion: No direct hem feature API in public Fusion API. Use combination of flangeFeatures and foldFeatures or model manually.
### create_contour_flange
- params: path (Path from sketch curve or edge collection), edges (Edge collection opt), operation (enum: add, cut, intersect, opt), width_from_sketch_plane (bool opt), bend_edges (Edge collection opt)
- Inventor: SheetMetalComponentDefinition.Features.ContourFlangeFeatures.CreateDefinition(Path, Operation, WidthExtentsFromSketchPlane, EdgeSet, BendEdges) or CreateContourFlangeDefinition(Path, Edges) returns ContourFlangeDefinition. Path is created from sketch curve via Features.CreatePath(SketchCurve). Example: path = compdef.Features.CreatePath(sketch.SketchCurves.SketchLines(1)); cf_def = compdef.Features.ContourFlangeFeatures.CreateContourFlangeDefinition(path, edges); cf = compdef.Features.ContourFlangeFeatures.Add(cf_def)
- Fusion: No native contour flange. Model as swept surface + offset or manual assembly.
### unfold_flat_pattern
- params: base_face (Face opt for placement), merge_coplanar (bool, default True), replace_geometry (bool opt, for NoMerge variant)
- Inventor: SheetMetalComponentDefinition.Unfold() -> generates default flat pattern with result in FlatPattern property. Or Unfold2(BaseFace) specifies base face for layout. UnfoldNoMerge(BaseFace, ReplaceGeometry) skips merging coplanar faces. Example: compdef.Unfold(); flat = compdef.FlatPattern; flat.Edit(); [edit/sketch]; flat.ExitEdit(); flat_faces = flat.Faces returns modified flat geometry. Gotcha: Call only once per design intent; re-unfolding rebuilds.
- Fusion: flatPatternFeatures.createDefinition(...) -> FlatPatternDefinition; flatPatternFeatures.add(def). Limited control; mostly UI-driven. Syntax: fp_def = design.activeComponent.bRepBodies[0].features.flatPatternFeatures.createDefinition(...); fp = flatPatternFeatures.add(fp_def)
### trim_surface
- params: surface_faces (Face collection), trim_boundaries (Face, Edge, or Curve collection), trim_type (enum: standard, extend, shrink, opt)
- Inventor: SheetMetalComponentDefinition.Features.TrimFeatures - collection only; actual trim is part of surface feature workflow. For ComponentDefinition (part): CompDef.Features.TrimFeatures.Add(TrimDefinition) where TrimDefinition is created externally via surface tools. NOT directly exposed in sheet metal API for drawing. For standalone surface trim: Use iLogic or manual face operations via ReplaceFaceFeatures. Example: N/A directly via Inventor COM public API; requires iLogic macro or UI.
- Fusion: patchFeatures (not trim per se, but surface manipulation). For trim: trimFeatures.createDefinition(surfaceBody, trimType, boundaries) -> TrimDefinition; trimFeatures.add(trimDef). Syntax: trim_def = design.activeComponent.bRepBodies[0].features.trimFeatures.createDefinition(boundaries); trim = features.trimFeatures.add(trim_def)
### create_ruled_surface
- params: ruled_surface_type (enum: linear, quadric, blend, tangent), generatrix_curves (Curve collection), distance (float, for some types), vector (Vector opt)
- Inventor: SheetMetalComponentDefinition.Features.RuledSurfaceFeatures.CreateDefinition(RuledSurfaceType, GeneratrixCurves, Distance, Vector) returns RuledSurfaceDefinition. RuledSurfaceType: 0 (kLinear), 1 (kCone), 2 (kBlend), 3 (kTangentBlend). Then RuledSurfaceFeatures.Add(Definition) returns RuledSurfaceFeature. Example: curves = app.TransientObjects.CreateObjectCollection(); [add sketch curves]; ruled_def = compdef.Features.RuledSurfaceFeatures.CreateDefinition(C.kLinear, curves, None, None); ruled = compdef.Features.RuledSurfaceFeatures.Add(ruled_def)
- Fusion: patchFeatures or loftFeatures. No direct 'ruled surface' but similar via patchFeatures.createDefinition(edges, boundaryCondition) or loft of two curves.
### stitch_surfaces
- params: input_surfaces (Face/SurfaceBody collection), gap_tolerance (float cm, optional), features_to_stitch (Surface feature collection, optional)
- Inventor: NOT exposed via public Inventor COM API for direct MCP tool. Internal method: SheetMetalComponentDefinition._AutoStitchAndPromote() is hidden/undocumented. Workaround: Use iLogic VB macro 'AutoStitch' or create BoundaryPatch features to join surfaces. Example: Manual via UI or iLogic: Call iLogicVb.Macro('AutoStitch') or create BoundaryPatchFeatures with matching boundary edges. Gotcha: Stitching is typically automatic during feature creation if topology is valid.
- Fusion: No explicit stitch API. Surfaces auto-knit on creation. Separate via SurfaceBody.isSheetBody or manual face selection. For multi-body stitching: Use model.combine() or assembly constraint.
### create_punch_tool
- params: tool_definition_file (str path to *.ipt), location_faces (Face collection), offset_distance (float cm opt), orientation (enum: perpendicular, along_normal, opt)
- Inventor: SheetMetalComponentDefinition.Features.PunchToolFeatures.Add(PunchToolDefinition) creates PunchToolFeature. PunchToolDefinition must be pre-created via PunchToolFeatures.CreatePunchToolDefinition(...) [not public]. Workaround: Load ipt tool file, place occurrence. Example: punch = compdef.Features.PunchToolFeatures.Item(1); punch.iFeatureDefinition returns tool definition object. Gotcha: Tool library must be registered; no on-the-fly tool creation.
- Fusion: No direct punch tool API. Model as separate 2D tool occurrence or emboss via patternFeatures.

**enums:** ViewOrientationEnum: kFront=1, kTop=2, kRight=3, kFrontIsometric=4, kTopIsometric=5, kRightIsometric=6, kCustom=7, kHomeView=8; ViewStyleEnum: kHiddenLine=0, kShaded=1, kWireframe=2, kTrueHiddenLine=3; SheetSizeEnum: kANSI_A=9989, kANSI_B=9990, kANSI_C=9991, kANSI_D=9992, kANSI_E=9993, kA4=9994, kA3=9995, kA2=9996, kA1=9997, kA0=9998, kISOA4=10240, kISOA3=10241; OrientationEnum: kPortrait=10242, kLandscape=10243; PartsListLevelEnum: kStructured=46593, kPartsOnly=46594, kStandard=46595; DimensionTypeEnum: kAlignedDimensionType=60161, kHorizontalDimensionType=60162, kVerticalDimensionType=60163; BendReliefShapeEnum: kStraightBendReliefShape=27905, kRoundBendReliefShape=27906, kDefaultBendReliefShape=27907, kTearBendReliefShape=27908; BendTransitionEnum: kNoBendTransition=28161, kIntersectionBendTransition=28162, kStraightLineBendTransition=28163, kArcBendTransition=28164, kDefaultBendTransition=28165, kTrimToBendBendTransition=28166; FlangeAngleReferenceTypeEnum: kAngle=0 (numeric angle), kReferencePlane=1 (use plane as reference); RuledSurfaceTypeEnum: kLinear=0, kCone=1, kBlend=2, kTangentBlend=3
