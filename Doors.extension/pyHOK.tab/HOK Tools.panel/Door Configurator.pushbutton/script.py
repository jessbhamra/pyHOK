"""HOK Door Configurator"""
# revit23
# Import necessary libraries
from Autodesk.Revit import DB, UI
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

# Get the element selection of the current document
# replace this with something hard coded to pull prototype door- put it on github as part of extension
doorid = (doorm[0])
door= doc.GetElement(doorid)

# Function to save door as new family
def save_as_new_family(door, family_name, panel_type, frame_type, width, height):
# Save the family with a new name
    temp_dir = tempfile.mkdtemp()
    family_path = os.path.join(temp_dir, family_name + ".rfa")
    backupf_path = os.path.join(temp_dir,"Backup")

# get the prototype door family
    print (str(door))
    fam_lam = DB.Element.GetValidTypes(door)
    fam_nam = fam_lam[0]
    family_type = (doc.GetElement(fam_nam))
    fam_tpe = (family_type.Family)
    print (str(fam_tpe)+"family")

# Edit Family to bring up the family editor
    family_temp = (doc.EditFamily(fam_tpe))

# save as family_temp as doc to find nested panels and frames
    family_temp.SaveAs(family_path, DB.SaveAsOptions())

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

# open a transaction to make changes to things in Revit
    with Transaction(doc, 'Create New Family Type') as trans:
        trans.Start()
# Use a FilteredElementCollector to search for elements of the given type
        collector = DB.FilteredElementCollector(doc)\
                    .OfClass(DB.Family)
# Iterate through the elements to find the one with the matching name
        for elem in collector:
            if elem.Name == family_name:
                # Get all family symbols (types) within the loaded family
                family_symbols = elem.GetFamilySymbolIds()


                for symbol_id in family_symbols:
                    symbol = doc.GetElement(symbol_id)
                    # Assuming you want to duplicate the first symbol for simplicity
                    new_symbol_id = symbol.Duplicate("{}x{}".format(int(width*12), int(height*12)))
                    new_sym_ref = DB.Reference(new_symbol_id)
                    new_symbol = doc.GetElement(new_sym_ref)

##use GUID for the shared parameters instead of searching by name
                    # Set the new symbol's parameters as needed
                    new_symbol.LookupParameter('PANEL WIDTH PANEL 1').Set(width)
                    new_symbol.LookupParameter('PANEL HEIGHT').Set(height)
                    
                   #Set the PANEL family Type parameter to the nested door family 
                   # that matches panel_type
                    paraList = new_symbol.GetParameters('PANEL 1')
                    paraId = (paraList[0])
                    famTypes = elem.GetFamilyTypeParameterValues(paraId.Id)
                    print (famTypes)
                    BamId = None
                    for famIYam in famTypes:
                        famZam = (doc.GetElement(famIYam))
                        if famZam.Name == panel_type:
                            print (famIYam)
                            BamId = famIYam
                            break 
                    BamElem = (doc.GetElement(BamId))
                    new_symbol.LookupParameter('PANEL 1').Set(BamElem.Id)

                   #Set the FRAME family Type parameter to the nested door family 
                   # that matches frame_type
                    faraList = new_symbol.GetParameters('FRAME')
                    faraId = (faraList[0])
                    framTypes = elem.GetFamilyTypeParameterValues(faraId.Id)
                    print (framTypes)
                    FramId = None
                    for famIFam in framTypes:
                        famFam = (doc.GetElement(famIFam))
                        if famFam.Name == frame_type:
                            print (famIFam)
                            FramId = famIFam
                            break 
                    FramElem = (doc.GetElement(FramId))
                    new_symbol.LookupParameter('FRAME').Set(FramElem.Id)

                    # Rename the family symbol to reflect the new dimensions in inches
                    new_symbol.Name = "{}x{}".format(int(width*12), int(height*12))

                    #delete the other type
                    delSym = doc.Delete(symbol_id)
                    break  # Exit after processing the first symbol
                break  # Exit after finding the family
        trans.Commit()
# open a transaction to make changes to things in Revit
#    with Transaction(doc, 'delete Delete family type') as trans:
#        trans.Start()
# Use a FilteredElementCollector to search for elements of the given type
#        collectory = DB.FilteredElementCollector(doc)\
#                    .OfClass(DB.Family)
#        symDone = None
# Iterate through the elements to find the one with the matching name
#        for elemy in collectory:
#            if elemy.Name == family_name:
        # Delete Delete family symbol
#                family_symbolys = elemy.GetFamilySymbolIds()
#                for symbolyId in family_symbolys:
#                    symboly = doc.GetElement(symbolyId)
#                    if symboly.Name == 'Delete':
#                        symDone = symboly.Delete(symbolyId)
 #                       break
  #                  break
   #     trans.Commit()
    #call_purge(family_name)
    # Clean up the temporary directory
    os.remove(family_path)
    os.rmdir(backupf_path)
    os.rmdir(temp_dir)


#function to purge unused nested families



#def call_purge(family_name):
   # purge unused nested families and Delete type symbol
  # initiate Edit family of family_temp 
 # Use a FilteredElementCollector to search for elements of the given type
#        collector = DB.FilteredElementCollector(doc)\
#                    .OfClass(DB.Family)
# Iterate through the elements to find the one with the matching name
#        for elem in collector:
#           if elem.Name == family_name:
#                EditFami = (doc.EditFamily(elem))

  # do this purge thing
  #   
#                cid_PurgeUnused = \
#                    EditFami.RevitCommandId.LookupPostableCommandId(
#                        EditFami.PostableCommand.PurgeUnused
#                        )
#                __revit__.PostCommand(cid_PurgeUnused) 

#                EditFami.LoadFamily(doc, DB.IFamilyLoadOptions.OnFamilyFound())
    # Load the saved family back into the project
    #with Transaction(doc, 'Load Family') as trans:
    #    trans.Start()
    #    family_loaded= doc.LoadFamily(family_path)
    #    print (str(family_loaded))
    #    if not family_loaded:
    #        print("Failed to load family.")
    #        return
    #    trans.Commit()

# Main function for user input etc
def main():
    # Prompt user to select a door
    #selected_door_id = forms.select_element(title='Select a Door', 
    #                                       of_class='FamilyInstance', 
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
    family_name = str.format(("08-Door-") + panel_type + ("-") + frame_type +("_HOK_I"))
#from pyrevit import forms
#selected_parameters = forms.select_parameters()
#if selected_parameters:
    #do_stuff_with_parameters()
# Convert width and height to Revit internal units (feet)
    width = float(width) / 12.0
    height = float(height) / 12.0

# Save the door as a new family and create family types
    save_as_new_family(door, family_name, panel_type, frame_type, width, height)

# Update the parameters in the door
   # update_door_parameters(door, family_name, panel_type, frame_type, width, height)

# Call the main function
main()