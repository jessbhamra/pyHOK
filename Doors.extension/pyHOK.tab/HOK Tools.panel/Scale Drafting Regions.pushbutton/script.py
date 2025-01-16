# -*- coding: utf-8 -*-

__title__ = 'Simple Scale - Minimal'
__author__ = 'HOK - Simplified Script'

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
from pyrevit import revit, script


def get_bounding_box_center(element, view):
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
    translation_to_origin = Transform.CreateTranslation(-base_point)
    scaling = Transform.Identity.ScaleBasis(scale_factor)
    translation_back = Transform.CreateTranslation(base_point)
    return translation_back.Multiply(scaling).Multiply(translation_to_origin)


doc = revit.doc
uidoc = revit.uidoc

active_view = doc.ActiveView
if active_view.ViewType != ViewType.DraftingView:
    print("ERROR: Must be run in a drafting view.")
    script.exit()

# Hard-coded large scale factor for clarity
scale_factor = 2.0

# Retrieve selection
selection = revit.get_selection()
selected_ids = selection.element_ids

if not selected_ids:
    print("No elements selected; nothing to scale.")
    script.exit()

print("DEBUG: Scaling factor is {}".format(scale_factor))
print("DEBUG: {} element(s) selected.".format(len(selected_ids)))

with Transaction(doc, "Minimal Scale Transaction") as t:
    t.Start()

    for elem_id in selected_ids:
        element = doc.GetElement(elem_id)
        if not element:
            print(" -> Could not retrieve element from ID={}".format(elem_id))
            continue

        # Must belong to the active view
        if element.OwnerViewId != active_view.Id:
            print(" -> Element ID={} is not in the active view.".format(elem_id))
            continue

        # Check if it's a FilledRegion or a CurveElement
        if isinstance(element, FilledRegion):
            print(" -> FilledRegion (ID={})".format(elem_id))

            center_pt = get_bounding_box_center(element, active_view)
            if center_pt is None:
                print("   -> No bounding box. Skipping.")
                continue

            transform = create_scaling_transform(center_pt, scale_factor)

            boundaries = element.GetBoundaries()
            if not boundaries:
                print("   -> No boundaries. Skipping.")
                continue

            # Rebuild boundaries
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

            if not new_loops:
                print("   -> Boundaries empty after transform. Skipping.")
                continue

            fr_type = doc.GetElement(element.GetTypeId())
            if not fr_type:
                print("   -> Could not retrieve region type. Skipping.")
                continue

            new_fr = FilledRegion.Create(doc, fr_type.Id, active_view.Id, new_loops)
            doc.Delete(elem_id)
            print("   -> Created new region ID={} and deleted old={}".format(new_fr.Id, elem_id))

        elif isinstance(element, CurveElement):
            print(" -> CurveElement (ID={})".format(elem_id))

            curve = element.GeometryCurve
            if not curve:
                print("   -> No geometry curve. Skipping.")
                continue

            center_pt = get_bounding_box_center(element, active_view)
            if center_pt is None:
                print("   -> No bounding box; using (0,0,0).")
                center_pt = XYZ(0,0,0)

            transform = create_scaling_transform(center_pt, scale_factor)
            new_curve = curve.CreateTransformed(transform)

            new_dl = doc.Create.NewDetailCurve(active_view, new_curve)

            # Copy line style
            ls = element.LineStyle
            if ls:
                new_dl.LineStyle = ls

            doc.Delete(elem_id)
            print("   -> Created new line ID={} and deleted old={}".format(new_dl.Id, elem_id))

        else:
            print(" -> ID={} is neither FilledRegion nor CurveElement. Skipping.".format(elem_id))

    t.Commit()

print("DONE: Minimal script committed. Check if changes remain visible.")
