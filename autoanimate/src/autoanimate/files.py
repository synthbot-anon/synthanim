import fnmatch
import html
import itertools
import io
import os
import re
import tkinter.filedialog
import zipfile

from .animate_interface import AnimateInterface
from .assets import AnimationAssets, SymbolFile


def walk_files(folder, filetypes):
    allowed_extensions = [x[1].split() for x in filetypes]
    allowed_extensions = list(itertools.chain(*allowed_extensions))

    def check_extension(filename):
        for allowed in allowed_extensions:
            if fnmatch.fnmatch(filename, allowed):
                return True

    for root, dirs, files in os.walk(folder):
        for f in files:
            if check_extension(f):
                yield os.path.join(root, f)


def select_source(args, filetypes):
    if args.batch:
        folder = select_input_folder("Select a source folder", args.input)
        return list(walk_files(folder, filetypes))

    else:
        file = select_input_file("Select a source file", args.input, filetypes)
        return [file]


def select_destination(args):
    return select_output_folder("Select a destination folder", args.output)


def select_input_file(prompt, path, filetypes):
    input(f"{prompt} [Enter]")
    result = path or tkinter.filedialog.askopenfilename(filetypes=filetypes)
    print("Selected:", result)
    return result


def select_output_file(prompt, path):
    input(f"{prompt} [Enter]")
    result = path or tkinter.filedialog.asksaveasfilename()
    print("Selected:", result)
    return result


def select_input_folder(prompt, path):
    input(f"{prompt} [Enter]")
    result = path or tkinter.filedialog.askdirectory(mustexist=True)
    print("Selected:", result)
    return result


def select_output_folder(prompt, path):
    input(f"{prompt} [Enter]")
    result = path or tkinter.filedialog.askdirectory(mustexist=False)
    print("Selected:", result)
    return result


def select_input_symbols(args):
    filetypes = [("Symbol Sample", "*.png")]
    if args.batch:
        result = select_input_folder("Select symbol samples folder", args.sample)
        return [SymbolFile(x) for x in walk_files(result, filetypes)]
    else:
        input("Select a symbol sample image [Enter]")
        result = args.sample or tkinter.filedialog.askopenfilename(filetypes=filetypes)
        print("Selected:", result)
        return [SymbolFile(result)]


def config_animate(args):
    return select_animate(args, get_confirmation=True)


def select_animate(args, get_confirmation=False):
    def save_and_create_interface(path):
        print("saving path:", path)
        args.config["DEFAULT"]["AdobeAnimateExe"] = path
        args.config.save()
        return AnimateInterface(path)

    def get_validation(path):
        if not path:
            return False

        if not get_confirmation:
            return True

        basename = os.path.basename(path).lower()
        if "animate" in basename and basename.endswith(".exe"):
            return True

        response = input("This doesn't look like Animate.exe. Are you sure? [y/n] ")
        return response.lower() == "y"

    if args.animate:
        print("Using", args.animate)
        if get_validation(args.animate):
            return save_and_create_interface(args.animate)

    if "AdobeAnimateExe" in args.config["DEFAULT"]:
        path = args.config["DEFAULT"]["AdobeAnimateExe"]

        if not get_confirmation:
            print("Using", path)
            return AnimateInterface(path)

        response = input(f"Do you want to reuse {path}? [y/n] ")
        if response.lower() == "y" and get_validation(path):
            print("Using", path)
            return AnimateInterface(path)

    response = input("Please select a version of Adobe Animate to use. [Enter]")

    path = tkinter.filedialog.askopenfilename(
        filetypes=[("Executable", "*.exe"), ("Any file", "*")]
    )

    print("Using", path)
    return save_and_create_interface(path)


def select_assets_folder(args):
    def save_and_create_interface(path):
        print("saving path:", path)
        args.config["DEFAULT"]["AnimationAssetsFolder"] = path
        args.config.save()
        return AnimationAssets(path)

    if args.assets:
        print("Using assets from", args.assets)
        return AnimationAssets(args.assets)

    if "AnimationAssetsFolder" in args.config["DEFAULT"]:
        path = args.config["DEFAULT"]["AnimationAssetsFolder"]
        response = input(f"Do you want to reuse the asset folder {path}? [y/n] ")
        if response.lower() == "y":
            print("Using", path)
            return AnimationAssets(path)

    result = select_input_folder("Select animation assets folder", args.assets)
    return save_and_create_interface(result)
