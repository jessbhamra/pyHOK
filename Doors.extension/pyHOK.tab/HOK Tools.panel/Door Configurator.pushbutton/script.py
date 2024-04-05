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
import sys
from System.Collections.Generic import List
import csv
# Import settings from config.py
import config

#__context__ = 'Doors'
doc = __revit__.ActiveUIDocument.Document
ui = __revit__.ActiveUIDocument
logger = coreutils.logger.get_logger(__name__)

#if frame is ds1, use shared parameter guid #### for the slider width slider 1 parameter, or do name match

def main():
    #defines the inputs via forms and runs the funtion(s) based on input
    xaml_file_path = config.XAML_FILE_PATH
    csv_file_path = config.CSV_FILE_PATH
    selected_action = prompt_door_action()
    if selected_action == 'New Door':
    # Prompt user to enter types in form
        class UserDetailsForm(WPFWindow):
            def __init__(self, xaml_file_path):
                WPFWindow.__init__(self, xaml_file_path)
                self.btnSubmit.Click += self.on_submit
                self.set_icon(config.ICON_PATH)
            def on_submit(self, sender, e):
                self.panel_type = self.txtPanelType.Text
                self.frame_type = self.txtFrameType.Text
                self.width = self.txtWidth.Text
                self.height = self.txtHeight.Text
                self.Close()
# Create and show the form
        form = UserDetailsForm(xaml_file_path)
        form.show_dialog()
# After the form is closed, access the inputs
        panel_type = form.panel_type.upper()
        frame_type = form.frame_type.upper()
        width = form.width.upper()
        height = form.height.upper()
        print(panel_type, frame_type, width, height)
#format of family name
        doorD, suffix = settings(frame_type)
        family_name = str.format(("08-Door_") + panel_type + ("_") + frame_type + suffix)
# Convert width and height to Revit internal units (feet)
        width = float(width) / 12.0
        height = float(height) / 12.0
# check to see if the info enters matches an existing door in the project. 
# #If yes, then check type, and if a new type, go to the edit function
        if check_fam(family_name, doc):
           # edit_types_and_params(family_name, panel_type, frame_type, width, height)  # Call function to edit an existing door
           print("edit_existing_door()")
        else:
# if new, use save_as_new_family
            save_as_new_family(family_name, panel_type, frame_type, width, height)
#if edit, use edit_types_and_parameters
    elif selected_action == 'Edit Existing Door':
        print("edit_existing_door()")
#If batch, load configs from csv file as per path below
    elif selected_action == 'Batch Add Door Families and Types':
# Load door configurations from the CSV file
        door_configs = load_door_configs_from_csv(csv_file_path)
# Now you can iterate over door_configs as before
        for confi in door_configs:
        # Unpack the configuration tuple into variables
            panel_type, frame_type, width, height = confi
                #format of family name
            doorD, suffix = settings(frame_type)
            family_name = "08-Door_" + panel_type + "_" + frame_type + suffix
# Convert width and height to Revit internal units (feet)
            width = float(width) / 12.0
            height = float(height) / 12.0
# Call save_as_new_family with the unpacked parameters
            save_as_new_family(family_name, panel_type, frame_type, width, height)
            print("Processed " + family_name + " with panel " + panel_type + ", frame " + frame_type + ", width " + str(width) + ", height " + str(height) + ".")
    else:
        print("No action selected or action canceled.")
#Print success message
    print("HOK Door Configurator finished {} at {} on {}".format(family_name, coreutils.current_time(), coreutils.current_date()))

#function to read batch door types from external csv file
def load_door_configs_from_csv(csv_file_path):
    door_configs = []
    with open(csv_file_path, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row:  # Ensure the row is not empty
                # Convert width and height to integers before appending
                door_configs.append((row[0], row[1], int(row[2]), int(row[3])))
    return door_configs

#function for mapping frame types to starting primitive family
def settings(frame_name):
    # Point to dictionary in config file where the keys are frame types and the values are source family primitives
    # Attempt to get the source family primitive for the given frame name
    # Unpack the tuple into doorD and suffix
    mapping = config.FRAME_TO_PRIMITIVE_MAPPING.get(frame_name, (None, None))
    doorD, suffix = mapping
    if doorD:
        print("The source family primitive for " + frame_name + " is " + doorD + ".")
        # Now return both the doorD and the suffix
        return doorD, suffix
    else:
        print("No action selected or action canceled.")
        return None, None
    
def check_fam(family_name, doc):
    collector = FilteredElementCollector(doc).OfClass(DB.Family)
    for family in collector:
        if family.Name == family_name:
            return True  # Family exists
    return False  # Family does not exist

def prompt_door_action():
    # Define the options to present to the user
    options = ['New Door', 'Edit Existing Door', 'Batch Add Door Families and Types']
    # Show the command switch window with the options
    selected_option = forms.CommandSwitchWindow.show(options, message='Select Door Action')
    # Return the selected option
    return selected_option

# Function to save door as new family
def save_as_new_family(family_name, panel_type, frame_type, width, height):
# Save the family with a new name
    temp_dir = tempfile.mkdtemp()
    family_path = os.path.join(temp_dir, family_name + ".rfa")
    backupf_path = os.path.join(temp_dir,"Backup")
    final_path = os.path.join(config.FINAL_FAMILY_PATH, family_name + ".rfa")
##This part below chooses whioch primitive door family to start from based on user frame type
#run dictionary function to pull base family name
    doorD, suffix = settings(frame_type)
    if doorD:       
        filCol = DB.FilteredElementCollector(doc)\
                    .OfCategory(BuiltInCategory.OST_Doors).WhereElementIsElementType()
# Iterate through the elements to find the one with the matching name
        for el in filCol:
            elFam = el.Family
           # print(elFam.Name)
            if elFam.Name == doorD:
                door = elFam
                break
    else: exit            
    print("making a new family...")
    print (str(family_name))
# Edit Family to bring up the family editor
    family_temp = (doc.EditFamily(door))#EditFamily must be called OUTSIDE of a transaction
#make new type and assign values
    typeName = "{}x{}".format(int(width*12), int(height*12))
    BamId = None
    FamId = None                
    FlamId = None
#start a transaction and instantiate family manager
    with Transaction(family_temp, 'Make Type and set Values') as trans:
        try:
            trans.Start()
            famMan = family_temp.FamilyManager
            famFamily = family_temp.OwnerFamily
            deleteType = famMan.CurrentType
            typeMake = famMan.NewType(typeName)
            print("making new type...")       
#these are the shared parameter GUIDs for the parameters we're looking for
            pwGU = config.PANEL_WIDTH_GUID #PANEL WIDTH PANEL 1
            phGU = config.PANEL_HEIGHT_GUID#PANEL HEIGHT
            pnGU = config.PANEL_TYPE_GUID #PANEL 1
            pfGU = config.FRAME_TYPE_GUID #FRAME
 #filtered element collector to grab nested door frame and panels
            print("updating parameters...")
            nestFams = DB.FilteredElementCollector(family_temp)\
                .OfClass(DB.Family).ToElements()
            for FamThis in nestFams:
                #print("type:{}".format(FamThis.Name))
                if FamThis.Name == panel_type:
                    BamId = FamThis
                elif FamThis.Name == frame_type:
                    FamId = FamThis
                else: 
                    FlamId = FamThis
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
        #set delete type as current type
                famMan.CurrentType = deleteType
                typeDel = famMan.DeleteCurrentType()
                famMan.CurrentType = typeMake  
                print("deleting embrionic type...")  
                trans.Commit()
        except Exception as e: 
            print("Error: {}".format(e))
            trans.RollBack()
#save as the family with new name and path
    family_temp.SaveAs(family_path, DB.SaveAsOptions())
    print("saving new file...")
#purge unused nested families function
    purge_perf_adv(family_temp)
# Load the saved family back into the project
    family_temp.SaveAs(final_path, DB.SaveAsOptions())
    print("loading new family into project...")
    with Transaction(doc, 'Load Family') as trans:
        trans.Start()
        family_loaded= doc.LoadFamily(family_path)
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
#THIS DOESN'T WORK YET, DON'T CALL IT
# open a transaction to make changes to things in Revit
    with Transaction(doc, 'Edit Types and Parameters') as trans:
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

                    # Set the new symbol's parameters as needed
                    new_symbol.LookupParameter(config.PARAMETER_NAMES["panel_width"]).Set(width)
                    new_symbol.LookupParameter(config.PARAMETER_NAMES["panel_height"]).Set(height)
                    # Rename the family symbol to reflect the new dimensions in inches
                    new_symbol.Name = "{}x{}".format(int(width*12), int(height*12))
                    break  # Exit after processing the first symbol
                break  # Exit after finding the family
        trans.Commit()

def purge_perf_adv(family_doc):
    purgeGuid = config.PURGE_GUID
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
# Deletes the elements
    print("it's purgin' time...")
    with Transaction(family_doc, 'Its purgin time') as s:
        s.Start()
        try:
            family_doc.Delete(purgableElementIds)
            #print("purge attempt 1")
        except:
            for e in purgableElementIds:
                try:
                    family_doc.Delete(e)
                        #print("purge attempt 2")
                except:
                        #print("no purge")
                    pass
        s.Commit()        
# Call the main function
main()
