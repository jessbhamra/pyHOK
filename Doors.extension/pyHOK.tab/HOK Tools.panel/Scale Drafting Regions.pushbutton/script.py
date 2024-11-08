# -*- coding: utf-8 -*-

__title__ = 'Scale Up Filled Regions and Lines in Drafting View'
__author__ = 'Your Name'

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
    ViewType,
    DetailLine,
    GraphicsStyleType,
    Options,
    GeometryInstance,
    GeometryElement,
    GeometryObject
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

# Collect all detail lines in the active drafting view
detail_lines = FilteredElementCollector(doc, active_view.Id)\
    .OfClass(CurveElement)\
    .WhereElementIsNotElementType()\
    .ToElements()

# Filter out model curves (keep only detail lines)
detail_lines = [dl for dl in detail_lines if dl.ViewSpecific and dl.LineStyle.GraphicsStyleCategory.CategoryType == Autodesk.Revit.DB.CategoryType.Annotation]

if not filled_regions and not detail_lines:
    forms.alert('No filled regions or detail lines found in the active drafting view.', exitscript=True)

# Start a transaction to modify the Revit document
transaction = Transaction(doc, 'Scale Up Filled Regions and Lines')
transaction.Start()

try:
    # Define the base point for scaling (origin)
    base_point = XYZ(0, 0, 0)

    # Create scaling transform
    scaling_transform = Transform.ScaleBasis(base_point, scale_factor)

    # Scaling Filled Regions
    for fr in filled_regions:
        # Get the sketch associated with the filled region
        # Retrieve the sketch by getting the dependent elements
        dependent_ids = fr.GetDependentElements(None)
        sketch = None
        for dep_id in dependent_ids:
            dep_elem = doc.GetElement(dep_id)
            if isinstance(dep_elem, Sketch):
                sketch = dep_elem
                break

        if not sketch:
            continue  # Skip if no sketch is found

        # Start sketch edit scope
        sketch_edit_scope = SketchEditScope(doc, 'Edit Filled Region Sketch')
        sketch_edit_scope.Start(sketch.Id)

        # Get existing model curves in the sketch
        model_curves = sketch.Profile

        # Delete existing model curves
        for curve_array in model_curves:
            for curve_elem in curve_array:
                doc.Delete(curve_elem.Id)

        # Get the boundaries of the filled region
        boundaries = fr.GetBoundaries()

        # Create new transformed curves
        for curve_loop in boundaries:
            transformed_curve_loop = CurveLoop()
            for curve in curve_loop:
                # Clone and transform the curve
                transformed_curve = curve.CreateTransformed(scaling_transform)
                transformed_curve_loop.Append(transformed_curve)

                # Create new model curve in the sketch
                doc.Create.NewModelCurve(transformed_curve, sketch.SketchPlane)

        # Finish sketch edit scope
        sketch_edit_scope.Commit(True)

    # Scaling Detail Lines
    for dl in detail_lines:
        # Get the geometry curve of the detail line
        geom_curve = dl.GeometryCurve

        # Clone and transform the curve
        transformed_curve = geom_curve.CreateTransformed(scaling_transform)

        # Create new detail line with the transformed curve
        new_dl = doc.Create.NewDetailCurve(active_view, transformed_curve)

        # Copy the line style
        new_dl.LineStyle = dl.LineStyle

        # Delete the old detail line
        doc.Delete(dl.Id)

    # Commit the transaction
    transaction.Commit()

    forms.alert('Filled regions and detail lines have been scaled successfully.', exitscript=True)

except Exception as e:
    # Roll back the transaction in case of an error
    transaction.RollBack()
    forms.alert('An error occurred: ' + str(e), exitscript=True)
