"""Replace family with instance length parameter with a line-based family"""
__title__ = 'Replace Family'
__author__ = 'HOK'

# choose which source families (detail component families) to replace.
# pick a target line-based detail component type.
# - Replaces all instances of the chosen families in the entire project with line-based ones.
# - Attempts to maintain approximate length and orientation from bounding boxes.
# no f-strings for compatibility
# No f-strings used to maintain compatibility
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
    forms.alert("No detail component family symbols found in the project.", exitscript=True)

# Build a list of unique families from the symbols
all_families = []
for fs in all_symbols:
    fam = fs.Family
    if fam not in all_families:
        all_families.append(fam)

if not all_families:
    forms.alert("No detail component families found in the project.", exitscript=True)

# -------------------------------------------------------------
# 2) PROMPT USER FOR SOURCE FAMILIES (MULTI-SELECT)
#    Using SelectFromList.show(context, title, width, height, **kwargs)
# -------------------------------------------------------------
source_families = forms.SelectFromList.show(
    [f.Name for f in all_families],              # context (list of strings)
    "Select Source Families to Replace",         # title
    500,                                         # width
    400,                                         # height
    button_name="Select Sources",                # **kwarg
    multiselect=True                             # **kwarg
)

if not source_families:
    forms.alert("No source families selected. Exiting.", exitscript=True)

# -------------------------------------------------------------
# 3) PROMPT USER FOR TARGET SYMBOL (SINGLE-SELECT)
# -------------------------------------------------------------
symbol_label_map = {}
for fs in all_symbols:
    label = fs.Family.Name + " : " + fs.Name
    symbol_label_map[label] = fs

sorted_labels = sorted(symbol_label_map.keys())

target_symbol_choice = forms.SelectFromList.show(
    sorted_labels,                               # context
    "Select Target Line-Based Detail Type",      # title
    500,                                         # width
    300,                                         # height
    button_name="Select Target",                 # **kwarg
    multiselect=False                            # **kwarg
)

if not target_symbol_choice:
    forms.alert("No target type selected. Exiting.", exitscript=True)

selected_target_symbol = symbol_label_map[target_symbol_choice]

# Ensure the target symbol is active
if not selected_target_symbol.IsActive:
    t_activate = DB.Transaction(doc, "Activate Target Symbol")
    t_activate.Start()
    selected_target_symbol.Activate()
    doc.Regenerate()
    t_activate.Commit()

# -------------------------------------------------------------
# 4) FIND & REPLACE ALL INSTANCES OF SELECTED SOURCE FAMILIES
# -------------------------------------------------------------
collector = DB.FilteredElementCollector(doc)\
               .OfCategory(DB.BuiltInCategory.OST_DetailComponents)\
               .WhereElementIsNotElementType()

instances_to_replace = []
for inst in collector:
    if isinstance(inst, DB.FamilyInstance):
        fam_name = inst.Symbol.Family.Name
        if fam_name in source_families:
            instances_to_replace.append(inst)

if not instances_to_replace:
    forms.alert("No instances of the selected source families found in the project.", exitscript=True)

# -------------------------------------------------------------
# 5) REPLACE VIA BOUNDING BOX (APPROXIMATE LENGTH & ORIENTATION)
# -------------------------------------------------------------
t_replace = DB.Transaction(doc, "Replace Detail Components")
t_replace.Start()

for original_instance in instances_to_replace:
    view_id = original_instance.OwnerViewId
    view = doc.GetElement(view_id)
    # We only want to do this in Detail or Drafting views
    if view is None or view.ViewType not in [DB.ViewType.Detail, DB.ViewType.Drafting]:
        continue

    bbox = original_instance.get_BoundingBox(None)
    if bbox is None:
        continue

    x_length = bbox.Max.X - bbox.Min.X
    y_length = bbox.Max.Y - bbox.Min.Y

    # Choose the longer dimension as the "length" direction
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

t_replace.Commit()

forms.alert("Replacement completed.")
