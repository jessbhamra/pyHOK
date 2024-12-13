from pyrevit import revit, DB
from System.Collections.Generic import List  # Import .NET List

# Get the current document and UIDocument
doc = revit.doc
uidoc = revit.uidoc

# Get the current selection
selection = uidoc.Selection.GetElementIds()

# Initialize a .NET List to store filtered elements
filtered_selection = List[DB.ElementId]()

# Iterate through the selection
for element_id in selection:
    element = doc.GetElement(element_id)
    if element:
        # Check if the element is a filled region
        if isinstance(element, DB.FilledRegion):
            filtered_selection.Add(element_id)
        # Check if the element is a line
        elif element.Category and element.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Lines):
            filtered_selection.Add(element_id)

# Update the selection in the UI
uidoc.Selection.SetElementIds(filtered_selection)

# Print a message to the console
print("Filtered selection updated: Only filled regions and lines retained.")
