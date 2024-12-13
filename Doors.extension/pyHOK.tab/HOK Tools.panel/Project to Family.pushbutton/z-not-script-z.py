from pyrevit import revit, DB
from System.Collections.Generic import List  # Import .NET List

# Get the current document and UIDocument
doc = revit.doc
uidoc = revit.uidoc

# Get the current selection
selection = uidoc.Selection.GetElementIds()

# Initialize separate .NET Lists for different categories
filled_regions = List[DB.ElementId]()
lines = List[DB.ElementId]()
detail_components = List[DB.ElementId]()

# Iterate through the selection
for element_id in selection:
    element = doc.GetElement(element_id)
    if element:
        # Check if the element is a filled region
        if isinstance(element, DB.FilledRegion):
            filled_regions.Add(element_id)
        # Check if the element is a line
        elif element.Category and element.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Lines):
            lines.Add(element_id)
        # Check if the element is a detail component (but not a filled region)
        elif element.Category and element.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_DetailComponents):
            detail_components.Add(element_id)

# Update the selection in the UI to only include filled regions and lines
filtered_selection = List[DB.ElementId]()
filtered_selection.AddRange(filled_regions)
filtered_selection.AddRange(lines)
uidoc.Selection.SetElementIds(filtered_selection)

# Perform additional actions for detail components
for detail_id in detail_components:
    detail_component = doc.GetElement(detail_id)
    # Example: Print the name of the detail component
    print("Detail Component:", detail_component.Name)

# Print a summary message to the console
print("Selection updated: Filled regions and lines retained. Detail components processed separately.")
