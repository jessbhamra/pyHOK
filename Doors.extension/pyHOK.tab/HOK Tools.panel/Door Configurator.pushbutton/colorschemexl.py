import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')
clr.AddReference('RevitNodes')
clr.AddReference('System')

from RevitServices.Persistence import DocumentManager
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Document, BuiltInCategory, Transaction, BuiltInParameterGroup, FamilyParameter, FamilyType, FilteredElementCollector
from Autodesk.Revit.UI.Selection import Selection, ObjectType
from System.Collections.Generic import List

# Import csv for CSV export
import csv

# Get the active document
doc = __revit__.ActiveUIDocument.Document

# Define the file path for the CSV
file_path = "B:\\ColorSchemes.csv"

# Open the CSV file for writing
with open(file_path, mode='w', newline='') as file:
    writer = csv.writer(file)

    # Write headers
    writer.writerow(["View Name", "Color Scheme Name", "Category Name", "Color Value (ARGB)"])

    # Get all views in the document
    views_collector = FilteredElementCollector(doc).OfClass(DB.View)

    # Iterate through views to find and export color schemes
    for view in views_collector:
        # Get color schemes in the view
        color_schemes = (view.ElementID).GetColorFillSchemeID()

        color_entries = color_schemes.ColorFillScheme.GetEntries

        for color_scheme in color_entries:
            # Get the name of the color scheme entry
            scheme_name = color_scheme.Name


# 


            # Get the category associated with the color scheme
            category_id = color_scheme.CategoryId
            category = doc.GetElement(category_id)
            category_name = category.Name if category else "Unknown Category"

            # Get color definitions
            definitions = color_scheme.ColorFillScheme.GetEntries

            for definition in definitions:
                # Extract color and value information
                color = definition.Color
                value = definition.Value

                # Convert color to ARGB
                argb_value = "({0},{1},{2},{3})".format(color.Alpha, color.Red, color.Green, color.Blue)

                # Write data to CSV
                writer.writerow([view.Name, scheme_name, category_name, argb_value])

print("Color schemes exported to " + file_path)
