# -*- coding: utf-8 -*-
"""
Convert selected 2D detail elements (lines, filled regions, detail components, detail groups, etc.)
into a single detail item family. Optionally replace the original selection with the newly created family instance.

Steps:
1. Prompt the user for a new family name.
2. Create a new detail family from a specified template.
3. Copy selected elements (or detail group members) into the family.
4. Save and load the family into the project.
5. Optionally replace original elements/group with a family instance placed at the original centroid.

Requires: Revit 2022+, pyRevit environment.
"""

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    BuiltInCategory,
    ElementTransformUtils,
    SaveAsOptions,
    Transform,
    XYZ,
    Transaction,
    Group,
    BoundingBoxXYZ,
    Family,
    FamilySymbol,
    ViewType,
    CopyPasteOptions,
    Structure,
    UV,
    View,
    Line,
)
from pyrevit import revit, DB, forms
from System.Collections.Generic import List
import os
import clr
import tempfile
# -------------------------------
# User Config
# -------------------------------
FAMILY_TEMPLATE_PATH = r"B://Temp//detail family templates/DetailItem_HOK_I.rft"  # **Update this path as needed**

# -------------------------------
# Setup & Validation
# -------------------------------
uidoc = revit.uidoc
doc = revit.doc

current_view = doc.ActiveView
if current_view.ViewType not in [ViewType.Detail, ViewType.DraftingView]:
    forms.alert("Please run this script in a Detail or Drafting view.", exitscript=True)

if not os.path.exists(FAMILY_TEMPLATE_PATH):
    forms.alert("Detail item family template not found. Please update FAMILY_TEMPLATE_PATH in the script.", exitscript=True)

# -------------------------------
# Identify Selected Elements
# -------------------------------
selection = uidoc.Selection.GetElementIds()

# Initialize separate .NET Lists for different categories
filled_regions = List[DB.ElementId]()
lines = List[DB.ElementId]()
detail_components = []  # Store detail component instances
non_component_elements = []

# Iterate through the selection
for element_id in selection:
    element = doc.GetElement(element_id)
    if element:
        # Check if the element is a filled region
        if isinstance(element, DB.FilledRegion):
            filled_regions.Add(element_id)
            non_component_elements.append(element)
        # Check if the element is a line
        elif element.Category and element.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Lines):
            lines.Add(element_id)
            non_component_elements.append(element)
        # Check if the element is a detail component (but not a filled region)
        elif element.Category and element.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_DetailComponents):
            detail_components.append(element)

# Update the selection in the UI to only include filled regions and lines
filtered_elements = List[DB.ElementId]()
filtered_elements.AddRange(filled_regions)
filtered_elements.AddRange(lines)
uidoc.Selection.SetElementIds(filtered_elements)

# Validate non_component_elements before use
if not non_component_elements and not detail_components:
    forms.alert("No valid elements to process. Please select valid detail elements.", exitscript=True)

# Validate selection_ids
selection_ids = uidoc.Selection.GetElementIds()
if not selection_ids:
    forms.alert("No elements selected. Please select detail elements or a detail group.", exitscript=True)

centroids = [el.get_BoundingBox(current_view).Min + el.get_BoundingBox(current_view).Max * 0.5 for el in non_component_elements if el.get_BoundingBox(current_view)]
if centroids:
    avg_x = sum(c.X for c in centroids) / len(centroids)
    avg_y = sum(c.Y for c in centroids) / len(centroids)
    avg_z = sum(c.Z for c in centroids) / len(centroids)
    placement_point = XYZ(avg_x, avg_y, avg_z)
else:
    # Fallback to origin if centroid cannot be determined
    placement_point = XYZ(0, 0, 0)

# -------------------------------
# Ask User for Family Name and Save Location
# -------------------------------
family_name = forms.ask_for_string(prompt="Enter a name for the new detail family:", default="NewDetailFamily")
if not family_name:
    forms.alert("No family name provided. Operation cancelled.", exitscript=True)

save_path = forms.save_file(file_ext='rfa', default_name=family_name)
if not save_path:
    forms.alert("No save location selected. Operation cancelled.", exitscript=True)

# -------------------------------
# Create the Family
# -------------------------------
app = doc.Application
try:
    family_doc = app.NewFamilyDocument(FAMILY_TEMPLATE_PATH)
except Exception as e:
    error_message = "Failed to create a new family document. Error: {}".format(e)
    forms.alert(error_message, exitscript=True)

t_fam = Transaction(family_doc, "Create Detail Family")
t_fam.Start()

# -------------------------------
# Copy Non-Component Elements
# -------------------------------
transform = Transform.CreateTranslation(XYZ(-avg_x, -avg_y, -avg_z))

if non_component_elements:
    elem_ids = [el.Id for el in non_component_elements]
    elem_ids_col = List[DB.ElementId](elem_ids)

    opts = CopyPasteOptions()
    all_views = FilteredElementCollector(family_doc).OfCategory(BuiltInCategory.OST_Views).ToElements()
    if not all_views:
        print("No views found in the family document.")

    try:
        ElementTransformUtils.CopyElements(current_view, elem_ids_col, all_views[0], transform, opts)
    except Exception as e:
        t_fam.RollBack()
        family_doc.Close(False)
        error_message = "Failed to copy elements to the family document. Error: {}".format(e)
        forms.alert(error_message, exitscript=True)

# -------------------------------
# Handle Detail Components
# -------------------------------
if detail_components:
    loaded_comp_families = {}

    # Acquire a reference plane for placement
    active_view = family_doc.ActiveView
    placement_ref = None

    reference_planes = DB.FilteredElementCollector(family_doc) \
                         .OfClass(DB.ReferencePlane) \
                         .ToElements()

    if reference_planes:
        placement_ref = reference_planes[0].GetReference()
    else:
        # If no ReferencePlane exists, create one
        ref_plane = family_doc.FamilyCreate.NewReferencePlane(
            XYZ(0, 0, 0),
            XYZ(1, 0, 0),
            XYZ(0, 1, 0),
            family_doc.ActiveView
        )
        placement_ref = ref_plane.GetReference()

    for comp in detail_components:
        print("Element ID: {}, Type: {}, Category: {}".format(
            comp.Id,
            type(comp),
            comp.Category.Name if comp.Category else "No Category"
        ))

        # Ensure element is a FamilyInstance and a detail component
        if not isinstance(comp, DB.FamilyInstance):
            print("Element {} is not a FamilyInstance. Skipping.".format(comp.Id))
            continue

        if comp.Category is None or comp.Category.Id.IntegerValue != int(DB.BuiltInCategory.OST_DetailComponents):
            print("Element {} is not a detail component. Skipping.".format(comp.Id))
            continue

        symbol = comp.Symbol
        if symbol is None:
            print("No symbol found for component {}".format(comp.Id))
            continue

            # DEBUG: Check actual symbol type
        print("Symbol type:", symbol.GetType().FullName)

            # Use a parameter-based approach to get the name
        symbol_name_param = symbol.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if symbol_name_param:
            symbol_name = symbol_name_param.AsString()
        else:
            print("Could not retrieve symbol name for component {}".format(comp.Id))
            continue

        if not symbol_name:
            print("Symbol name is empty for component {}".format(comp.Id))
            continue

        comp_family = symbol.Family
        fam_name = comp_family.Name
 
    # Proceed with loading family, placing instance, etc.
        # Load family into the family_doc if not already loaded
        if fam_name not in loaded_comp_families:
            try:
                fam_doc = doc.EditFamily(comp_family)
                temp_dir = tempfile.gettempdir()
                temp_family_path = os.path.join(temp_dir, fam_name + ".rfa")

                if os.path.exists(temp_family_path):
                    os.remove(temp_family_path)

                fam_doc.SaveAs(temp_family_path)
                fam_doc.Close(False)

                new_fam_ref = clr.Reference[Family]()
                if family_doc.LoadFamily(temp_family_path, new_fam_ref):
                    new_fam = new_fam_ref.Value
                    loaded_comp_families[fam_name] = new_fam
                else:
                    print("Failed to load family '{}' into the family_doc.".format(fam_name))
                    continue
            except Exception as ex:
                print("Error editing/loading family '{}': {}".format(fam_name, ex))
                continue
        else:
            new_fam = loaded_comp_families[fam_name]

        # Find the matching symbol by name in the loaded family
      # Find the matching symbol by name in the loaded family
        new_comp_symbol = None
        for fsid in new_fam.GetFamilySymbolIds():
            fs = family_doc.GetElement(fsid)
            if fs:
        # Instead of fs.Name, use a parameter:
                fs_name_param = fs.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
                fs_name = fs_name_param.AsString() if fs_name_param else None

                if fs_name == symbol_name:
                    new_comp_symbol = fs
                    break


        if not new_comp_symbol:
            print("Could not find symbol '{}' in family '{}'. Skipping.".format(symbol_name, fam_name))
            continue

        # Activate symbol if not active
        if not new_comp_symbol.IsActive:
            new_comp_symbol.Activate()
            family_doc.Regenerate()

        # Determine placement point
# Determine placement point as before
        comp_location = None
        loc = comp.Location
        if loc and hasattr(loc, "Point"):
            comp_location = loc.Point
        else:
            bbox = comp.get_BoundingBox(current_view)
            if bbox:
                comp_location = (bbox.Min + bbox.Max) * 0.5
            else:
                print("No bounding box for component {}. Skipping.".format(comp.Id))
                continue

        # Determine placement point
        loc = comp.Location
        if loc and hasattr(loc, "Rotation"):
            original_rotation = loc.Rotation
        else:
            original_rotation = 0.0

        # Apply the same transform for location
        transformed_point = transform.OfPoint(comp_location)
        uv_location = XYZ(transformed_point.X, transformed_point.Y, 0)

        fs_symbol = clr.Convert(new_comp_symbol, FamilySymbol)
        active_view = family_doc.ActiveView

        if active_view is None:
            all_views = FilteredElementCollector(family_doc).OfClass(View).ToElements()
            for v in all_views:
                if v.ViewType == ViewType.DraftingView or v.ViewType == ViewType.FloorPlan:
                    active_view = v
                    break

        # Place the instance
        try:
            new_instance = family_doc.FamilyCreate.NewFamilyInstance(
                uv_location,
                fs_symbol,
                active_view
            )
    
            # Rotate the instance if needed
            if abs(original_rotation) > 1e-9:
                rotate_axis_start = XYZ(uv_location.X, uv_location.Y, uv_location.Z)
                rotate_axis_end = XYZ(uv_location.X, uv_location.Y, uv_location.Z + 1)
                rotation_axis = Line.CreateBound(rotate_axis_start, rotate_axis_end)
                ElementTransformUtils.RotateElement(family_doc, new_instance.Id, rotation_axis, original_rotation)

        except Exception as e:
            print("Failed to place detail component in family: {}".format(e))



t_fam.Commit()

# -------------------------------
# Save the Family
# -------------------------------
save_options = SaveAsOptions()
save_options.OverwriteExistingFile = True

try:
    family_doc.SaveAs(save_path, save_options)
except Exception as e:
    family_doc.Close(False)
    error_message = "Failed to save the family. Error: {}".format(e)
    forms.alert(error_message, exitscript=True)

family_doc.Close(False)


# -------------------------------
# Load Family into Project
# -------------------------------
t_load = Transaction(doc, "Load Detail Family")
t_load.Start()

loaded_family_ref = clr.Reference[Family]()
res = doc.LoadFamily(save_path, loaded_family_ref)
t_load.Commit()

if not res:
    forms.alert("Failed to load the newly created family into the project.", exitscript=True)
else:
    loaded_family = loaded_family_ref.Value

loaded_fam = None
families = FilteredElementCollector(doc).OfClass(Family).ToElements()
for f in families:
    if f.Name == family_name:
        loaded_fam = f
        break

if not loaded_fam:
    forms.alert("Cannot find the loaded family in the project.", exitscript=True)

fam_sym = None
for fsid in loaded_fam.GetFamilySymbolIds():
    fam_sym = doc.GetElement(fsid)
    if fam_sym:
        break

if not fam_sym:
    forms.alert("The loaded family has no available types.", exitscript=True)
    raise Exception("No family symbols found.")

if not fam_sym.IsActive:
    t_activate = Transaction(doc, "Activate Family Symbol")
    t_activate.Start()
    fam_sym.Activate()
    t_activate.Commit()

replace = forms.alert("Do you want to replace the original selected elements/groups with the new family instance?", 
                     title="Replace Elements?",  
                     yes=True, 
                     no=True)

if replace:
    t_replace = Transaction(doc, "Replace with Family Instance")
    t_replace.Start()

    try:
        new_instance = doc.Create.NewFamilyInstance(placement_point, fam_sym, current_view)

        # Ensure all element IDs are in a single collection before deleting
        all_elements_to_delete = List[DB.ElementId]()
        all_elements_to_delete.AddRange(filtered_elements)
        all_elements_to_delete.AddRange([el.Id for el in detail_components])

        for el_id in all_elements_to_delete:
            try:
                doc.Delete(el_id)
            except Exception as del_e:
                delete_error = "Failed to delete element ID {}. Error: {}".format(el_id.IntegerValue, del_e)
                forms.alert(delete_error, exitscript=True)
    except Exception as e:
        t_replace.RollBack()
        replace_error = "Failed to place the family instance or delete original elements. Error: {}".format(e)
        forms.alert(replace_error, exitscript=True)
        raise

    t_replace.Commit()

forms.alert("Detail family created successfully!", title="Success")
