import os
import shutil

def move_files_with_extension(source_folder, backup_folder, extension='.0001.rvt'):
    # Check if the source folder exists
    if not os.path.isdir(source_folder):
        print("The source folder " + source_folder + " does not exist.")
        return

    # Create the backup folder if it doesn't exist
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)

    # List all files in the source folder
    files = os.listdir(source_folder)
    
    # Filter files with the specific extension
    files_to_move = [file for file in files if file.endswith(extension)]
    
    # Move each file
    for file in files_to_move:
        source_path = os.path.join(source_folder, file)
        backup_path = os.path.join(backup_folder, file)
        try:
            shutil.move(source_path, backup_path)
            print("Moved file: " + source_path + " to " + backup_path)
        except Exception as e:
            print("Failed to move " + source_path + ": " + str(e))

# Example usage
source_folder = 'R:\\FWR\\RESOURCES\\BIM-STAGING\\RVT-DRAFT\\Doors v2\\Security\\ALL DOORS BETA'
backup_folder = 'R:\\FWR\\RESOURCES\\BIM-STAGING\\RVT-DRAFT\\Doors v2\\Security\\ALL DOORS BETA\\Backup2'
move_files_with_extension(source_folder, backup_folder)