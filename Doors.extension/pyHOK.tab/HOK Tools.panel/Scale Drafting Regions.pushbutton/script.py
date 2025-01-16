# -*- coding: utf-8 -*-

__title__ = 'Scale Selected Drafting Elements - Debug'
__author__ = 'HOK - Extended Debugging'

from Autodesk.Revit.DB import (
    Transaction,
    TransactionGroup,
    XYZ,
    FilledRegion,
    Transform,
    CurveElement,
    ViewType,
    CurveLoop,
    BoundingBoxXYZ
)
from pyrevit import revit, forms, script


def get_bounding_box_center(element, view):
    """
    Returns the center point of 'element' in the context of 'view'.
    Returns None if bounding box is invalid.
    """
    try:
        bbox = element.get_BoundingBox(view)
        if bbox:
            min_pt = bbox.Min
            max_pt = bbox.Max
            cx = (min_pt.X + max_pt.X) / 2.0
            cy = (min_pt.Y + max_pt.Y) / 2.0
            cz = (min_pt.Z + max_pt.Z) / 2.0
            return XYZ(cx, cy, cz)
    except:
        pass
    return None


def create_scaling_transform(base_point, scale_factor):
    """
    Creates a Transform that scales about 'base_point'.
    """
    translation_to_origin = Transform.CreateTranslation(-base_point)
    scaling = Transform.Identity.ScaleBasis(scale_factor)
    translation_back = Transform.CreateTranslation(base_point)
    return translation_back.Multiply(scaling).Multiply(translation_to_origin)


doc = revit.doc
active_view = doc.ActiveView

# Must be a drafting view
if active_view.ViewType != ViewType.DraftingView:
    forms.alert('This script must be run in a drafting view.', exitscript=True)

# Get user scale factor
scale_factor_input = forms.ask_for_string(
    default='2.0',
    prompt='Enter the scale factor (e.g., 2.0 to double size):',
    title='Scale Factor'
)

if not scale_factor_input:
    script.exit()

try:
    scale_factor = float(scale_factor_input)
except:
    forms.alert('Invalid scale factor. Must be numeric.', exitscript=True)

print("DEBUG: Active drafting view is Id={} Named='{}'".format(active_view.Id, active_view.Name))
print("DEBUG: Scale factor set to {}".format(scale_factor))

# --------------------------------------------------------------------------
# Get the current selection from pyRevit
selection = revit.get_selection()
selected_ids = selection.element_ids

if not selected_ids:
    forms.alert('No elements selected. Please select lines or filled regions, then run again.', exitscript=True)

print("DEBUG: The user selected {} element(s).".format(len(selected_ids)))


# Separate out FilledRegions and Lines (ANY CurveElement) from that selection
filled_regions = []
curve_elements = []

for elem_id in selected_ids:
    element = doc.GetElement(elem_id)
    if not element:
        print("DEBUG: Could not retrieve element for id={}.".format(elem_id))
        continue

    # Check if it belongs to the active drafting view
    if element.OwnerViewId != active_view.Id:
        print("DEBUG: Element id={} belongs to view {}, not the active view {}. Skipping.".format(
            elem_id, element.OwnerViewId, active_view.Id
        ))
        continue

    # Identify if it's a FilledRegion
    if isinstance(element, FilledRegion):
        filled_regions.append(element)
        print("DEBUG: -> Found a FilledRegion (ID={}).".format(elem_id))
    # Identify if it's a line (CurveElement) of any kind
    elif isinstance(element, CurveElement):
        curve_elements.append(element)
        print("DEBUG: -> Found a CurveElement (ID={}).".format(elem_id))
    else:
        print("DEBUG: -> Element id={} is not a FilledRegion or CurveElement. Skipping.".format(elem_id))

print("DEBUG: Totals => FilledRegions: {} | CurveElements: {}".format(len(filled_regions), len(curve_elements)))

if not filled_regions and not curve_elements:
    forms.alert('No valid FilledRegion or line elements in the selection.', exitscript=True)

# --------------------------------------------------------------------------
# We'll wrap everything in a TransactionGroup so if an error occurs,
# we can catch it and avoid a silent rollback.
tg = TransactionGroup(doc, 'Scale Selected Drafting Elements')
tg.Start()

try:
    with Transaction(doc, 'Scale Selected Drafting Elements - T1') as tx:
        tx.Start()

        # -------------------------------------------------
        # Scale FilledRegions
        for fr in filled_regions:
            fr_id = fr.Id
            print("\nDEBUG: Scaling FilledRegion (ID={}).".format(fr_id))

            # 1) Get bounding box center
            center_pt = get_bounding_box_center(fr, active_view)
            if center_pt is None:
                print(" -> No valid bounding box center. Skipping.")
                continue

            # 2) Build transform
            transform = create_scaling_transform(center_pt, scale_factor)

            # 3) Get boundaries
            boundaries = fr.GetBoundaries()
            if not boundaries:
                print(" -> No boundaries found. Skipping.")
                continue

            transformed_boundaries = []
            boundary_count = 0

            # Each boundary is an array of curves
            for boundary in boundaries:
                if not boundary:
                    continue

                boundary_curves = []
                for c in boundary:
                    if c:
                        boundary_curves.append(c.CreateTransformed(transform))

                if boundary_curves:
                    loop = CurveLoop()
                    for bc in boundary_curves:
                        loop.Append(bc)
                    transformed_boundaries.append(loop)
                    boundary_count += 1

            if boundary_count == 0:
                print(" -> Boundaries had no valid curves after transform. Skipping.")
                continue

            # 4) Create new FilledRegion
            fr_type_id = fr.GetTypeId()
            fr_type = doc.GetElement(fr_type_id)
            if not fr_type:
                print(" -> Could not retrieve FilledRegionType. Skipping.")
                continue

            new_fr = FilledRegion.Create(doc, fr_type.Id, active_view.Id, transformed_boundaries)
            print(" -> Created new FilledRegion ID={}. Deleting old ID={}.".format(new_fr.Id, fr_id))
            doc.Delete(fr_id)

        # -------------------------------------------------
        # Scale Lines (ANY CurveElement)
        for ce in curve_elements:
            ce_id = ce.Id
            print("\nDEBUG: Scaling CurveElement (ID={}).".format(ce_id))

            # 1) Check bounding box
            center_pt = get_bounding_box_center(ce, active_view)
            if center_pt is None:
                center_pt = XYZ(0, 0, 0)
                print(" -> No bounding box center, using global origin (0,0,0).")

            # 2) Build transform
            transform = create_scaling_transform(center_pt, scale_factor)

            # 3) Get geometry curve
            geom_curve = ce.GeometryCurve
            if not geom_curve:
                print(" -> No geometry curve. Skipping.")
                continue

            # 4) Create new curve with transform
            new_curve = geom_curve.CreateTransformed(transform)
            new_ce = doc.Create.NewDetailCurve(active_view, new_curve)

            # Try to copy line style if available
            old_style = ce.LineStyle
            if old_style:
                new_ce.LineStyle = old_style
                print(" -> Copied line style from old line to new line.")

            doc.Delete(ce_id)
            print(" -> Created new line ID={} and deleted old ID={}.".format(new_ce.Id, ce_id))

        tx.Commit()

    tg.Assimilate()

    forms.alert('Scaling transaction completed. If geometry is unchanged, check debug output.', exitscript=True)

except Exception as ex:
    # If something fails mid-transaction, we roll back
    print("\nDEBUG: Exception => {}".format(ex))
    tg.RollBack()
    forms.alert('Error occurred; transaction rolled back:\n{}'.format(ex), exitscript=True)
