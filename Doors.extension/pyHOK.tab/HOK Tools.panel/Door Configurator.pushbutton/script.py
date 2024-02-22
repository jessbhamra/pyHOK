"""HOK Door Configurator"""
# revit23
# Import necessary libraries
from Autodesk.Revit import DB, UI
from Autodesk.Revit.DB import Document, BuiltInCategory, Transaction, BuiltInParameterGroup, FamilyParameter, FamilyType, FilteredElementCollector
from Autodesk.Revit.UI.Selection import Selection, ObjectType
from pyrevit import forms, revit, coreutils, script
from pyrevit.forms import WPFWindow
import tempfile
import os
import clr
import System
from System.Collections.Generic import List

__context__ = 'Doors'

doc = __revit__.ActiveUIDocument.Document
ui = __revit__.ActiveUIDocument
####
####
####New part here to pick new, edit, or bulk
doorm = ui.Selection.GetElementIds()
# Gets the element selection of the current document
# replace this with something hard coded inside one of the other functions/ its own function to pull the right prototype door based on the panel and frame types.
doorid = (doorm[0])
door= doc.GetElement(doorid)
####
####
####
logger = coreutils.logger.get_logger(__name__)
#function for making families and types from excel. settings/ whatever file


# Main function for user input etc
def main():
    # Prompt user to select a door
    class UserDetailsForm(WPFWindow):
        def __init__(self, xaml_file_path):
            WPFWindow.__init__(self, xaml_file_path)
            self.btnSubmit.Click += self.on_submit
            self.set_icon("C:\\Users\\Jess.Bhamra\\OneDrive - HOK\\Documents\\GitHub\\DoorConfig\\Doors.extension\\pyHOK.tab\\HOK Tools.panel\\Door Configurator.pushbutton\\HOK.ico")

        def on_submit(self, sender, e):
            self.panel_type = self.txtPanelType.Text
            self.frame_type = self.txtFrameType.Text
            self.width = self.txtWidth.Text
            self.height = self.txtHeight.Text
            self.Close()
### THIS NEEDS TO BE UPDATED ONCE WE HAVE A LOCATION FOR IT TO GO FOR DEPLOYMENT
# Path to the XAML file
    xaml_file_path = "C:\\Users\\Jess.Bhamra\\OneDrive - HOK\\Documents\\GitHub\\DoorConfig\\Doors.extension\\pyHOK.tab\\HOK Tools.panel\\Door Configurator.pushbutton\\rDetailsForm.xaml"

# Create and show the form
    form = UserDetailsForm(xaml_file_path)
    form.show_dialog()

# After the form is closed, you can access the inputs
    print(form.panel_type, form.frame_type, form.width, form.height)
    panel_type = form.panel_type.upper()
    frame_type = form.frame_type.upper()
    width = form.width.upper()
    height = form.height.upper()

#If user doesn't give the right input, exit out 
#of the program and/ or give them another chance to enter

#format of family name
    family_name = str.format(("08-Door_") + panel_type + ("_") + frame_type +("_SingleFlush_HOK_I"))

# Convert width and height to Revit internal units (feet)
    width = float(width) / 12.0
    height = float(height) / 12.0

#sort funtion - is this a new door or an edit to an existing door? somewhere decide what base file to start with. Where should these go?

# if new, use save_as_new_family

#if edit, use edit_types_and_parameters

# Save the door as a new family and create family types
    save_as_new_family(door, family_name, panel_type, frame_type, width, height)

#Print success message
    print("HOK Door Configurator finished {} at {} on {}".format(family_name, coreutils.current_time(), coreutils.current_date()))

#purge

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
            print(str(deleteType),  " delete bB")
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
                        if str(pParr) == pwGU:
                    #if PANEL WIDTH PANEL 
                            famMan.Set(parr, width)
                        elif str(pParr) == phGU:
                    #elif PANEL HEIGHT   
                            famMan.Set(parr, height)
                        elif str(pParr) == pnGU:
                    #elif panel type
                            BamSyms = BamId.GetFamilySymbolIds()
                            for BamSym in BamSyms:
                                famMan.Set(parr, BamSym)  
                    #elif frame types                  
                        elif str(pParr) == pfGU:
                            FamSyms = FamId.GetFamilySymbolIds()
                            for FamSym in FamSyms:
                                famMan.Set(parr, (FamSym)) 
        #delete unused nested families
                    FlamSyms = FlamId.GetFamilySymbolIds()
                    for FlamSym in FlamSyms: 
                        FlamSId = family_temp.GetElement(FlamSym)
        #set delete type as current type
                famMan.CurrentType = deleteType
                typeDel = famMan.DeleteCurrentType()
                famMan.CurrentType = typeMake  
                if typeDel:
                    print("Deleting embrionic type...")  
                trans.Commit()
        except Exception as e: 
            print("Error: {}".format(e))
            trans.RollBack()
#purge unused nested families function
   # collect_and_cull(family_temp)
  #   purge_unused_nested_families(family_temp)
#save as the family with new name and path
    family_temp.SaveAs(family_path, DB.SaveAsOptions())
    print("saving new file...")

    purge_perf_adv(family_temp)
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



def purge_perf_adv(family_doc):
    purgeGuid = 'e8c63650-70b7-435a-9010-ec97660c1bda'
    purgableElementIds = []
    performanceAdviser = DB.PerformanceAdviser.GetPerformanceAdviser()
    guid = System.Guid(purgeGuid)
    ruleId = None
    allRuleIds = performanceAdviser.GetAllRuleIds()
    for rule in allRuleIds:
    # Finds the PerformanceAdviserRuleId for the purge command
        if str(rule.Guid) == purgeGuid:
            ruleId = rule
    ruleIds = List[DB.PerformanceAdviserRuleId]([ruleId])
    for i in range(4):
    # Executes the purge
        failureMessages = performanceAdviser.ExecuteRules(family_doc, ruleIds)
        if failureMessages.Count > 0:
        # Retreives the elements
            purgableElementIds = failureMessages[0].GetFailingElements()
    print(purgableElementIds)
# Deletes the elements
    with Transaction(family_doc, 'Its purgin time') as s:
        s.Start()
        try:
            family_doc.Delete(purgableElementIds)
            print("purge attempt 1")

        except:
            for e in purgableElementIds:
                try:
                    family_doc.Delete(e)
                    print("purge attempt 2")
                except:
                    print("no purge")
                    pass
        s.Commit()        

# Call the main function
main()
