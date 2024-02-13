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
import System

__context__ = 'Doors'

doc = __revit__.ActiveUIDocument.Document
ui = __revit__.ActiveUIDocument

doorm = ui.Selection.GetElementIds()

# Get the element selection of the current document
# replace this with something hard coded to pull prototype door
doorid = (doorm[0])
door= doc.GetElement(doorid)

# Function to save door as new family
def save_as_new_family(door, family_name, panel_type, frame_type, width, height):
# Save the family with a new name
    temp_dir = tempfile.mkdtemp()
    family_path = os.path.join(temp_dir, family_name + ".rfa")
    backupf_path = os.path.join(temp_dir,"Backup")

# get the prototype door family
    #print (str(door))
    print("making a new family...")
    fam_lam = DB.Element.GetValidTypes(door)
    fam_nam = fam_lam[0]
    family_type = (doc.GetElement(fam_nam))
    fam_tpe = (family_type.Family)
    print (str(fam_tpe)+"family")

# Edit Family to bring up the family editor
    family_temp = (doc.EditFamily(fam_tpe))#EditFamily must be called OUTSIDE of a transaction
#make new type and assign values
    typeName = "{}x{}".format(int(width*12), int(height*12))


#start a transaction and instantiate family manager
    with Transaction(family_temp, 'Make Type and set Values') as trans:
        try:
            trans.Start()
            famMan = family_temp.FamilyManager
            famFamily = family_temp.OwnerFamily
            #print ("51" , (famFamily))
            deleteType = famMan.CurrentType
            #print(str(deleteType),  " delete bB")
            typeMake = famMan.NewType(typeName)
            print("making new type...")

        
#these are the shared parameter GUIDs for the parameters we're looking for
            pwGU = "318d67dd-1f5f-43fb-a3d0-32ac31f1babb"#PANEL WIDTH PANEL 1
            phGU = "3e7f226e-bc78-407c-982a-d45a405cd2a9"#PANEL HEIGHT
            pnGU = "8e89f65d-3ed9-45c8-9808-8c315dedadce" #PANEL 1
            pfGU = "b6930f0e-c0f5-432b-80ee-6c649f876cae" #FRAME


  #filtered element collector to grab nested door families
            nestFams = DB.FilteredElementCollector(family_temp)\
                .OfClass(DB.Family).ToElements()
                
            BamId = None
            FamId = None                
            FlamId = None
            print("updating parameters...")
            for FamThis in nestFams:
                if FamThis.Name == panel_type:
                    BamId = FamThis
                elif FamThis.Name == frame_type:
                    FamId = FamThis
                else: FlamId = FamThis

                
#If a new type was made successfully
            if typeMake:
#get the set of Family parameters and iterate through them
                paraSet = famMan.GetParameters()
            #for each parameter in the family
                for parr in paraSet:
                #if the parameter is shared,
                    if parr.IsShared:
                        pParr = parr.GUID
                    #print ( pParr)

  #check if the parameter GUID matches the 4 parameters we are looking to set
  #                   
                        if str(pParr) == pwGU:
                    #if PANEL WIDTH PANEL 
                            famMan.Set(parr, width)
                    
                        elif str(pParr) == phGU:
                    #elif PANEL HEIGHT   
                            famMan.Set(parr, height)

                        elif str(pParr) == pnGU:
                            #print (BamId.Id)
                            BamSyms = BamId.GetFamilySymbolIds()
                            for BamSym in BamSyms:
                                famMan.Set(parr, BamSym) 
                                #print(str(BamSym))
                    
                        elif str(pParr) == pfGU:
                            FamSyms = FamId.GetFamilySymbolIds()
                            #print(FamSyms)
                            for FamSym in FamSyms:
                                famMan.Set(parr, (FamSym)) 

        #udelete unused nested families
                    FlamSyms = FlamId.GetFamilySymbolIds()
                    #print(FlamSyms)
                    for FlamSym in FlamSyms: 
                        FlamSId = family_temp.GetElement(FlamSym)
#                    if FlamSId.Family.
 #                       if not FlamSId.IsActive:
 #                               family_temp.Delete(FlamSym)
#purge nested families                                 
                #purge nested prototypical type
                  #set delete type as current type
                famMan.CurrentType = deleteType
                typeDel = famMan.DeleteCurrentType()  
                if typeDel:
                    print("Deleting embrionic type...")
                trans.Commit()

        #else:
            #print ("88")
            #trans.RollBack()
                    #if it doesn't work, throw an error message 
        except Exception as e: 
            print("Error: {}".format(e))
            trans.RollBack()


    #do the pruge here

#delete Delete family
  

#save as the family with new name and path
    family_temp.SaveAs(family_path, DB.SaveAsOptions())
    print("saving new file...")
# Load the saved family back into the project
    print("loading new family into project...")
    with Transaction(doc, 'Load Family') as trans:
        trans.Start()
        family_loaded= doc.LoadFamily(family_path)
       # print (str(family_loaded))
        if not family_loaded:
            print("Failed to load family.")
            return
        trans.Commit()
    print ("reticulating splines...")
    # Clean up the temporary directory
    os.remove(family_path)
    os.rmdir(backupf_path)
    os.rmdir(temp_dir)

def edit_types_and_params(family_name, panel_type, frame_type, width, height):
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
                    #duplicate the first symbol for simplicity
                    #specify which to duplicate
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
                    #print (framTypes)
                    FramId = None
                    for famIFam in framTypes:
                        famFam = (doc.GetElement(famIFam))
                        if famFam.Name == frame_type:
                            print (famIFam)
                            FramId = famIFam
                            break
                    FramElem = (doc.GetElement(FramId))
                    new_symbol.LookupParameter('FRAME').Set(FramElem.Id)
###########try to do this another way using Type instead of symbol
                    # Rename the family symbol to reflect the new dimensions in inches
                    new_symbol.Name = "{}x{}".format(int(width*12), int(height*12))
#this may have to be done in the purge function instead
                    #delete the Delete type
                    delSym = doc.Delete(symbol_id)
    # call purge
                    break  # Exit after processing the first symbol
                break  # Exit after finding the family
        trans.Commit()


def call_purge(family_name):
#Function to purge unused nested families from a specified family.


#      
    # Find the family by name
    family = None
    for el in FilteredElementCollector(doc).OfClass(DB.Family):
        if el.Name == family_name:
            family = el
            break

    if family:
        famDoc = doc.EditFamily(family)
        # Edit the family to access nested families
        with Transaction((famDoc), 'Purge Unused Nested Families') as trans:
            trans.Start()
#Function to call Types from type symbols
# Also delete Delete type
# then purge

            try:
                # Check nested families and delete unused ones
                for nested_family in (FilteredElementCollector(famDoc).OfClass(DB.Family).ToElementIds()):
                    nestSym = famDoc.GetElement(nested_family)
                    nestSymb= nestSym.GetFamilySymbolIds()
                    if nestSymb:
                        for syms in nestSymb:
                            symSel = (famDoc.GetElement(syms))
                            if not symSel.IsActive:
                                famDoc.Delete(nestSym.Id)
                                break
                
                
            # Load the family back into the project
                class FamilyOption(DB.IFamilyLoadOptions):
                    def OnFamilyFound(self, family, overwriteParameterValues):
                        overwriteParameterValues = True
                        return True

                family_loaded = famDoc.LoadFamily(doc, FamilyOption())
                if family_loaded:
                    print("Family loaded successfully.") 
                
                    trans.Commit()
        #if it doesn't work, throw an error message 
            except Exception as e:
                print("Error: {}".format(e))
                trans.RollBack()
    else:
        print("Family not found with the specified name.")

                
def purgeIt():

    """Call Revit "Purge Unused" after completion."""
    cid_PurgeUnused = \
        UI.RevitCommandId.LookupPostableCommandId(
            UI.PostableCommand.PurgeUnused
            )
    __revit__.PostCommand(cid_PurgeUnused)

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
    width = 37
    #forms.ask_for_string("Enter Width (in inches)")
    height = 85
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
#    edit_types_and_params(family_name, panel_type, frame_type, width, height)

#purrrrrrggggggggeeeeeee
 #   call_purge(family_name)

# Call the main function
main()
#elif PANEL 1  and FRAME with an else so only have to iterate through fEC once
                        
                     #filtered element collector to grab nested door families
                       # parTry = DB.FilteredElementCollector(family_temp)\
                                #.OfCategory(BuiltInCategory.OST_Doors)\
                                #.WhereElementIsElementType()
                        
                        #parrGet = family_temp.GetElement(parr.Id)
                        #famTypes = famFamily.GetFamilyTypeParameterValues(parrGet.Id)
                        #print (famTypes, "91")
                        #BamId = None
                        #FamId = None