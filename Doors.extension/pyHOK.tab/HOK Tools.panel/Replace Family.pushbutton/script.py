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
# 3) CHECK IF ANY SELECTED FAMILY IS LINE-BASED
#     (Family.FamilyPlacementType == FamilyPlacementType.CurveBased)
# -------------------------------------------------------------
is_line_based_in_selection = False
for fam in unique_fams:
    if fam.Name in source_families:
        # If it's recognized as line-based (CurveBased)
        if fam.FamilyPlacementType == DB.FamilyPlacementType.CurveBased:
            is_line_based_in_selection = True
            break
# -------------------------------------------------------------
# 4) PROMPT USER FOR TARGET SYMBOL (SINGLE-SELECT)
# -------------------------------------------------------------
def get_target_family_symbol():
    # Collect all detail item family symbols
 #   collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_DetailComponents)
 #    collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_DetailComponents)
  
    #symbol_label_map = {}
    # for fs in collector:
    #     fam_obj = getattr(fs, "Family", None)
    #     if not fam_obj or fam_obj.FamilyPlacementType != DB.FamilyPlacementType.CurveBased:
    #         continue
    #     label = fam_obj.Name + " : " + fs.Name
    #     symbol_label_map[label] = fs
    collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_DetailComponents)

    symbol_label_map = {}
    for fs in collector:
        fam_obj = fs.Family  # Directly access Family
        if not fam_obj:
            continue
    
    # Use get_Parameter to safely extract the name
        fam_name = fs.FamilyName
        sym_name = fs.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
    
        if fam_name and sym_name:
            fam_name = fam_name
            sym_name = sym_name.AsString()
            print(fam_name, ":", sym_name,":", fam_obj.FamilyPlacementType)  # Debugging
    
            if fam_obj.FamilyPlacementType == DB.FamilyPlacementType.CurveBasedDetail:
                label = fam_name + " : " + sym_name
                symbol_label_map[label] = fs


    sorted_labels = sorted(symbol_label_map.keys())
    
    if not sorted_labels:
        forms.alert("No line-hosted detail families found.", exitscript=True)
    
    target_symbol_choice = forms.SelectFromList.show(
        sorted_labels,
        "Select Target Detail Family Type",
        500,
        300,
        button_name="Select Target",
        multiselect=False
    )
    
    if not target_symbol_choice:
        forms.alert("No target type selected. Exiting.", exitscript=True)

    selected_target_symbol = symbol_label_map[target_symbol_choice]

    if not selected_target_symbol.IsActive:
        with DB.Transaction(doc, "Activate Target Symbol"):
            selected_target_symbol.Activate()
            doc.Regenerate()
    
    return selected_target_symbol

selected_target_symbol = get_target_family_symbol()

# -------------------------------------------------------------
# 5) COLLECT INSTANCES TO REPLACE
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
        
        fam_name = fam.Name
        if fam_name in source_families:
            instances_to_replace.append(inst)

if not instances_to_replace:
    forms.alert("No instances of the selected source families found in the project.", exitscript=True)

# -------------------------------------------------------------
# 6) REPLACE VIA BOUNDING BOX
# -------------------------------------------------------------
t = DB.Transaction(doc, "Replace Detail Components")
t.Start()

for original_instance in instances_to_replace:
    view_id = original_instance.OwnerViewId
    view = doc.GetElement(view_id)
    # We only want to do this in Detail or Drafting views
    if not view or view.ViewType not in [DB.ViewType.Detail, DB.ViewType.DraftingView]:
        continue

    bbox = original_instance.get_BoundingBox(None)
    if not bbox:
        continue

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
print ()
