"""Replace family with instance length parameter with a line-based family"""
__title__ = 'Replace Family'
__author__ = 'HOK'

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    FamilySymbol,
    FamilyInstance,
    BuiltInCategory,
    Transaction,
    Line,
    XYZ,
    FamilyPlacementType,
    LocationPoint
)
from pyrevit import revit, forms, script

# Get the current Revit document
doc = revit.doc

# Collect all detail component family symbols in the document
detail_component_symbols = FilteredElementCollector(doc)\
    .OfClass(FamilySymbol)\
    .OfCategory(BuiltInCategory.OST_DetailComponents)\
    .ToElements()

# Create a dictionary of detail component family names and their symbols
detail_family_options = {fs.FamilyName: fs for fs in detail_component_symbols}

# Prompt the user to select the detail component family to replace
selected_detail_family_name = forms.SelectFromList.show(
    sorted(detail_family_options.keys()),
    title='Select Detail Component Family to Replace',
    button_name='Select'
)

# Exit the script if no family is selected
if not selected_detail_family_name:
    script.exit()

detail_family_symbol = detail_family_options[selected_detail_family_name]

# Collect all line-based family symbols in the document
line_based_symbols = FilteredElementCollector(doc)\
    .OfClass(FamilySymbol)\
    .WhereElementIsElementType()\
    .ToElements()

# Filter to only include line-based families
line_based_symbols = [
    fs for fs in line_based_symbols
    if fs.Family.FamilyPlacementType == FamilyPlacementType.Linear
]

# Create a dictionary of line-based family names and their symbols
line_family_options = {fs.FamilyName: fs for fs in line_based_symbols}

# Prompt the user to select the line-based family to use for replacement
selected_line_family_name = forms.SelectFromList.show(
    sorted(line_family_options.keys()),
    title='Select Line-based Family to Replace With',
    button_name='Select'
)

# Exit the script if no family is selected
if not selected_line_family_name:
    script.exit()

line_family_symbol = line_family_options[selected_line_family_name]

# Collect all instances of the selected detail component family
detail_instances = FilteredElementCollector(doc)\
    .OfClass(FamilyInstance)\
    .OfCategory(BuiltInCategory.OST_DetailComponents)\
    .WhereElementIsNotElementType()\
    .ToElements()

instances_to_replace = [
    inst for inst in detail_instances
    if inst.Symbol.FamilyName == selected_detail_family_name
]

# Start a transaction to modify the Revit document
transaction = Transaction(doc, 'Replace Detail Components with Line-based Family')
transaction.Start()

try:
    for inst in instances_to_replace:
        # Get the location of the instance
        location = inst.Location

        if isinstance(location, LocationPoint):
            point = location.Point

            # Define a line for the line-based family instance
            start_point = point
            end_point = XYZ(point.X + 1.0, point.Y, point.Z)  # 1 unit in the X direction
            line = Line.CreateBound(start_point, end_point)

            # Place the line-based family instance
            new_instance = doc.Create.NewFamilyInstance(
                line,
                line_family_symbol,
                doc.ActiveView
            )

            # Optionally, copy parameters from the old instance to the new instance

            # Delete the old detail component instance
            doc.Delete(inst.Id)
        else:
            # Handle cases where the location is not a point
            pass

    # Commit the transaction
    transaction.Commit()
except Exception as e:
    # Roll back the transaction in case of an error
    transaction.RollBack()
    forms.alert('An error occurred: ' + str(e), exitscript=True)
