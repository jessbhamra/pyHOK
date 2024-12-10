# -*- coding: utf-8 -*-
"""
pyRevit script:
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

# -------------------------------
# User Config
# -------------------------------
FAMILY_TEMPLATE_PATH = r"B://Temp//detail family templates/DetailItem_HOK_I.rft"  # **Update this path as needed**

# -------------------------------
# Setup & Validation
# -------------------------------
uidoc = revit.uidoc
doc = revit.doc

selection_ids = uidoc.Selection.GetElementIds()
if not selection_ids:
    forms.alert("No elements selected. Please select detail elements or a detail group.", exitscript=True)

current_view = doc.ActiveView
if current_view.ViewType not in [ViewType.Detail, ViewType.DraftingView]:
    forms.alert("Please run this script in a Detail or Drafting view.", exitscript=True)

if not os.path.exists(FAMILY_TEMPLATE_PATH):
    forms.alert("Detail item family template not found. Please update FAMILY_TEMPLATE_PATH in the script.", exitscript=True)

# -------------------------------
# Identify Selected Elements
# -------------------------------
selected_elements = [doc.GetElement(eid) for eid in selection_ids]

# Identify if a detail group is selected
detail_groups = [el for el in selected_elements if isinstance(el, Group) and el.GroupType.Category.Id.IntegerValue == BuiltInCategory.OST_IOSDetailGroups]
non_group_elements = [el for el in selected_elements if not isinstance(el, Group)]

# Gather elements to process
elements_to_process = []
if detail_groups:
    for grp in detail_groups:
        for member_id in grp.GetMemberIds():
            member_el = doc.GetElement(member_id)
            elements_to_process.append(member_el)
    elements_to_process.extend(non_group_elements)  # Optionally include non-group elements
else:
    elements_to_process = non_group_elements

if not elements_to_process:
    forms.alert("No valid detail elements found. Please select 2D detail elements or a detail group.", exitscript=True)

# Validate categories for 2D elements
valid_cats = [
    BuiltInCategory.OST_Lines,
    BuiltInCategory.OST_FilledRegion,
    BuiltInCategory.OST_DetailComponents,
#    BuiltInCategory.OST_InsulationLines,
#    BuiltInCategory.OST_CLines,
#    BuiltInCategory.OST_ReferenceLines,
]

filtered_elements = []
unsupported_elements = []
for el in elements_to_process:
    if el.Category and el.Category.Id.IntegerValue in [cat.value__ for cat in valid_cats]:
        filtered_elements.append(el)
    else:
        unsupported_elements.append(el)

if not filtered_elements:
    forms.alert("Selected elements are not supported for conversion.", exitscript=True)

# -------------------------------
# Compute a Reference Point (Centroid) for Placement
# -------------------------------
def get_element_bbox_center(e):
    bbox = e.get_BoundingBox(current_view)
    if bbox:
        center = (bbox.Min + bbox.Max) * 0.5
        return center
    else:
        return None

centroids = [get_element_bbox_center(el) for el in filtered_elements]
centroids = [c for c in centroids if c is not None]
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

# Removed 'prompt_title' from save_file
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
#elem_ids = [el.Id for el in filtered_elements]
#elem_ids = [el.Id for el in filtered_elements]

# Convert Python list to .NET List[ElementId]
#elem_ids_col = List[DB.ElementId]()
#for eid in elem_ids:
#    elem_ids_col.Add(eid)
#    print(eid)

elem_ids = [el.Id for el in filtered_elements]
elem_ids_col = List[DB.ElementId](elem_ids)

opts = CopyPasteOptions()

#  copy from current_view in project doc to family_doc.ActiveView
try:
    ElementTransformUtils.CopyElements(current_view, elem_ids_col, family_doc.ActiveView, Transform.Identity, opts)
except Exception as e:
    t_fam.RollBack()
    family_doc.Close(False)
    error_message = "Failed to copy elements to the family document. Error: {}".format(e)
    forms.alert(error_message, exitscript=True)

t_fam.Commit()

# Save the family
save_options = SaveAsOptions()
save_options.OverwriteExistingFile = True  # Allow overwriting if the file already exists

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
loaded_family = DB.Family()
try:
    res = doc.LoadFamily(save_path, loaded_family)
except Exception as e:
    t_load.RollBack()
    error_message = "Failed to load the family into the project. Error: {}".format(e)
    forms.alert(error_message, exitscript=True)
    raise

t_load.Commit()

if not res:
    forms.alert("Failed to load the newly created family into the project.", exitscript=True)

# Find the loaded family by name
loaded_fam = None
families = FilteredElementCollector(doc).OfClass(Family).ToElements()
for f in families:
    if f.Name == family_name:
        loaded_fam = f
        break

if not loaded_fam:
    forms.alert("Cannot find the loaded family in the project.", exitscript=True)

# Get a family symbol (type)
fam_sym = None
for fsid in loaded_fam.GetFamilySymbolIds():
    fam_sym = doc.GetElement(fsid)
    if fam_sym:
        break

if not fam_sym:
    forms.alert("The loaded family has no available types.", exitscript=True)
    raise Exception("No family symbols found.")

# Activate the family symbol if not already active
if not fam_sym.IsActive:
    t_activate = Transaction(doc, "Activate Family Symbol")
    t_activate.Start()
    fam_sym.Activate()
    t_activate.Commit()

# -------------------------------
# Replace Original Elements/Groups with Family Instance
# -------------------------------
replace = forms.alert("Do you want to replace the original selected elements/groups with the new family instance?", 
                     title="Replace Elements?", 
                     warning=True, 
                     yes=True, 
                     no=True)

if replace:
    t_replace = Transaction(doc, "Replace with Family Instance")
    t_replace.Start()

    try:
        # Place an instance at the centroid
        new_instance = doc.Create.NewFamilyInstance(placement_point, fam_sym, current_view)

        # Delete original elements and detail groups
        for el in elements_to_process:
            try:
                doc.Delete(el.Id)
            except Exception as del_e:
                delete_error = "Failed to delete element ID {}. Error: {}".format(el.Id, del_e)
                forms.alert(delete_error, exitscript=True)
    except Exception as e:
        t_replace.RollBack()
        replace_error = "Failed to place the family instance or delete original elements. Error: {}".format(e)
        forms.alert(replace_error, exitscript=True)
        raise

    t_replace.Commit()

forms.alert("Detail family created successfully!", title="Success")
