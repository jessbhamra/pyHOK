# Import necessary libraries
from pyrevit import revit, DB
from pyrevit import forms

# Function to change door parameter
def change_door_parameter(door, parameter_name, new_value):
    param = door.LookupParameter(parameter_name)
    if param:
        param.Set(new_value)
    else:
        print(f"Parameter '{parameter_name}' not found on door.")

# Main function
def main():
    # Show a form to select a door family
    door_family = forms.select_familydoc(title='Select a Door Family')
    
    if door_family is None:
        print("No door family selected.")
        return

    # Show a form to input the parameter value
    new_value = forms.ask_for_string("Enter new parameter value")
    
    if new_value is None:
        print("No parameter value entered.")
        return

    # Get all doors of the selected family
    doors = DB.FilteredElementCollector(revit.doc)\
               .OfClass(DB.FamilyInstance)\
               .OfCategory(DB.BuiltInCategory.OST_Doors)\
               .WhereElementIsNotElementType()\
               .ToElements()

    doors = [door for door in doors if door.Symbol.Family.Name == door_family.Name]

    # Change the parameter for each door
    for door in doors:
        change_door_parameter(door, "YourParameterName", new_value)

# Call the main function
main()
