# -*- coding: utf-8 -*-

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
    ViewType,
    DetailLine,
    GraphicsStyleType,
    Options,
    GeometryInstance,
    GeometryElement,
    GeometryObject,
    CurveElement,
    CategoryType
)
from pyrevit import revit, forms, script

# Function to create a scaling Transform about a specific point
def create_scaling_transform(base_point, scale_factor):
    # Translation to move the base point to the origin
    translation_to_origin = Transform.CreateTranslation(-base_point)

    # Scaling transform about the origin
    scaling = Transform.Identity
    scaling = scaling.ScaleBasis(scale_factor)

    # Translation to move back to the base point
    translation_back = Transform.CreateTranslation(base_point)

    # Combine the transforms: translate to origin, scale, translate back
    scaling_transform = translation_back.Multiply(scaling).Multiply(translation_to_origin)

    return scaling_transform

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
detail_lines = [
    dl for dl in detail_lines
    if dl.ViewSpecific and dl.LineStyle.GraphicsStyleCategory.CategoryType == CategoryType.Annotation
]

if not filled_regions and not detail_lines:
    forms.alert('No filled regions or detail lines found in the active drafting view.', exitscript=True)

# Define the base point for scaling (origin)
base_point = XYZ(0, 0, 0)

# Create scaling transform using the custom function
scaling_transform = create_scaling_transform(base_point, scale_factor)

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

    # Start sketch edit scope without an active transaction
    sketch_edit_scope = SketchEditScope(doc, 'Edit Filled Region Sketch')
    sketch_edit_scope.Start(sketch.Id)

    try:
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
            for curve in curve_loop:
                # Clone and transform the curve
                transformed_curve = curve.CreateTransformed(scaling_transform)

                # Create new model curve in the sketch
                doc.Create.NewModelCurve(transformed_curve, sketch.SketchPlane)

        # Commit the sketch edit scope
        sketch_edit_scope.Commit(True)

    except Exception as e:
        # Roll back the sketch edit scope in case of an error
        sketch_edit_scope.RollBack()
        raise e  # Re-raise the exception to be caught by the outer exception handler

# Scaling Detail Lines
with Transaction(doc, 'Scale Detail Lines'):
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

forms.alert('Filled regions and detail lines have been scaled successfully.', exitscript=True)
