# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import (
    Transaction,
    FilteredElementCollector,
    ElementMulticategoryFilter,
    BuiltInCategory,
    ElementTransformUtils,
    ViewFamilyType,
    FamilyCreationOptions,
    SaveAsOptions
)
from Autodesk.Revit.UI import (
    TaskDialog,
    FileOpenDialog,
    FileOpenDialogResult,
    IExternalEventHandler,
    IExternalApplication,
    UIDocument
)
from pyrevit import revit, DB, forms
import os

# Get the current document and UI
uidoc = revit.uidoc
doc = revit.doc

# Ensure we have a selection of detail elements
selection_ids = [elId for elId in uidoc.Selection.GetElementIds()]
if not selection_ids:
    forms.alert("No elements selected. Please select 2D detail elements and run again.", exitscript=True)

# Retrieve the selected elements
selected_elements = [doc.GetElement(eid) for eid in selection_ids]

# Filter the selected elements to only those that are 2D Detail elements
# Valid categories for "2D detail" could include:
# Detail Lines (OST_Lines), Filled Regions (OST_FilledRegion), Detail Components (OST_DetailComponents),
# Reference Planes (OST_CLines)
valid_categories = [
    BuiltInCategory.OST_Lines,
    BuiltInCategory.OST_FilledRegion,
    BuiltInCategory.OST_DetailComponents,
    BuiltInCategory.OST_Insulation, # If needed
    BuiltInCategory.OST_CLines,
    BuiltInCategory.OST_DetailItems
]

filtered_selection = [el for el in selected_elements if el.Category and el.Category.Id.IntegerValue in [cat.value__ for cat in valid_categories]]

if not filtered_selection:
    forms.alert("No valid 2D detail elements selected. Please select lines, detail components, or filled regions.", exitscript=True)

# Check if we're in a detail or drafting view
current_view = doc.ActiveView
if not (current_view.ViewType == DB.ViewType.Detail or current_view.ViewType == DB.ViewType.DraftingView):
    forms.alert("Please run this command in a Detail or Drafting view.", exitscript=True)


##################################
# Family creation steps
##################################

# Path to your detail item family template
# Update this to a valid path on your machine or company standard template.
FAMILY_TEMPLATE_PATH = r"C:\Revit Templates\Metric Detail Item.rft"  # Example, must exist!

if not os.path.exists(FAMILY_TEMPLATE_PATH):
    forms.alert("Detail item family template not found. Update FAMILY_TEMPLATE_PATH in script.")
    raise ValueError("Family template path invalid")

app = doc.Application

# Create a new family document from template
family_doc = app.NewFamilyDocument(FAMILY_TEMPLATE_PATH)

# Start a transaction in the family doc (not strictly necessary for copy)
t_fam = Transaction(family_doc, "Prepare Family")
t_fam.Start()

# The copy/paste process: we have to map elements from the project doc to family doc
# We'll try using ElementTransformUtils.CopyElements
element_ids_to_copy = [el.Id for el in filtered_selection]

# Copy the elements into the family document
mapping = ElementTransformUtils.CopyElements(
    sourceDoc=doc,
    elementIds=element_ids_to_copy,
    targetDoc=family_doc,
    transform=DB.Transform.Identity
)

t_fam.Commit()


# Save the family to a temporary location or prompt user for location
temp_family_path = forms.save_file(file_ext='rfa', prompt_title='Save new detail family', default_name='NewDetailFamily')
if not temp_family_path:
    forms.alert("No save location specified. Cancelling.")
    family_doc.Close(False)
    raise Exception("Family save cancelled")

save_options = SaveAsOptions()
family_doc.SaveAs(temp_family_path, save_options)
family_doc.Close(False)

##################################
# Load the created family into the project
##################################
t_load = Transaction(doc, "Load Detail Component Family")
t_load.Start()
loaded_family = None
load_result = doc.LoadFamily(temp_family_path, loaded_family)
t_load.Commit()

if not load_result:
    forms.alert("Failed to load the newly created family into the project.")
    raise Exception("Family load failed")


# Optionally, place an instance of the newly created family in the current view
# Find the just-loaded family
fam = [f for f in FilteredElementCollector(doc).OfClass(DB.Family) if f.FamilyCategory and f.Name in temp_family_path][0]

# Each family can have multiple symbols (types). We'll take the first available
family_symbol = None
for fsid in fam.GetFamilySymbolIds():
    family_symbol = doc.GetElement(fsid)
    break

if family_symbol and not family_symbol.IsActive:
    # Make sure the symbol is activated
    t_activate = Transaction(doc, "Activate Family Symbol")
    t_activate.Start()
    family_symbol.Activate()
    t_activate.Commit()

# Now place an instance at the current view's origin as an example:
t_place = Transaction(doc, "Place Detail Component Instance")
t_place.Start()
doc.Create.NewFamilyInstance(DB.XYZ(0,0,0), family_symbol, current_view)
t_place.Commit()

forms.alert("Detail family created and placed successfully.")
