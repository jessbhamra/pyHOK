"""HOK Door Configurator"""

# Import necessary libraries
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Document
from Autodesk.Revit.UI.Selection import Selection, ObjectType
# BuiltInCategory, Transaction
from pyrevit import forms
import tempfile
import os

doc = __revit__.ActiveUIDocument.Document
ui = __revit__.ActiveUIDocument

# Function to update door parameters
# 
#make a transaction
def update_door_parameters(door, panel_type, frame_type, width, height):
    transaction = DB.Transaction(doc, 'Update Door Parameters')
    transaction.Start()
    try:
        door.LookupParameter('PANEL 1').Set(panel_type)
        door.LookupParameter('FRAME').Set(frame_type)
        door.LookupParameter('PANEL WIDTH PANEL 1').Set(width)
        door.LookupParameter('PANEL HEIGHT').Set(height)
        transaction.Commit()
    except Exception:
        print("Failed to update parameters")
        #transaction.RollBack()
        transaction.Commit()

# Function to save door as new family
def save_as_new_family(door, panel_type, frame_type, width, height):
    # Define the new family name
    family_name = str.format(panel_type + frame_type)

    type_name = str((width) + (height))

    # Save the family with a new name
    temp_dir = tempfile.mkdtemp()
    family_path = os.path.join(temp_dir, family_name + ".rfa")

   # family_path = str(os.path.join(temp_dir, family_name + ".rfa"))
    
    family_temp = Document.EditFamily(selected_door)
    #DB.Document.SaveAs(family_path, DB.SaveAsOptions())

    # Load the family back into the document
    with DB.Transaction("Load Family"):
        family_loaded = DB.LoadFamily(family_path)
        #if family_loaded:
            # Get the family symbol and duplicate it with the new type name
  #          family_symbols = DB.FilteredElementCollector(revit.doc)\
   #                            .OfClass(DB.FamilySymbol)\
    #                           .OfCategory(DB.BuiltInCategory.OST_Doors)\
     #                          .Where(lambda x: x.Family.Name == family_name)
     #       for symbol in family_symbols:
     #           new_symbol = symbol.Duplicate(type_name)
     #           new_symbol.LookupParameter('Width').Set(width)
     #           new_symbol.LookupParameter('Height').Set(height)

    # Clean up the temporary directory
    os.remove(family_path)
    os.rmdir(temp_dir)


# Main function
def main():
    # Prompt user to select a door
   # selected_door_id = forms.select_element(title='Select a Door', 
   #                                         of_class='FamilyInstance', 
    #                                        category='OST_Doors')
    #if selected_door_id is None:
    #    print("No door selected.")
    #    return
    selected_door = ui.Selection.PickObject(ObjectType.Element)

    # Ask user to input Panel Type, Frame Type, Width and Height
    panel_type = forms.ask_for_string("Enter Panel Type")
    frame_type = forms.ask_for_string("Enter Frame Type")
    width = forms.ask_for_string("Enter Width (in inches)")
    height = forms.ask_for_string("Enter Height (in inches)")

#from pyrevit import forms
#selected_parameters = forms.select_parameters()
#if selected_parameters:
    #do_stuff_with_parameters()
    #
    #

    # Convert width and height to Revit internal units (feet)
    width = float(width) / 12.0
    height = float(height) / 12.0

    # Update the parameters in the door
    update_door_parameters(selected_door, panel_type, frame_type, width, height)

    # Save the door as a new family and create family types
    save_as_new_family(selected_door, panel_type, frame_type, width, height)

# Call the main function
main()