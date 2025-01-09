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
from Autodesk.Revit import DB
from Autodesk.Revit.DB import DetailElementOrderUtils
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
# 3) PROMPT USER FOR TARGET SYMBOL (SINGLE-SELECT)
# -------------------------------------------------------------
def get_target_family_symbol():
    # Collect all detail item family symbols

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
        #   print(fam_name, ":", sym_name,":", fam_obj.FamilyPlacementType)  # Debugging
    
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
          #  print("DEBUG: Instance ID={} has no Symbol.".format(inst.Id))
            continue
        fam = sym.Family
        if not fam:
          #  print("DEBUG: Instance ID={} has Symbol with no Family.".format(inst.Id))
            continue
        
        fam_name = fam.Name
        if not fam_name:
            #print("DEBUG: Instance ID={} has Symbol's Family with no Name.".format(inst.Id))
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

# Sort by element ID, so you are replacing in ascending creation order
instances_to_replace.sort(key=lambda x: x.Id.IntegerValue)

# -------------------------------------------------------------
# 5) PROMPT USER FOR OFFSET
# -------------------------------------------------------------
# user_offset_str = forms.ask_for_string(
#     prompt="Enter additional offset (+/-). E.g. '1.5' or '-1.0':",
#     default="0.0"
# )

# if user_offset_str is None:
#     forms.alert("No offset supplied. Exiting.", exitscript=True)

user_offset_str="-37/256"

# Ask user if they want to invert offset direction
# flip_direction = forms.alert(
#     "Flip offset direction?\nPress 'Yes' to invert direction, or 'No' to keep default.",
#     yes=True,
#     no=True
# )

flip_direction = True

def parse_inch_fraction(s):
#    Parse a string representing inches in fractional or decimal format.
#    Examples of valid inputs:
#      "1/2"     => 0.5
#    Returns a float (in inches).
#    If parsing fails, returns 0.0

    s = s.strip()
    whole = 0.0
    fraction = 0.0

    # Split on space to check if there's "whole part" + "fraction part"
    parts = s.split()
    try:
        if len(parts) == 2:
            # E.g. "3 1/4"
            # First part (whole number or decimal)
            whole_str = parts[0]
            whole = float(whole_str)

            # Second part (fraction or decimal)
            frac_str = parts[1]
            if "/" in frac_str:
                # e.g. "1/4"
                num_str, den_str = frac_str.split("/")
                fraction = float(num_str) / float(den_str)
            else:
                # Might just be decimal => "0.25"
                fraction = float(frac_str)

        else:
            # Single chunk => either "1/2", "3.75", "4"
            if "/" in s:
                # fraction only
                num_str, den_str = s.split("/")
                fraction = float(num_str) / float(den_str)
            else:
                # decimal or integer
                whole = float(s)

    except Exception:
        # If any parsing error, default to 0.0
        return 0.0

    return whole + fraction

parsed_inches = (parse_inch_fraction(user_offset_str)/12)
# -------------------------------------------------------------
# 6) MAP ORIGINAL ELEMENTS TO THEIR VIEWS
# -------------------------------------------------------------
original_to_view = {} 
 # Mapping of original element ID -> hosting view ID

for original_inst in instances_to_replace:
    view_id = original_inst.OwnerViewId
    if view_id and view_id != DB.ElementId.InvalidElementId:
        original_to_view[original_inst.Id] = view_id

# Debug: Print mapping
# for original_id, view_id in original_to_view.items():
#    print("DEBUG: Original Element ID {0} is hosted in View ID {1}".format(original_id, view_id))

# Dictionary to map original elements to their hosting views

replaced_elements = {}
# -------------------------------------------------------------
# 7) REPLACE USING BOUNDING BOX APPROXIMATION
# -------------------------------------------------------------
with DB.Transaction(doc, "Replace with offset") as t:
    t.Start()
    replaced_elements = {}  # Mapping of original ID -> new ID
    for original_inst in instances_to_replace:
        view_id = original_inst.OwnerViewId
        view = doc.GetElement(view_id)
        if not view or view.ViewType not in [DB.ViewType.Detail, DB.ViewType.DraftingView]:
            continue

        bbox = original_inst.get_BoundingBox(view)
        if not bbox:
            continue

        dx = bbox.Max.X - bbox.Min.X
        dy = bbox.Max.Y - bbox.Min.Y

        if abs(dx) >= abs(dy):
            length = abs(dx)
            thickness = abs(dy)
            angle = 0.0
            if dx < 0:
                angle = math.pi
            offset_sign = 1.0
        else:
            length = abs(dy)
            thickness = abs(dx)
            angle = math.pi / 2.0
            if dy < 0:
                angle = -math.pi / 2.0
            offset_sign = -1.0

        if flip_direction:
            offset_sign *= -1.0

        midX = (bbox.Min.X + bbox.Max.X) / 2.0
        midY = (bbox.Min.Y + bbox.Max.Y) / 2.0
        midZ = (bbox.Min.Z + bbox.Max.Z) / 2.0

        half_thickness = thickness / 2.0
        net_offset = half_thickness + parsed_inches

        if abs(dx) >= abs(dy):
            midY += offset_sign * net_offset
        else:
            midX += offset_sign * net_offset

        start_pt = DB.XYZ(
            midX - (length / 2.0) * math.cos(angle),
            midY - (length / 2.0) * math.sin(angle),
            midZ
        )
        end_pt = DB.XYZ(
            midX + (length / 2.0) * math.cos(angle),
            midY + (length / 2.0) * math.sin(angle),
            midZ
        )

        line = DB.Line.CreateBound(start_pt, end_pt)

        try:
            new_inst = doc.Create.NewFamilyInstance(line, selected_target_symbol, view)
            replaced_elements[original_inst.Id] = new_inst.Id  # Track mapping
            doc.Delete(original_inst.Id)

        except Exception as e:
            print("ERROR: Replacing {0} failed: {1}".format(original_inst.Id, e))

    t.Commit()

# -------------------------------------------------------------
# 8) ADJUST DRAW ORDER TO MOVE NEW ELEMENTS TO THE BACK
# -------------------------------------------------------------

# Adjust draw order for replaced elements
with DB.Transaction(doc, "Adjust Draw Order") as t:
    t.Start()
    for original_id, new_id in replaced_elements.items():
        new_element = doc.GetElement(new_id)
        view_id = new_element.OwnerViewId
        view = doc.GetElement(view_id)

        # Ensure the view is valid
        if view and view.ViewType in [DB.ViewType.Detail, DB.ViewType.DraftingView]:
            try:
                # Move the element to the back
                DetailElementOrderUtils.SendToBack(doc, view, new_element.Id)
            except Exception as e:
                print("ERROR: Adjusting draw order for {} failed: {}".format(new_id.IntegerValue, e))
    t.Commit()
