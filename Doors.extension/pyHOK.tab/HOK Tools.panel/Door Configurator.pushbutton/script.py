"""HOK Door Configurator"""

# Import necessary libraries
from Autodesk.Revit import DB
from Autodesk.Revit.DB import Document, BuiltInCategory, Transaction, FilteredElementCollector
from Autodesk.Revit.UI.Selection import Selection, ObjectType
from pyrevit import forms, revit
import tempfile
import os
import clr

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
def update_door_parameters(door, family_name, panel_type, frame_type, width, height):
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
#use GUID for the shared parameters to set them better
        

# Function to save door as new family
def save_as_new_family(door, family_name, panel_type, frame_type, width, height):

    #type_name = str((width) + (height))
    # Save the family with a new name
    temp_dir = tempfile.mkdtemp()
    family_path = os.path.join(temp_dir, family_name + ".rfa")
    backupf_path = os.path.join(temp_dir,"Backup")

    print (str(door))
    fam_lam = DB.Element.GetValidTypes(door)
    fam_nam = fam_lam[0]
    #print (str(fam_nam))
    family_type = (doc.GetElement(fam_nam))
    fam_tpe = (family_type.Family)

    print (str(fam_tpe)+"family")
    family_temp = (doc.EditFamily(fam_tpe))
    #DB.Document.SaveAs(family_path, DB.SaveAsOptions())
    family_temp.SaveAs(family_path, DB.SaveAsOptions())

    #print(family_path)

    # Load the saved family back into the project
    with Transaction(doc, 'Load Family') as trans:
        trans.Start()
        family_loaded= doc.LoadFamily(family_path)
        print (str(family_loaded))
        if not family_loaded:
            print("Failed to load family.")
            return
        trans.Commit()

    # Find the loaded family by name to work with its symbols
    with Transaction(doc, 'Create New Family Type') as trans:
        trans.Start()
        # Use a FilteredElementCollector to search for elements of the given type
        collector = DB.FilteredElementCollector(doc)\
                    .OfClass(DB.Family)
                            #.OfCategory(BuiltInCategory.OST_Doors)\
        print(str(collector))
        # Iterate through the elements to find the one with the matching name
        for elem in collector:
            print (str(elem.Name))
            if elem.Name == family_name:
                # Get all family symbols (types) within the loaded family
                
                family_symbols = elem.GetFamilySymbolIds()
                for symbol_id in family_symbols:
                    symbol = doc.GetElement(symbol_id)
                    # Assuming you want to duplicate the first symbol for simplicity
                    new_symbol_id = symbol.Duplicate("{}x{}".format(int(width*12), int(height*12)))
                    new_sym_ref = DB.Reference(new_symbol_id)
                    new_symbol = doc.GetElement(new_sym_ref)
                    

                   # Nested family retrieval to set the panel and frame type
                    

                    door_collector = DB.FilteredElementCollector(doc)\
                   .OfCategory(DB.BuiltInCategory.OST_Doors)\
                   .WhereElementIsNotElementType()
                    #nest_frm_type = 

                    #nest_pnl_type = 

                    # Set the new symbol's parameters as needed
                    new_symbol.LookupParameter('PANEL WIDTH PANEL 1').Set(width)
                    new_symbol.LookupParameter('PANEL HEIGHT').Set(height)

                    #parameter_set= new_symbol.GetParameters()

                    #for paras in parameter_set:
                    #    if paras.Name == panel_type: # do something!    
                    #        paras_set = paras.GetElementIds
                    #    break
                    
                    
                #    panel_set = new_symbol.LookupParameter('PANEL 1')
                    
                #    (panel_type)
                     

                #    parameter2= new_symbol.LookupParameter('FRAME')
                #    if parameter2 is not None:
                #        frame_set = new_symbol.LookupParameter('FRAME').Set(frame_type)
                #        if frame_set:
                #            print('woo frame')
                #        else:
                #            print( 'noo frame')
                #    else:
                #        print( 'FRAME parameter was not found')
                
                    # Rename the symbol to reflect the new dimensions in inches
                    new_symbol.Name = "{}x{}".format(int(width*12), int(height*12))
                    break  # Exit after processing the first symbol
                break  # Exit after finding the family
        trans.Commit()
   
    # Clean up the temporary directory
    os.remove(family_path)
    os.rmdir(backupf_path)
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
    #door = ui.Selection.PickObject(ObjectType.Element)

    # Ask user to input Panel Type, Frame Type, Width and Height
    panel_type = "DF"
    #forms.ask_for_string("Enter Panel Type")
    frame_type = "S02"
    #forms.ask_for_string("Enter Frame Type")
    width = 43
    #forms.ask_for_string("Enter Width (in inches)")
    height = 96
    #forms.ask_for_string("Enter Height (in inches)")
    # Define the new family name
    family_name = str.format(panel_type + frame_type)
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
    save_as_new_family(door, family_name, panel_type, frame_type, width, height)

    # Update the parameters in the door
    #update_door_parameters(door, family_name, panel_type, frame_type, width, height)

# Call the main function
main()