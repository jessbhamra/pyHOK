"""Replace family with instance length parameter with a line-based family"""
__title__ = 'Replace Family'
__author__ = 'HOK'

# choose which source families (detail component families) to replace.
# pick a target line-based detail component type.
# - Replaces all instances of the chosen families in the entire project with line-based ones.
# - Attempts to maintain approximate length and orientation from bounding boxes.

import sys
import math
from pyrevit import revit, DB, forms

doc = revit.doc

# Get all FamilySymbols that are detail components.
all_symbols = []
for fs in DB.FilteredElementCollector(doc)\
             .OfClass(DB.FamilySymbol)\
             .WhereElementIsElementType()\
             .ToElements():
    # Check if symbol category is Detail Components
    if fs.Category and fs.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_DetailComponents):
        all_symbols.append(fs)

if not all_symbols:
    forms.alert("No detail component family symbols found in the project.", exitscript=True)

# Extract unique families from these symbols
all_families = []
for fs in all_symbols:
    fam = fs.Family
    if fam not in all_families:
        all_families.append(fam)

if not all_families:
    forms.alert("No detail component families found in the project.", exitscript=True)

# Ask user to choose source families (multi-select)
source_families = forms.SelectFromList(
    "Select Source Detail Families to Replace",
    [f.Name for f in all_families],
    multiselect=True
)

if not source_families:
    forms.alert("No source family selected. Exiting.", exitscript=True)

# Now ask user to pick target symbol from all_symbols
target_symbol_label_map = {}
for fs in all_symbols:
    label = fs.Family.Name + " : " + fs.Name
    target_symbol_label_map[label] = fs

target_symbol_choice = forms.SelectFromList(
    "Select Target Line-Based Detail Family Type",
    sorted(target_symbol_label_map.keys())
)

if not target_symbol_choice:
    forms.alert("No target type selected. Exiting.", exitscript=True)

selected_target_symbol = target_symbol_label_map[target_symbol_choice]

# Ensure target symbol is active
if not selected_target_symbol.IsActive:
    t = DB.Transaction(doc, "Activate Target Symbol")
    t.Start()
    selected_target_symbol.Activate()
    doc.Regenerate()
    t.Commit()

# Find all instances of the chosen source families
collector = DB.FilteredElementCollector(doc)\
               .OfCategory(DB.BuiltInCategory.OST_DetailComponents)\
               .WhereElementIsNotElementType()

source_family_names = source_families
instances_to_replace = []
for inst in collector:
    if isinstance(inst, DB.FamilyInstance):
        fam_name = inst.Symbol.Family.Name
        if fam_name in source_family_names:
            instances_to_replace.append(inst)

if not instances_to_replace:
    forms.alert("No instances of the selected source families found in the project.", exitscript=True)

t = DB.Transaction(doc, "Replace Detail Components with Line-Hosted Components")
t.Start()

for original_instance in instances_to_replace:
    view_id = original_instance.OwnerViewId
    view = doc.GetElement(view_id)
    # We only want to replace in detail or drafting views
    if view is None or view.ViewType not in [DB.ViewType.Detail, DB.ViewType.Drafting]:
        # Skip if not in a detail/drafting view
        continue

    bbox = original_instance.get_BoundingBox(None)
    if bbox is None:
        continue

    # Determine orientation and length from bounding box
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

    # Delete original
    doc.Delete(original_instance.Id)

t.Commit()

forms.alert("Replacement completed.")
