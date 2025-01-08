# -*- coding: utf-8 -*-
"""
Replace Families with Line-Based Detail Components
Use this tool to swap out one or more detail component families in all drafting/detail views
with a selected line-based detail family. 
It attempts to retain each element's approximate length/orientation using bounding boxes.
"""

import sys
import math
from pyrevit import revit, DB, forms

doc = revit.doc

# -------------------------------------------------------------
# 1) COLLECT ALL DETAIL FAMILY SYMBOLS
# -------------------------------------------------------------
all_symbols = []
for fs in DB.FilteredElementCollector(doc)\
             .OfClass(DB.FamilySymbol)\
             .WhereElementIsElementType()\
             .ToElements():
    if fs.Category and fs.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_DetailComponents):
        all_symbols.append(fs)

if not all_symbols:
    forms.alert("No detail component family symbols found.", exitscript=True)

# Build a set of unique families
unique_fams = set()
for fs in all_symbols:
    if fs.Family:
        unique_fams.add(fs.Family)

if not unique_fams:
    forms.alert("No detail component families found.", exitscript=True)

# -------------------------------------------------------------
# 2) PROMPT USER FOR SOURCE FAMILIES (BY NAME, MULTI-SELECT)
# -------------------------------------------------------------
family_name_list = [fam.Name for fam in unique_fams if fam]
source_families = forms.SelectFromList.show(
    family_name_list, 
    "Select Source Families to Replace", 
    500, 400,
    button_name="Select",
    multiselect=True
)

if not source_families:
    forms.alert("No source families selected.", exitscript=True)

# -------------------------------------------------------------
# 3) PROMPT USER FOR TARGET SYMBOL (SINGLE-SELECT)
# -------------------------------------------------------------


print("DEBUG: Found {} detail symbols in the project.".format(len(all_symbols)))

symbol_label_map = {}
for fs in all_symbols:
    # Debug prints to see what's happening
    print("DEBUG: Checking symbol ID={} | Family=? | SymbolName=?".format(fs.Id))
    
    # Safely check Family first
    fam_obj = getattr(fs, "Family", None)
    if not fam_obj:
        print("     --> Skipping: No Family object on symbol.")
        continue
    
    fam_name = getattr(fam_obj, "Name", None)
    sym_name = getattr(fs, "Name", None)
    
    if not fam_name:
        print("     --> Skipping: Family has no valid Name.")
        continue
    if not sym_name:
        print("     --> Skipping: Symbol has no valid Name.")
        continue

    # Now we know we have valid names
    label = fam_name + " : " + sym_name
    symbol_label_map[label] = fs
    print("     --> ADDED: '{}'\n".format(label))

print("DEBUG: Created {} entries in symbol_label_map.".format(len(symbol_label_map)))

# Now build the sorted label list for the dialog
sorted_labels = sorted(symbol_label_map.keys())
print("DEBUG: Sorted labels = {}".format(sorted_labels))

target_symbol_choice = forms.SelectFromList.show(
    sorted_labels,
    "Select Target Line-Based Detail Type",
    500, 300,
    button_name="Select Target",
    multiselect=False
)


if not target_symbol_choice:
    forms.alert("No target type selected.", exitscript=True)

selected_target_symbol = symbol_label_map[target_symbol_choice]

# Activate target symbol if not already
if not selected_target_symbol.IsActive:
    with DB.Transaction(doc, "Activate Target Symbol"):
        selected_target_symbol.Activate()
        doc.Regenerate()

# -------------------------------------------------------------
# 4) COLLECT INSTANCES TO REPLACE
# -------------------------------------------------------------
collector = DB.FilteredElementCollector(doc)\
              .OfCategory(DB.BuiltInCategory.OST_DetailComponents)\
              .WhereElementIsNotElementType()

instances_to_replace = []
for inst in collector:
    if isinstance(inst, DB.FamilyInstance):
        sym = inst.Symbol
        if not sym:
            continue
        fam = sym.Family
        if not fam:
            continue
        
        fam_name = fam.Name  # Safely call .Name after confirming 'fam' is not None
        if fam_name in source_families:
            instances_to_replace.append(inst)

if not instances_to_replace:
    forms.alert("No instances of the selected source families found in the project.", exitscript=True)

# -------------------------------------------------------------
# 5) REPLACE VIA BOUNDING BOX
# -------------------------------------------------------------
t = DB.Transaction(doc, "Replace Detail Components")
t.Start()

for original_instance in instances_to_replace:
    view_id = original_instance.OwnerViewId
    view = doc.GetElement(view_id)
    # We only want to do this in Detail or Drafting views
    if not view or view.ViewType not in [DB.ViewType.Detail, DB.ViewType.Drafting]:
        continue

    bbox = original_instance.get_BoundingBox(None)
    if not bbox:
        continue

    # Approximate orientation + length from bounding box
    x_length = bbox.Max.X - bbox.Min.X
    y_length = bbox.Max.Y - bbox.Min.Y

    if abs(x_length) >= abs(y_length):
        length = abs(x_length)
        angle = 0.0
        if x_length < 0:
            angle = math.pi
    else:
        length = abs(y_length)
        angle = math.pi / 2.0
        if y_length < 0:
            angle = -math.pi / 2.0

    midX = (bbox.Min.X + bbox.Max.X) / 2.0
    midY = (bbox.Min.Y + bbox.Max.Y) / 2.0
    midZ = (bbox.Min.Z + bbox.Max.Z) / 2.0

    start_point = DB.XYZ(midX - (length / 2.0) * math.cos(angle),
                         midY - (length / 2.0) * math.sin(angle),
                         midZ)
    end_point = DB.XYZ(midX + (length / 2.0) * math.cos(angle),
                       midY + (length / 2.0) * math.sin(angle),
                       midZ)

    line = DB.Line.CreateBound(start_point, end_point)
    new_instance = doc.Create.NewFamilyInstance(line, selected_target_symbol, view)

    doc.Delete(original_instance.Id)

t.Commit()
forms.alert("Replacement completed.")
