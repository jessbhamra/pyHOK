# -*- coding: utf-8 -*-
"""Select elements in drafting view and convert to detail family"""
__title__ = 'Project to Family'
__author__ = 'HOK'

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    FamilySymbol,
    FamilyInstance,
    BuiltInCategory,
    Transaction,
    ElementTransformUtils,
    FamilyCreationOptions,
    IFamilyLoadOptions,
    ViewDrafting,
    Family,
    LinePatternElement,
    LinePattern,
    LinePatternSegment,
    CurveElement,
    LineStyle,
    Category,
    XYZ,
    Line,
    Arc,
    View
)
from pyrevit import revit, forms, script

# Implementing a simple family load options class
class SimpleFamilyLoadOptions(IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues = True
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, source, overwriteParameterValues):
        overwriteParameterValues = True
        return True

# Get the current Revit document
doc = revit.doc

# Collect all drafting views in the document
drafting_views = FilteredElementCollector(doc)\
    .OfClass(ViewDrafting)\
    .ToElements()

# Create a dictionary of drafting view names and their elements
drafting_view_options = {view.Name: view for view in drafting_views}

# Prompt the user to select the drafting view
selected_view_name = forms.SelectFromList.show(
    sorted(drafting_view_options.keys()),
    title='Select Drafting View to Convert Elements From',
    button_name='Select'
)

# Exit the script if no view is selected
if not selected_view_name:
    script.exit()

selected_view = drafting_view_options[selected_view_name]

# Collect all curve elements (lines, arcs, etc.) in the selected drafting view
curve_elements = FilteredElementCollector(doc, selected_view.Id)\
    .OfClass(CurveElement)\
    .ToElements()

# Start a transaction to modify the Revit document
transaction = Transaction(doc, 'Convert Drafting View Elements to Detail Items')
transaction.Start()

try:
    # Create a new detail item family
    fam_doc = doc.Application.NewFamilyDocument('Metric Detail Item.rft')

    # Get the family editor
    fam_editor = fam_doc.FamilyCreate

    # Map to store line styles
    line_style_map = {}

    # Loop through each curve element
    for curve_elem in curve_elements:
        # Get the geometry curve
        geom_curve = curve_elem.GeometryCurve

        # Get the line style of the curve element
        curve_line_style = curve_elem.LineStyle

        # Check if the line style already exists in the family document
        if curve_line_style.Name not in line_style_map:
            # Create a new line style in the family document
            line_cat = fam_doc.Settings.Categories.get_Item(BuiltInCategory.OST_Lines)
            new_subcat = fam_doc.Settings.Categories.NewSubcategory(line_cat, curve_line_style.Name)

            # Copy line pattern and color
            new_subcat.LineColor = curve_line_style.GraphicsStyleCategory.LineColor
            new_subcat.SetLineWeight(curve_line_style.GraphicsStyleCategory.GetLineWeight(GraphicsStyleType.Projection), GraphicsStyleType.Projection)
            line_pattern_id = curve_line_style.GraphicsStyleCategory.GetLinePatternId(GraphicsStyleType.Projection)
            new_subcat.SetLinePatternId(line_pattern_id, GraphicsStyleType.Projection)

            # Add to map
            line_style_map[curve_line_style.Name] = new_subcat

        # Create the curve in the family document
        if isinstance(geom_curve, Line) or isinstance(geom_curve, Arc):
            fam_editor.NewModelCurve(geom_curve, fam_doc.ActiveView.SketchPlane)
        else:
            # Handle other curve types if necessary
            pass

        # Set the line style
        new_curve_elem = fam_doc.GetElement(fam_doc.OwnerFamily.Id)
        new_curve_elem.LineStyle = line_style_map[curve_line_style.Name]

    # Save the family document to a temporary location
    temp_family_path = r'C:\Temp\DetailItemFromDraftingView.rfa'
    fam_doc.SaveAs(temp_family_path)

    # Load the family into the project
    family = None
    loaded = doc.LoadFamily(temp_family_path, SimpleFamilyLoadOptions(), family)

    if loaded:
        # Get the family symbol
        family_symbols = family.GetFamilySymbolIds()
        if family_symbols.Count > 0:
            symbol_id = list(family_symbols)[0]
            symbol = doc.GetElement(symbol_id)

            # Place the family instance into the current view
            doc.Create.NewFamilyInstance(XYZ(0, 0, 0), symbol, selected_view)

    # Close the family document without saving
    fam_doc.Close(False)

    # Commit the transaction
    transaction.Commit()

except Exception as e:
    # Roll back the transaction in case of an error
    transaction.RollBack()
    forms.alert('An error occurred: ' + str(e), exitscript=True)
