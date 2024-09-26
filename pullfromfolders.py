import os
import shutil

def extract_files_to_parent(parent_folder):
    for root, dirs, files in os.walk(parent_folder, topdown=False):
        for name in files:
            file_path = os.path.join(root, name)
            new_path = os.path.join(parent_folder, name)
            
            # Move the file to the parent folder
            if os.path.exists(new_path):
                # If a file with the same name exists in the parent folder, append a number to the filename
                base, ext = os.path.splitext(name)
                counter = 1
                while os.path.exists(new_path):
                    new_path = os.path.join(parent_folder, "{}_{}{}".format(base, counter, ext))
                    counter += 1
            shutil.move(file_path, new_path)

        for name in dirs:
            dir_path = os.path.join(root, name)
            # Remove the empty directories
            if dir_path != parent_folder:
                shutil.rmtree(dir_path)

# Example usage:
parent_folder = "B:\\Revit Projects\\__drafts\\doors temp"
extract_files_to_parent(parent_folder)
