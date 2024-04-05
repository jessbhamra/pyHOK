# config.py
#Configuration file for door builder to make it easier to swap this stuff up

# Paths
ICON_PATH = "C:\\Users\\Jess.Bhamra\\OneDrive - HOK\\Documents\\GitHub\\DoorConfig\\Doors.extension\\pyHOK.tab\\HOK Tools.panel\\Door Configurator.pushbutton\\HOK.ico"
XAML_FILE_PATH = "C:\\Users\\Jess.Bhamra\\OneDrive - HOK\\Documents\\GitHub\\DoorConfig\\Doors.extension\\pyHOK.tab\\HOK Tools.panel\\Door Configurator.pushbutton\\rDetailsForm.xaml"
CSV_FILE_PATH = "B:\\Revit Projects\\_python tests\\door_configs4.csv"
FINAL_FAMILY_PATH = "B:\\Revit Projects\\security doors temp\\try5\\"

# GUIDs for parameters
PANEL_WIDTH_GUID = "318d67dd-1f5f-43fb-a3d0-32ac31f1babb"
PANEL_HEIGHT_GUID = "3e7f226e-bc78-407c-982a-d45a405cd2a9"
PANEL_TYPE_GUID = "8e89f65d-3ed9-45c8-9808-8c315dedadce"
FRAME_TYPE_GUID = "b6930f0e-c0f5-432b-80ee-6c649f876cae"

# Purge GUID
PURGE_GUID = 'e8c63650-70b7-435a-9010-ec97660c1bda'

# Frame to primitive mapping
# Frame to primitive mapping with family name suffix
FRAME_TO_PRIMITIVE_MAPPING = {
    "S01": ("DoorConfigPrimative02", "_SingleSwing_HOK_I"),
    "S02": ("DoorConfigPrimative02", "_SingleSwing_HOK_I"),
    "S03": ("DoorConfigPrimative02", "_SingleSwing_HOK_I"),
    "D03A": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D03B": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D03C": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D04A": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D04B": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D04C": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D05A": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D05B": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D05C": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D06A": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D06B": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D06C": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D07A": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D07B": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D07C": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "S21": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "S22": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "DS1": ("DoorConfigPrimativeSingleSliding02", "_SingleSliding_HOK_I"),
    "S23": ("DoorConfigPrimativeSidelite01", "_SingleSwing_HOK_I"),
    "D02": ("DoorConfigPrimativeDouble01", "_DoubleSwing_HOK_I")
}


# Revit parameter names
PARAMETER_NAMES = {
    "panel_width": "PANEL WIDTH PANEL 1",
    "panel_height": "PANEL HEIGHT",

}