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

# Collect all detail component families:
all_families = []
for fs_id in doc.GetFamilySymbolIds():
    fs = doc.GetElement(fs_id)
    if fs is not None and fs.Category is not None:
        if fs.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_DetailComponents):
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

# Filter family symbols to line-based detail families to choose from as target
# We'll just show all detail family types and let the user pick.
# Ideally, the user chooses a line-based one.
all_symbols = []
for fs_id in doc.GetFamilySymbolIds():
    fs = doc.GetElement(fs_id)
    if fs is not None and fs.Category is not None:
        if fs.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_DetailComponents):
            all_symbols.append(fs)

if not all_symbols:
    forms.alert("No detail component family symbols found.", exitscript=True)

target_symbol = forms.SelectFromList("Select Target Line-Based Detail Family Type", [fs.Family.Name + " : " + fs.Name for fs in all_symbols])
if not target_symbol:
    forms.alert("No target type selected. Exiting.", exitscript=True)

# Parse the selected target symbol
selected_target_symbol = None
for fs in all_symbols:
    label = fs.Family.Name + " : " + fs.Name
    if label == target_symbol:
        selected_target_symbol = fs
        break

if not selected_target_symbol:
    forms.alert("Unable to find the selected target symbol in the document.", exitscript=True)

# Ensure target symbol is active
if not selected_target_symbol.IsActive:
    t = DB.Transaction(doc, "Activate Target Symbol")
    t.Start()
    selected_target_symbol.Activate()
    doc.Regenerate()
    t.Commit()

# Now we have the source families and the target symbol.
# Find all instances of these source families in the project.
collector = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_DetailComponents).WhereElementIsNotElementType()

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
    # Each detail item belongs to a view, we must recreate in that view.
    view_id = original_instance.OwnerViewId
    view = doc.GetElement(view_id)
    if view is None or view.ViewType not in [DB.ViewType.Detail, DB.ViewType.Drafting]:
        # Skip if not in a detail/drafting view (just in case)
        continue

    bbox = original_instance.get_BoundingBox(None)
    if bbox is None:
        continue

    x_length = bbox.Max.X - bbox.Min.X
    y_length = bbox.Max.Y - bbox.Min.Y

    # Determine orientation and length
    # Pick the longest dimension as the length direction
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

    # Compute start and end points
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
