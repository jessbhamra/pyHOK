# -*- coding: utf-8 -*-

__title__ = 'Debug Scale Filled Regions'
__author__ = 'HOK - Example Debugging Script'

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
    CategoryType,
    BoundingBoxXYZ
)
from pyrevit import revit, forms, script


def get_bounding_box_center(element, view):
    """
    Retrieves the bounding box of 'element' in the context of 'view'.
    Returns an XYZ representing the center of the bounding box.
    Returns None if bounding box is invalid.
    """
    bbox = element.get_BoundingBox(view)
    if bbox is None:
        return None
    min_pt = bbox.Min
    max_pt = bbox.Max
    center_x = (min_pt.X + max_pt.X) / 2.0
    center_y = (min_pt.Y + max_pt.Y) / 2.0
    center_z = (min_pt.Z + max_pt.Z) / 2.0
    return XYZ(center_x, center_y, center_z)


def create_scaling_transform(base_point, scale_factor):
    """
    Creates a transform that scales about 'base_point'.
    """
    # Translate to origin
    translation_to_origin = Transform.CreateTranslation(-base_point)

    # Scale around origin
    scaling = Transform.Identity.ScaleBasis(scale_factor)

    # Optional: add a small translation on X or Y to see it move
    # For example, to nudge elements 5 feet in X after scaling:
    # nudge = Transform.CreateTranslation(XYZ(5.0, 0, 0))
    # scaling = scaling.Multiply(nudge)

    # Translate back
    translation_back = Transform.CreateTranslation(base_point)
    return translation_back.Multiply(scaling).Multiply(translation_to_origin)


doc = revit.doc
active_view = doc.ActiveView

# Must be a drafting view
if active_view.ViewType != ViewType.DraftingView:
    forms.alert('This script must be run in a drafting view.', exitscript=True)

# Default large scale factor to clearly see the change
scale_factor_input = forms.ask_for_string(
    default='10.0',
    prompt='Enter the scale factor (e.g., 10.0 to enlarge by 10x):',
    title='Scale Factor'
)

if not scale_factor_input:
    script.exit()

try:
    scale_factor = float(scale_factor_input)
except ValueError:
    forms.alert('Invalid scale factor. Please enter a numeric value.', exitscript=True)

# Collect filled regions in this drafting view
filled_regions = FilteredElementCollector(doc, active_view.Id)\
    .OfClass(FilledRegion)\
    .ToElements()

# Collect detail lines (CurveElements) in this drafting view
detail_lines = FilteredElementCollector(doc, active_view.Id)\
    .OfClass(CurveElement)\
    .WhereElementIsNotElementType()\
    .ToElements()

# Filter out any model lines, keep only detail lines (Annotation category)
detail_lines = [
    dl for dl in detail_lines
    if dl.ViewSpecific
    and dl.LineStyle
    and dl.LineStyle.GraphicsStyleCategory
    and dl.LineStyle.GraphicsStyleCategory.CategoryType == CategoryType.Annotation
]

print("DEBUG: Found {} filled regions.".format(len(filled_regions)))
print("DEBUG: Found {} detail lines.".format(len(detail_lines)))

if not filled_regions and not detail_lines:
    forms.alert('No filled regions or detail lines found in the active drafting view.', exitscript=True)

# Start transaction
with Transaction(doc, 'Scale Filled Regions and Detail Lines') as tx:
    tx.Start()

    # --- Scale Filled Regions ---
    for fr in filled_regions:
        print("DEBUG: Processing FilledRegion Id={}".format(fr.Id))

        # 1) Get region type
        fr_type = doc.GetElement(fr.GetTypeId())
        if not fr_type:
            print("DEBUG:  -> Could not retrieve FilledRegionType. Skipping.")
            continue

        # 2) Get region bounding box center, to scale about that point
        center_point = get_bounding_box_center(fr, active_view)
        if center_point is None:
            print("DEBUG:  -> No valid bounding box. Skipping region.")
            continue

        print("DEBUG:  -> BoundingBox center: {}".format(center_point))
        print("DEBUG:  -> Scale factor: {}".format(scale_factor))

        # 3) Retrieve boundaries
        boundaries = fr.GetBoundaries()
        if not boundaries:
            print("DEBUG:  -> No boundaries found for this region. Skipping.")
            continue

        # 4) Build transforms
        scaling_transform = create_scaling_transform(center_point, scale_factor)

        # 5) Create new boundaries
        transformed_boundaries = []
        boundary_count = 0
        for boundary in boundaries:
            if not boundary:
                continue

            # accumulate curves first
            boundary_curves = []
            for curve in boundary:
                if curve:
                    transformed_curve = curve.CreateTransformed(scaling_transform)
                    boundary_curves.append(transformed_curve)

            if not boundary_curves:
                continue

            new_loop = CurveLoop()
            for bc in boundary_curves:
                new_loop.Append(bc)

            boundary_count += 1
            transformed_boundaries.append(new_loop)

        print("DEBUG:  -> Created {} new boundary loops for region.".format(boundary_count))

        # If no loops, skip
        if not transformed_boundaries:
            continue

        # 6) Create the new filled region
        new_fr = FilledRegion.Create(doc, fr_type.Id, active_view.Id, transformed_boundaries)

        # 7) Delete old region
        doc.Delete(fr.Id)

    # --- Scale Detail Lines ---
    for dl in detail_lines:
        print("DEBUG: Processing DetailLine Id={}".format(dl.Id))

        geom_curve = dl.GeometryCurve
        if not geom_curve:
            print("DEBUG:  -> No geometry curve on detail line. Skipping.")
            continue

        center_point = get_bounding_box_center(dl, active_view)
        if center_point is None:
            # If bounding box is None, fallback to global origin
            center_point = XYZ(0, 0, 0)
            print("DEBUG:  -> No bounding box for detail line. Using (0,0,0) as base.")

        print("DEBUG:  -> Detail line bounding box center: {}".format(center_point))

        scaling_transform = create_scaling_transform(center_point, scale_factor)

        # Transform the curve
        transformed_curve = geom_curve.CreateTransformed(scaling_transform)

        # Create new detail line
        new_dl = doc.Create.NewDetailCurve(active_view, transformed_curve)

        # Copy original line style
        if dl.LineStyle:
            new_dl.LineStyle = dl.LineStyle

        # Delete the old line
        doc.Delete(dl.Id)

    tx.Commit()

forms.alert('Filled regions and detail lines have been scaled successfully.', exitscript=True)
