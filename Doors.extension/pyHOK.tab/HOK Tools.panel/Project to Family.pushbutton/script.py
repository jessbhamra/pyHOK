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
detail_components = List[DB.ElementId]()
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
            detail_components.Add(element_id)

# Update the selection in the UI to only include filled regions and lines
filtered_elements = List[DB.ElementId]()
filtered_elements.AddRange(filled_regions)
filtered_elements.AddRange(lines)
uidoc.Selection.SetElementIds(filtered_elements)

# Validate non_component_elements before use
if not non_component_elements:
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

# Copy elements from project to family
if non_component_elements:
    elem_ids = [el.Id for el in non_component_elements]
    elem_ids_col = List[DB.ElementId](elem_ids)

    opts = CopyPasteOptions()

    all_views = FilteredElementCollector(family_doc).OfCategory(BuiltInCategory.OST_Views).ToElements()

    if not all_views:
        print("No views found in the family document.")

    transform = Transform.CreateTranslation(XYZ(-avg_x, -avg_y, -avg_z))
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

    for comp in detail_components:
        if not isinstance(comp, DB.FamilyInstance):
            continue

        symbol = comp.Symbol
        if symbol is None:
            continue

        symbol_name = symbol.Name
        comp_family = symbol.Family
        fam_name = comp_family.Name

        if fam_name not in loaded_comp_families:
            try:
                fam_doc = doc.EditFamily(comp_family)
            except Exception as e:
                continue

            temp_dir = tempfile.gettempdir()
            temp_family_path = os.path.join(temp_dir, fam_name + ".rfa")
            try:
                if os.path.exists(temp_family_path):
                    os.remove(temp_family_path)
                fam_doc.SaveAs(temp_family_path)
                fam_doc.Close(False)
            except Exception as e:
                continue

            new_fam = load_family_into_famdoc(family_doc, temp_family_path)
            if not new_fam:
                continue

            loaded_comp_families[fam_name] = new_fam

        else:
            new_fam = loaded_comp_families[fam_name]

        new_comp_symbol = None
        for fsid in new_fam.GetFamilySymbolIds():
            fs = family_doc.GetElement(fsid)
            if fs and fs.Name == symbol_name:
                new_comp_symbol = fs
                break

        if not new_comp_symbol:
            continue

        if not new_comp_symbol.IsActive:
            new_comp_symbol.Activate()
            family_doc.Regenerate()

        comp_center = comp.get_BoundingBox(current_view).Min + comp.get_BoundingBox(current_view).Max * 0.5
        transformed_point = transform.OfPoint(comp_center)

        try:
            family_doc.FamilyCreate.NewFamilyInstance(transformed_point, new_comp_symbol, DB.Structure.StructuralType.NonStructural)
        except Exception as e:
            continue

t_fam.Commit()

# Save the family
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
        all_elements_to_delete.AddRange(detail_components)

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
