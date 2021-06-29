#!/usr/bin/python

import os
import random
import shutil

SOURCE_FOLDER = "C:/Users/synthbot/Desktop/Sorted Animation Assets"
DEST_FOLDER = "Z:/shared/sorted-animation-assets/samples"


def copy_files(root, files, target_folder):
    for f in files:
        source_file = os.path.join(root, f)
        dest_file = os.path.join(target_folder, f)
        print("copying", f, "from", root)
        shutil.copyfile(source_file, dest_file)


if __name__ == "__main__":
    for root, folders, files in os.walk(SOURCE_FOLDER):
        descent = os.path.relpath(root, SOURCE_FOLDER)
        target_folder = os.path.join(DEST_FOLDER, descent)

        try:
            os.mkdir(target_folder)
        except FileExistsError as e:
            pass

        if len(files) < 3:
            copy_files(root, files, target_folder)
            continue

        retained = random.sample(files, 3)
        copy_files(root, retained, target_folder)
