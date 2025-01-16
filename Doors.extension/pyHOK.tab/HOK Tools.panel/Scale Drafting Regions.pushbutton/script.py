# -*- coding: utf-8 -*-

__title__ = 'Scale Filled Regions'
__author__ = 'HOK'

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    FilledRegion,
    FilledRegionType,
    Transaction,
    Transform,
    XYZ,
    ViewType,
    CurveLoop,
    CurveElement,
    ElementId,
    CategoryType
)
from pyrevit import revit, forms, script


def create_scaling_transform(base_point, scale_factor):
    translation_to_origin = Transform.CreateTranslation(-base_point)
    scaling = Transform.Identity.ScaleBasis(scale_factor)
    translation_back = Transform.CreateTranslation(base_point)
    scaling_transform = translation_back.Multiply(scaling).Multiply(translation_to_origin)
    return scaling_transform


doc = revit.doc
active_view = doc.ActiveView

# Must be a drafting view
if active_view.ViewType != ViewType.DraftingView:
    forms.alert('This script must be run in a drafting view.', exitscript=True)

# Get scale factor
scale_factor_input = forms.ask_for_string(
    default='2.0',
    prompt='Enter the scale factor (e.g., 2.0 for doubling the size):',
    title='Scale Factor'
)

if not scale_factor_input:
    script.exit()

try:
    scale_factor = float(scale_factor_input)
except ValueError:
    forms.alert('Invalid scale factor. Please enter a numeric value.', exitscript=True)

# Collect filled regions
filled_regions = FilteredElementCollector(doc, active_view.Id)\
    .OfClass(FilledRegion)\
    .ToElements()

# Collect detail lines
detail_lines = FilteredElementCollector(doc, active_view.Id)\
    .OfClass(CurveElement)\
    .WhereElementIsNotElementType()\
    .ToElements()

detail_lines = [
    dl for dl in detail_lines
    if dl.ViewSpecific and dl.LineStyle.GraphicsStyleCategory.CategoryType == CategoryType.Annotation
]

if not filled_regions and not detail_lines:
    forms.alert('No filled regions or detail lines found in the active drafting view.', exitscript=True)

base_point = XYZ(0, 0, 0)
scaling_transform = create_scaling_transform(base_point, scale_factor)

with Transaction(doc, 'Scale Filled Regions and Detail Lines') as tx:
    tx.Start()

    # Scale Filled Regions
    for fr in filled_regions:
        # Get the type of the filled region
        fr_type_id = fr.GetTypeId()
        fr_type = doc.GetElement(fr_type_id)
        
        # If fr_type is None, skip
        if not fr_type:
            # You could show a message or just skip
            continue
        
        # Get boundaries
        boundaries = fr.GetBoundaries()
        if not boundaries:
            # No boundaries? Skip or handle as needed
            continue

        # Prepare list of transformed boundaries
        transformed_boundaries = []
        for boundary in boundaries:
            if not boundary:
                continue  # Skip if boundary array is None

            transformed_boundary = CurveLoop()
            for curve in boundary:
                if curve:
                    transformed_curve = curve.CreateTransformed(scaling_transform)
                    transformed_boundary.Append(transformed_curve)
            # Only add if it has at least one curve
            if not transformed_boundary.IsEmpty():
                transformed_boundaries.append(transformed_boundary)

        if not transformed_boundaries:
            # If no valid curves, skip
            continue

        # Create new filled region
        new_fr = FilledRegion.Create(doc, fr_type.Id, active_view.Id, transformed_boundaries)

        # Delete old
        doc.Delete(fr.Id)

    # Scale Detail Lines
    for dl in detail_lines:
        geom_curve = dl.GeometryCurve
        if not geom_curve:
            continue

        transformed_curve = geom_curve.CreateTransformed(scaling_transform)
        new_dl = doc.Create.NewDetailCurve(active_view, transformed_curve)
        new_dl.LineStyle = dl.LineStyle
        doc.Delete(dl.Id)

    tx.Commit()

forms.alert('Filled regions and detail lines have been scaled successfully.', exitscript=True)
