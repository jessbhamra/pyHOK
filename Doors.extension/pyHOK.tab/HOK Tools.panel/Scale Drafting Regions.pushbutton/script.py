
"""Scale up multiple filled regions"""
__title__ = 'Scale Filled Regions'
__author__ = 'HOK'

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    FilledRegion,
    Transaction,
    Transform,
    CurveLoop,
    Curve,
    ElementId,
    XYZ,
    Sketch,
    SketchPlane,
    ModelCurve,
    SketchEditScope,
    ElementTransformUtils,
    Line,
    Arc,
    Ellipse,
    NurbSpline,
    ViewType
)
from pyrevit import revit, forms, script

# Get the current Revit document
doc = revit.doc

# Get the active view
active_view = doc.ActiveView

# Check if the active view is a drafting view
if not active_view.ViewType == ViewType.DraftingView:
    forms.alert('This script must be run in a drafting view.', exitscript=True)

# Prompt the user to input the scale factor
scale_factor_input = forms.ask_for_string(
    default='2.0',
    prompt='Enter the scale factor (e.g., 2.0 for doubling the size):',
    title='Scale Factor'
)

# Exit if no input
if not scale_factor_input:
    script.exit()

try:
    scale_factor = float(scale_factor_input)
except ValueError:
    forms.alert('Invalid scale factor. Please enter a numeric value.', exitscript=True)

# Collect all filled regions in the active drafting view
filled_regions = FilteredElementCollector(doc, active_view.Id)\
    .OfClass(FilledRegion)\
    .ToElements()

if not filled_regions:
    forms.alert('No filled regions found in the active drafting view.', exitscript=True)

# Start a transaction to modify the Revit document
transaction = Transaction(doc, 'Scale Up Filled Regions')
transaction.Start()

try:
    for fr in filled_regions:
        # Get the sketch associated with the filled region
        sketch_id = fr.GetSketchId()
        sketch = doc.GetElement(sketch_id)

        # Get the boundaries of the filled region
        boundaries = fr.GetBoundaries()

        # Calculate the centroid of the filled region
        points = []
        for curve_loop in boundaries:
            for curve in curve_loop:
                start_point = curve.GetEndPoint(0)
                end_point = curve.GetEndPoint(1)
                points.append(start_point)
                points.append(end_point)

        centroid = XYZ(
            sum(pt.X for pt in points) / len(points),
            sum(pt.Y for pt in points) / len(points),
            sum(pt.Z for pt in points) / len(points)
        )

        # Create a scaling transform around the centroid
        scaling_transform = Transform.ScaleBasis(centroid, scale_factor)

        # Create a list to hold the transformed curves
        transformed_curves = []

        for curve_loop in boundaries:
            for curve in curve_loop:
                # Clone the curve to avoid modifying the original
                geom_curve = curve.Clone()

                # Apply the scaling transform to the curve
                transformed_curve = geom_curve.CreateTransformed(scaling_transform)

                # Add the transformed curve to the list
                transformed_curves.append(transformed_curve)

        # Start sketch edit scope
        sketch_edit_scope = SketchEditScope(doc, 'Edit Filled Region Sketch')
        sketch_edit_scope.Start(sketch.Id)

        # Delete existing model curves in the sketch
        model_curves = sketch.GetAllModelCurves()
        for mc in model_curves:
            doc.Delete(mc.Id)

        # Create new model curves with the transformed curves
        sketch_plane = sketch.SketchPlane

        for curve in transformed_curves:
            # Create new model curve in the sketch
            if isinstance(curve, Line) or isinstance(curve, Arc) or isinstance(curve, Ellipse) or isinstance(curve, NurbSpline):
                doc.Create.NewModelCurve(curve, sketch_plane)
            else:
                # Handle other curve types if necessary
                pass

        # Finish sketch edit scope
        sketch_edit_scope.Commit(True)

    # Commit the transaction
    transaction.Commit()

    forms.alert('Filled regions have been scaled successfully.', exitscript=True)

except Exception as e:
    # Roll back the transaction in case of an error
    transaction.RollBack()
    forms.alert('An error occurred: ' + str(e), exitscript=True)
