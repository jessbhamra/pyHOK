"""HOK Door Configurator"""

# Import necessary libraries
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Document, BuiltInCategory, Transaction
from Autodesk.Revit.UI.Selection import Selection, ObjectType
from pyrevit import forms, revit
import tempfile
import os

__context__ = 'Doors'

doc = __revit__.ActiveUIDocument.Document
ui = __revit__.ActiveUIDocument

doorm = ui.Selection.GetElementIds()
#door = __revit__.selection
# Get the element selection of the current document
doorid = (doorm[0])
door= doc.GetElement(doorid)


#door_collector = DB.FilteredElementCollector(doc)\
#                   .OfCategory(DB.BuiltInCategory.OST_Doors)\
#                   .WhereElementIsNotElementType()


# Function to update door parameters
# revit23
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
    backupf_path = os.path.join(temp_dir,"Backup")
   # family_path = str(os.path.join(temp_dir, family_name + ".rfa"))
    #ui.SaveAs(family_path)

    #extract revit family from selection
    #fam_lam= doc.GetElement(door)  
    #fam_lam= DB.FilteredElementCollector(door)
    print (str(door))
    fam_lam = DB.Element.GetValidTypes(door)
    fam_nam = fam_lam[0]


    print (str(fam_nam))

    #fam_fmr = fam_nam.
    family_type = (doc.GetElement(fam_nam))
    fam_tpe = (family_type.Family)

    print (str(fam_tpe)+"family")
    family_temp = (doc.EditFamily(fam_tpe))
    #DB.Document.SaveAs(family_path, DB.SaveAsOptions())
    family_temp.SaveAs(family_path, DB.SaveAsOptions())

    print(family_path)

    # Load the family back into the document
    with DB.Transaction(doc):
        family_loaded = DB.Document.LoadFamily(doc,family_path)
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
   # os.remove(family_path)
    #os.rmdir(backupf_path)
    #os.rmdir(temp_dir)


# Main function
def main():
    # Prompt user to select a door
   # selected_door_id = forms.select_element(title='Select a Door', 
   #                                         of_class='FamilyInstance', 
    #                                        category='OST_Doors')
    #if selected_door_id is None:
    #    print("No door selected.")
    #    return
    #door = ui.Selection.PickObject(ObjectType.Element)

    # Ask user to input Panel Type, Frame Type, Width and Height
    panel_type = "PNL-F"
    #forms.ask_for_string("Enter Panel Type")
    frame_type = "FRM-S01"
    #forms.ask_for_string("Enter Frame Type")
    width = 36
    #forms.ask_for_string("Enter Width (in inches)")
    height = 84
    #forms.ask_for_string("Enter Height (in inches)")

#from pyrevit import forms
#selected_parameters = forms.select_parameters()
#if selected_parameters:
    #do_stuff_with_parameters()
    #
    #

    # Convert width and height to Revit internal units (feet)
    width = float(width) / 12.0
    height = float(height) / 12.0

  

    # Save the door as a new family and create family types
    save_as_new_family(door, panel_type, frame_type, width, height)

    # Update the parameters in the door
    update_door_parameters(door, panel_type, frame_type, width, height)

# Call the main function
main()