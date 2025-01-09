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

print("DEBUG: Source Families Selected: {}".format(source_families))

# Normalize source family names for case-insensitive comparison
source_families_normalized = [s.strip().lower() for s in source_families]
# -------------------------------------------------------------
# 3) CHECK IF ANY SELECTED FAMILY IS LINE-BASED
#     (Family.FamilyPlacementType == FamilyPlacementType.CurveBased)
# -------------------------------------------------------------
# is_line_based_in_selection = False
# for fam in unique_fams:
#     if fam.Name in source_families:
#         # If it's recognized as line-based (CurveBased)
#         if fam.FamilyPlacementType == DB.FamilyPlacementType.CurveBased:
#             is_line_based_in_selection = True
#             break
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
          #  print("DEBUG: Instance ID={} has no Symbol.".format(inst.Id))
            continue
        fam = sym.Family
        if not fam:
          #  print("DEBUG: Instance ID={} has Symbol with no Family.".format(inst.Id))
            continue
        
        fam_name = fam.Name
        if not fam_name:
            print("DEBUG: Instance ID={} has Symbol's Family with no Name.".format(inst.Id))
            continue
        
        #print("DEBUG: Instance ID={} has Family Name='{}'.".format(inst.Id, fam_name))
        fam_name_normalized = fam_name.strip().lower()
        if fam_name_normalized in source_families_normalized:
           # print("DEBUG: Instance ID={} matches source family '{}'.".format(inst.Id, fam_name))
            instances_to_replace.append(inst)
      #  else:
            #print("DEBUG: Instance ID={} does not match any source family.".format(inst.Id, fam_name))

print("DEBUG: Total instances to replace: {}".format(len(instances_to_replace)))

if not instances_to_replace:
    forms.alert("No instances of the selected source families found in the project.", exitscript=True)

# -------------------------------------------------------------
# 4) Replace Using Bounding Box Approximation
# -------------------------------------------------------------
with DB.Transaction(doc, "Replace View-Hosted Families w/ Line-Based") as t:
    t.Start()

    for original_inst in instances_to_replace:
        view_id = original_inst.OwnerViewId
        view = doc.GetElement(view_id)

        # 4a) Get bounding box in that view
        bbox = original_inst.get_BoundingBox(view)
        if not bbox:
            # Skip if no bounding box
            continue

        # 4b) Approximate orientation & length from bounding box
        dx = bbox.Max.X - bbox.Min.X
        dy = bbox.Max.Y - bbox.Min.Y

        if abs(dx) >= abs(dy):
            length = abs(dx)
            angle = 0.0
            if dx < 0:
                angle = math.pi
        else:
            length = abs(dy)
            angle = math.pi / 2.0
            if dy < 0:
                angle = -math.pi / 2.0

        # 4c) Compute the bounding box center
        midX = (bbox.Min.X + bbox.Max.X) / 2.0
        midY = (bbox.Min.Y + bbox.Max.Y) / 2.0
        midZ = (bbox.Min.Z + bbox.Max.Z) / 2.0

        # Start + End points for the line
        start_pt = DB.XYZ(midX - (length / 2.0) * math.cos(angle),
                          midY - (length / 2.0) * math.sin(angle),
                          midZ)
        end_pt = DB.XYZ(midX + (length / 2.0) * math.cos(angle),
                        midY + (length / 2.0) * math.sin(angle),
                        midZ)

        line = DB.Line.CreateBound(start_pt, end_pt)

        # 4d) Create the new line-based instance
        try:
            new_inst = doc.Create.NewFamilyInstance(line, selected_target_symbol, view)
            # 4e) Delete the original
            doc.Delete(original_inst.Id)
        except Exception as e:
            print("ERROR: Replacing instance {} failed: {}".format(original_inst.Id, e))

    t.Commit()

forms.alert("Replacement complete.")