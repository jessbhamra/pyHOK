## pyRevit script to take selected 2d content and convert to detail family. 
## possibly also replace selected with new family automatically once created.
## also allow detail groups to be converted, and replaced where desired.

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
    FamilyCreationOptions,
    ElementTransformUtils,
    SaveAsOptions,
    Transform,
    XYZ,
    Transaction,
    Group,
    Category,
    BoundingBoxXYZ,
    Family,
    FamilySymbol,
)
from pyrevit import revit, DB, forms
import os

# -------------------------------
# User Config
# -------------------------------
FAMILY_TEMPLATE_PATH = r"B://Temp//detail family templates"  # Update as needed

# -------------------------------
# Setup & Validation
# -------------------------------
uidoc = revit.uidoc
doc = revit.doc

selection_ids = uidoc.Selection.GetElementIds()
if not selection_ids:
    forms.alert("No elements selected. Please select detail elements or a detail group.", exitscript=True)

current_view = doc.ActiveView
if current_view.ViewType not in [DB.ViewType.Detail, DB.ViewType.DraftingView]:
    forms.alert("Please run this in a Detail or Drafting view.", exitscript=True)

if not os.path.exists(FAMILY_TEMPLATE_PATH):
    forms.alert("Detail item family template not found. Update FAMILY_TEMPLATE_PATH.", exitscript=True)


# -------------------------------
# Identify Selected Elements
# -------------------------------
selected_elements = [doc.GetElement(eid) for eid in selection_ids]

# Identify if a detail group is selected (we'll assume one detail group or multiple are allowed)
detail_groups = [el for el in selected_elements if isinstance(el, Group) and el.GroupType.Category.Id.IntegerValue == BuiltInCategory.OST_IOSDetailGroups]
non_group_elements = [el for el in selected_elements if not isinstance(el, Group)]

# If detail groups are selected, gather their members
elements_to_process = []
if detail_groups:
    # We'll combine all detail group members and treat them as one set of elements
    # If multiple groups selected, we combine all members. Alternatively, handle one group at a time if desired.
    for grp in detail_groups:
        for member_id in grp.GetMemberIds():
            member_el = doc.GetElement(member_id)
            elements_to_process.append(member_el)
    # If groups are selected, ignore the non-group elements for this run (or merge them if needed)
    # Here we merge them, allowing user to select a group plus some lines. Adjust logic if undesired.
    elements_to_process.extend(non_group_elements)
else:
    # No detail group selected, just use the currently selected 2D elements
    elements_to_process = non_group_elements

if not elements_to_process:
    forms.alert("No valid detail elements found. Please select 2D detail elements or a detail group.", exitscript=True)

# Validate categories for 2D elements
valid_cats = [
    BuiltInCategory.OST_Lines,
    BuiltInCategory.OST_FilledRegion,
    BuiltInCategory.OST_DetailComponents,
    BuiltInCategory.OST_Insulation,
    BuiltInCategory.OST_CLines,
    BuiltInCategory.OST_DetailItems,
    # Groups handled separately
]

filtered_elements = []
for el in elements_to_process:
    if el.Category and el.Category.Id.IntegerValue in [cat.value__ for cat in valid_cats]:
        filtered_elements.append(el)
    # If something doesn't fit, skip it silently or show a message
    # forms.alert(f"Element {el.Id} category {el.Category.Name} not supported")

if not filtered_elements:
    forms.alert("Selected elements are not supported for conversion.", exitscript=True)

# -------------------------------
# Compute a reference point (centroid) for placement
# -------------------------------
# We can compute a simple centroid by averaging the bounding box centers of each element
def get_element_bbox_center(e):
    bbox = e.get_BoundingBox(current_view)
    if bbox:
        center = (bbox.Min + bbox.Max) * 0.5
        return center
    else:
        return XYZ(0,0,0)

centroids = [get_element_bbox_center(el) for el in filtered_elements if get_element_bbox_center(el)]
if centroids:
    avg_x = sum(c.X for c in centroids) / len(centroids)
    avg_y = sum(c.Y for c in centroids) / len(centroids)
    avg_z = sum(c.Z for c in centroids) / len(centroids)
    placement_point = XYZ(avg_x, avg_y, avg_z)
else:
    placement_point = XYZ(0,0,0)


# -------------------------------
# Ask user for family name
# -------------------------------
family_name = forms.ask_for_string(prompt="Enter a name for the new detail family:", default="NewDetailFamily")
if not family_name:
    forms.alert("No family name provided. Operation cancelled.", exitscript=True)

# Ask user for save location
save_path = forms.save_file(file_ext='rfa', prompt_title='Save new detail family', default_name=family_name)
if not save_path:
    forms.alert("No save location selected. Operation cancelled.", exitscript=True)


# -------------------------------
# Create the Family
# -------------------------------
app = doc.Application
family_doc = app.NewFamilyDocument(FAMILY_TEMPLATE_PATH)

t_fam = Transaction(family_doc, "Create Detail Family")
t_fam.Start()

# Copy elements from project to family
elem_ids = [el.Id for el in filtered_elements]
ElementTransformUtils.CopyElements(doc, elem_ids, family_doc, Transform.Identity, None)

t_fam.Commit()

# Save family
save_options = SaveAsOptions()
family_doc.SaveAs(save_path, save_options)
family_doc.Close(False)


# -------------------------------
# Load Family into Project
# -------------------------------
t_load = Transaction(doc, "Load Detail Family")
t_load.Start()
loaded_family = None
res = doc.LoadFamily(save_path, loaded_family)
t_load.Commit()

if not res:
    forms.alert("Failed to load the newly created family into the project.")
    raise Exception("Family load failed")

# Find the loaded family by name
loaded_fam = None
for f in FilteredElementCollector(doc).OfClass(Family):
    if f.Name == family_name:
        loaded_fam = f
        break

if not loaded_fam:
    forms.alert("Cannot find loaded family in the project.")
    raise Exception("Family not found after load.")

# Get a family symbol
fam_sym = None
for fsid in loaded_fam.GetFamilySymbolIds():
    fam_sym = doc.GetElement(fsid)
    if fam_sym:
        break

if fam_sym and not fam_sym.IsActive:
    t_activate = Transaction(doc, "Activate Family Symbol")
    t_activate.Start()
    fam_sym.Activate()
    t_activate.Commit()


# -------------------------------
# Optionally Replace Original With Family Instance
# -------------------------------
replace = forms.alert("Replace original selected elements/group with the new family instance?", yes=True, no=True)
if replace:
    t_replace = Transaction(doc, "Replace with Family Instance")
    t_replace.Start()

    # Place an instance at the centroid
    new_instance = doc.Create.NewFamilyInstance(placement_point, fam_sym, current_view)
    
    # Delete original elements and detail groups if any
    for el in elements_to_process:
        try:
            doc.Delete(el.Id)
        except:
            pass

    t_replace.Commit()


forms.alert("Detail family created successfully!")
