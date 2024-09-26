import os
import shutil

def copy_txt_for_revit_families(txt_file_path, revit_family_folder):
    """
    Copies a specified .txt file for each Revit family (.rfa) in a specified folder,
    naming the copies after the Revit families.

    :param txt_file_path: Path to the .txt file to be copied.
    :param revit_family_folder: Folder containing Revit family files (.rfa).
    """
    # Ensure the .txt file exists
    if not os.path.isfile(txt_file_path):
        print("Error: The file {} does not exist.".format(txt_file_path))
        return

    # Ensure the folder exists
    if not os.path.isdir(revit_family_folder):
        print("Error: The folder {} does not exist.".format(revit_family_folder))
        return

    # Iterate over all files in the specified folder
    for filename in os.listdir(revit_family_folder):
        if filename.lower().endswith('.rfa'):  # Check if the file is a Revit family file
            # Construct the full path to the current Revit family file
            family_path = os.path.join(revit_family_folder, filename)
            # Construct the new .txt file name based on the Revit family file name
            new_txt_file_name = os.path.splitext(filename)[0] + '.txt'
            new_txt_file_path = os.path.join(revit_family_folder, new_txt_file_name)
            # Copy the .txt file
            shutil.copy(txt_file_path, new_txt_file_path)
            print("Copied {} to {}".format(txt_file_path, new_txt_file_path))


txt_file_path = 'B:\\Revit Projects\\security doors temp\\TYPECATALOG.txt'
revit_family_folder = 'B:\\Revit Projects\\security doors temp\\TRY8'
copy_txt_for_revit_families(txt_file_path, revit_family_folder)