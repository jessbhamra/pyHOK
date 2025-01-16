# -*- coding: utf-8 -*-

__title__ = 'Scale Selection as One Group'
__author__ = 'HOK - Single Center Example (with user scale input)'

from Autodesk.Revit.DB import (
    Transaction,
    XYZ,
    ViewType,
    FilledRegion,
    Transform,
    CurveElement,
    CurveLoop,
    BoundingBoxXYZ
)
from pyrevit import revit, forms, script


def get_combined_bounding_box_center(doc, view, element_ids):
    """
    Computes a bounding box that encapsulates all elements in 'element_ids'.
    Returns the center point (XYZ) or None if no valid bounding boxes.
    """
    min_x = None
    min_y = None
    min_z = None
    max_x = None
    max_y = None
    max_z = None

    for eid in element_ids:
        elem = doc.GetElement(eid)
        if not elem:
            continue
        # Only consider elements truly in the active view
        if elem.OwnerViewId != view.Id:
            continue

        try:
            bbox = elem.get_BoundingBox(view)
            if bbox:
                # Initialize min/max if first valid box
                if min_x is None:
                    min_x = bbox.Min.X
                    min_y = bbox.Min.Y
                    min_z = bbox.Min.Z
                    max_x = bbox.Max.X
                    max_y = bbox.Max.Y
                    max_z = bbox.Max.Z
                else:
                    # Update existing min/max
                    if bbox.Min.X < min_x:
                        min_x = bbox.Min.X
                    if bbox.Min.Y < min_y:
                        min_y = bbox.Min.Y
                    if bbox.Min.Z < min_z:
                        min_z = bbox.Min.Z
                    if bbox.Max.X > max_x:
                        max_x = bbox.Max.X
                    if bbox.Max.Y > max_y:
                        max_y = bbox.Max.Y
                    if bbox.Max.Z > max_z:
                        max_z = bbox.Max.Z
        except:
            pass

    if min_x is None:
        # Means we found no valid bounding boxes at all
        return None

    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    cz = (min_z + max_z) / 2.0
    return XYZ(cx, cy, cz)


def create_scaling_transform(base_point, scale_factor):
    translation_to_origin = Transform.CreateTranslation(-base_point)
    scaling = Transform.Identity.ScaleBasis(scale_factor)
    translation_back = Transform.CreateTranslation(base_point)
    return translation_back.Multiply(scaling).Multiply(translation_to_origin)


# ------------------------------------------------------------------------
doc = revit.doc
active_view = doc.ActiveView

# Ensure we're in a drafting view
if active_view.ViewType != ViewType.DraftingView:
    script.exit("ERROR: Must be run in a Drafting View.")

# Prompt user for the scale factor
scale_factor_input = forms.ask_for_string(
    default='2.0',
    prompt='Enter the scale factor (e.g., 2.0 for doubling size):',
    title='Scale Factor'
)

# If user cancels or leaves blank
if not scale_factor_input:
    script.exit("User canceled scale factor input.")

try:
    scale_factor = float(scale_factor_input)
except:
    script.exit("Invalid scale factor. Must be numeric.")

# Retrieve current selection
selection = revit.get_selection()
selected_ids = selection.element_ids

if not selected_ids:
    script.exit("No elements selected in the view.")

# Get one bounding box center for the entire selection
center_pt = get_combined_bounding_box_center(doc, active_view, selected_ids)
if not center_pt:
    script.exit("No valid bounding boxes for the selected elements.")

with Transaction(doc, "Scale Selection as One Group") as t:
    t.Start()

    # Create one transform for all elements
    transform = create_scaling_transform(center_pt, scale_factor)

    for eid in selected_ids:
        elem = doc.GetElement(eid)
        if not elem:
            continue
        if elem.OwnerViewId != active_view.Id:
            # Skip elements that belong to a different view
            continue

        # Scale FilledRegion
        if isinstance(elem, FilledRegion):
            fr_type = doc.GetElement(elem.GetTypeId())
            if not fr_type:
                continue

            boundaries = elem.GetBoundaries()
            if not boundaries:
                continue

            new_loops = []
            for boundary in boundaries:
                if not boundary:
                    continue
                curve_list = []
                for c in boundary:
                    if c:
                        curve_list.append(c.CreateTransformed(transform))
                if curve_list:
                    loop = CurveLoop()
                    for cc in curve_list:
                        loop.Append(cc)
                    new_loops.append(loop)

            if new_loops:
                new_fr = FilledRegion.Create(doc, fr_type.Id, active_view.Id, new_loops)
                doc.Delete(eid)

        # Scale line (CurveElement)
        elif isinstance(elem, CurveElement):
            gc = elem.GeometryCurve
            if not gc:
                continue
            new_curve = gc.CreateTransformed(transform)
            new_dl = doc.Create.NewDetailCurve(active_view, new_curve)
            if elem.LineStyle:
                new_dl.LineStyle = elem.LineStyle
            doc.Delete(eid)

        # If other element types are selected, just skip them silently

    t.Commit()

print("DONE: Scaled entire selection around the combined bounding box center by factor {}.".format(scale_factor))
