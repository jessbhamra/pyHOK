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
FRAME_TO_PRIMITIVE_MAPPING = {
        "D01": "DoorConfigPrimative02",
        "S02": "DoorConfigPrimative02",
        "S03": "DoorConfigPrimative02",
        "D03A": "DoorConfigPrimativeSidelite01",
        "D03B": "DoorConfigPrimativeSidelite01",
        "D03C": "DoorConfigPrimativeSidelite01",
        "D04A": "DoorConfigPrimativeSidelite01",
        "D04B": "DoorConfigPrimativeSidelite01",
        "D04C": "DoorConfigPrimativeSidelite01",
        "D05A": "DoorConfigPrimativeSidelite01",
        "D05B": "DoorConfigPrimativeSidelite01",
        "D05C": "DoorConfigPrimativeSidelite01",
        "D06A": "DoorConfigPrimativeSidelite01",
        "D06B": "DoorConfigPrimativeSidelite01",
        "D06C": "DoorConfigPrimativeSidelite01",
        "D07A": "DoorConfigPrimativeSidelite01",
        "D07B": "DoorConfigPrimativeSidelite01",
        "D07C": "DoorConfigPrimativeSidelite01",
        "S21": "DoorConfigPrimativeSidelite01",
        "S22": "DoorConfigPrimativeSidelite01",
        "S23": "DoorConfigPrimativeSidelite01",
        "D02": "DoorConfigPrimativeDouble01"
}

# Family name suffix
FAMILY_NAME_SUFFIX = "_SingleSwing_HOK_I"

# Revit parameter names
PARAMETER_NAMES = {
    "panel_width": "PANEL WIDTH PANEL 1",
    "panel_height": "PANEL HEIGHT",

}