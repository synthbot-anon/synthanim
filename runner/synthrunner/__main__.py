import argparse
import collections
from glob import glob
import os.path
import re
import queue
import shlex
import sys
import tempfile
import time
import traceback
import webbrowser

from .config import SynthConfigParser, ConfigArgAction
from synthrunner import files
from .i_hate_windows import make_windows_usable

def print_deque(x):
    for item in x:
        print(item)

def dump_xfl(args):
    animate = files.select_animate(args)
    input_files = files.select_source(args, [("FLA file", "*.fla")])
    output_path = files.select_destination(args)

    print_deque(animate.open_animate())

    for inp in input_files:
        basename = os.path.splitext(os.path.basename(inp))[0]
        outp = f"{os.path.join(output_path, basename)}.xfl"
        print_deque(animate.dump_xfl(sourceFile=inp, outputFile=outp))


def dump_texture_atlas(args):
    animate = files.select_animate(args)
    assets = files.select_assets_folder(args)
    assets.collect_files()

    input_symbols = files.select_input_symbols(args)
    output_path = files.select_destination(args)

    # collect symbol files into fla file buckets
    buckets = {}
    for symbolFile in input_symbols:
        destination = buckets.setdefault(symbolFile.fla_name, [])
        destination.append(symbolFile)

    print_deque(animate.open_animate())

    for fla_name in buckets:
        source_file = assets.get_path(f"{fla_name}.fla")
        print("checking:", fla_name, "got", source_file)
        if not source_file:
            continue

        samples = []
        for symbolFile in buckets[fla_name]:
            symbol_name = symbolFile.symbol_name
            dest_folder = os.path.join(output_path, fla_name, symbol_name).replace(
                "\\", "/"
            )
            os.makedirs(dest_folder, exist_ok=True)
            samples.append({"symbolName": symbol_name, "destFolder": dest_folder})

        command = {"sourceFile": source_file, "samples": samples}

        print_deque(animate.dump_texture_atlas(command))


def dump_samples(args):
    animate = files.select_animate(args)
    input_files = files.select_source(args, [("Animation file", "*.fla *.xfl")])
    output_folder = files.select_destination(args)

    print_deque(animate.open_animate())

    print("Dumping samples...")
    for inp in input_files:
        print_deque(animate.dump_symbol_samples(inp, output_folder))
    print("Done")

def convert(args):
    animate = files.select_animate(args)
    input_files = files.select_source(args, [("FLA file", "*.fla"), ("XFL file", "*.xfl")])
    output_path = files.select_destination(args)

    print_deque(animate.open_animate())

    for inp in input_files:
        basename = os.path.splitext(os.path.basename(inp))[0]
        outp = f"{os.path.join(output_path, basename)}"
        print_deque(animate.convert(sourceFile=inp, outputDir=outp))


def run_tests(args):
    animate = files.select_animate(args)
    print("Make sure Adobe Animate doesn't show any popups during this test.")

    print()
    print("Opening Animate... ", end="", flush=True)
    print_deque(animate.open_animate())
    print("Done", flush=True)

    print("[Test] Checking ActionScript2 popup... ", end="", flush=True)
    print_deque(
        animate.open_file(sourceFile="./animate-tests/popup - as2 deprecation.fla")
    )
    print("Done", flush=True)

    print("[Test] Checking bitmap size popup... ", end="", flush=True)
    with tempfile.TemporaryDirectory() as temp_dirpath:
        print_deque(
            animate.dump_symbol_samples(
                sourceFile="./animate-tests/popup - bitmap too large.fla",
                outputDir=temp_dirpath,
            )
        )
    print("Done", flush=True)

    print("[Test] Checking missing font popup... ", end="", flush=True)
    print_deque(
        animate.open_file(sourceFile="./animate-tests/popup - missing font.fla")
    )
    print("Done", flush=True)

    print("[Test] Checking invalid file popup... ", end="", flush=True)
    print_deque(
        animate.open_file(
            sourceFile="./animate-tests/popup - file cannot be opened.fla"
        )
    )
    print("Done", flush=True)

    print()
    print("Done running tests.")


def setup(args):
    vcpp_location = "https://support.microsoft.com/en-us/topic/the-latest-supported-visual-c-downloads-2647da03-1eea-4433-9aff-95f26a218cc0"
    animate_location = "https://drive.google.com/drive/folders/17hgz4fbIqYetvxHh2MX1KdTP6efIauUU?usp=sharing"
    data_location = "https://drive.google.com/drive/u/2/folders/1kk8Xb5Xht4wahyHYOIVpMRtB69eg3Yhl"
    have_animate = input("""
--- ---
The setup process does four things:
  1. If needed, walk you through downloading Adobe Animate.
  2. It walks you through downloading the data.

You can quit at any time by pressing Ctrl+Shift+C simultaneously. [Enter]
""")
    open_browser = input(f"""
--- ---
To run Adobe Animate, you'll first need to install Microsoft Visual
C++. If you don't already have it installed (or don't know), you
should try installing it now. Do you want to open a browser to the
download page? [y/n]
""")
    if open_browser and open_browser[0].lower() == 'y':
        proceed = input("""
When your browser opens to the page, look for the section titled
"Visual Studio 2015, 2017 and 2019". [Enter]
""")
        webbrowser.open(vcpp_location)

    open_browser = input(f"""
--- ---
Once you have Visual C++ installed, you'll need the patched Adobe
Animate. The patched Adobe Animate is here under
"Adobe Animate 21.0.5.zip":
- {animate_location}
Do you want to open a browser to this location? [y/n]
""")
    if open_browser and open_browser[0].lower() == 'y':
        webbrowser.open(animate_location)

    input("""
--- ---
Unzip the file to any location. The password is iwtcird. Once you do,
come back here and hit enter to continue. Inside the unzipped folder,
you'll see a file called "Animate - fully patched.exe". In the next
step, make sure to select that file. [Enter]
""")

    animate = files.config_animate(args)

    open_browser = input(f"""
--- ---
Done with step 1. Next, you should download the animation files and
symbol labels. You can download as much of or as little of the animation
files as you want, depending on what you want to do. The full dataset is
192 gigabytes. There's a random sample of the dataset that's only 900 MB.
The labels are only 200 MB.

You can find all of the files here:
  - {data_location}
  - Animation Assets are in mlp-animation-assets. Download parts of this
    if you want to help create the dataset. If you're doing this, post in
    the thread so we can coordinate efforts.
  - Sample of assets are in mlp-animation-samples. If you only want to play
    around with some data for testing purposes, you can download this instead
    of the full Animation Assets data. Make sure to unzip it. There's no
    password.
  - Symbol labels are in mlp-animation-symbol-labels. This data tells the
    script which animation symbols represent full characters, as opposed to
    partial characters (like eyes and hooves) or objects. Download this
    regardless of how you're using this tool. Make sure to unzip it. There's
    no password.

The link to these assets is in the thread. Do you want to open a browser
to the link? [y/n]
"""
)
    if open_browser and open_browser[0].lower() == 'y':
        webbrowser.open(data_location)

    input("""
--- ---
That's all. You can download the files as needed. You don't need to run this
everytime you run the script. Your setup will persist in the file config.txt.

Here are the basic commands:
  convert
  - This will ask for an FLA file and a destination. It will convert the
    FLA to XFL and it will convert all shape objects to SVG. This is the
    command for converting FLA into a usable format.
  dump-samples
  - This will ask for an animation file and a destination. It will dump a
    sample image of every symbol in the animation file. This is the command
    for turning FLA into files we can label easily.
  dump-xfl
  - This will ask for an FLA file and a destination. It will convert the
    FLA to XFL.
  dump-texture-atlas
  - This will ask for an Animation Assets directory, a symbol sample
    image (which you can get from dump-samples), and a destination folder.
    It will dump the animation data for that symbol in texture atlas format.

You can add --batch to all of these. When you add, it will ask for folders
instead of files. For example:
  dump-xfl --batch
  - This will convert a folder of FLA files, and it will search all sub-
  directories.

Adobe Animate will take focus when you execute any of these commands.
REMEMBER that you can always hit Ctrl+Shift+C to stop the script. This will
be important if you're running a long batch process and want to stop in
the middle.

Cheers. [Enter]
--- ---
""")


def main():
    make_windows_usable()

    default_config = SynthConfigParser()
    default_config.read("./config.txt")

    parser = argparse.ArgumentParser(description="Automate Adobe Animate")
    parser.add_argument("--animate", type=str, metavar="C:/Animate.exe")
    parser.add_argument(
        "--config", type=str, default=default_config, action=ConfigArgAction
    )

    subparsers = parser.add_subparsers(title="commands", dest="command")

    cmd_dump_xfl_parser = subparsers.add_parser("dump-xfl")
    cmd_dump_xfl_parser.add_argument("--batch", action="store_true")
    cmd_dump_xfl_parser.add_argument("--input", type=str, metavar="file|folder")
    cmd_dump_xfl_parser.add_argument("--output", type=str, metavar="folder")

    cmd_dump_samples_parser = subparsers.add_parser("dump-samples")
    cmd_dump_samples_parser.add_argument("--batch", action="store_true")
    cmd_dump_samples_parser.add_argument("--input", metavar="file|folder")
    cmd_dump_samples_parser.add_argument("--output", metavar="folder")

    cmd_dump_texture_atlas = subparsers.add_parser("dump-texture-atlas")
    cmd_dump_texture_atlas.add_argument("--batch", action="store_true")
    cmd_dump_texture_atlas.add_argument("--assets", metavar="folder")
    cmd_dump_texture_atlas.add_argument("--sample", metavar="file|folder")
    cmd_dump_texture_atlas.add_argument("--output", metavar="folder")

    cmd_convert = subparsers.add_parser("convert")
    cmd_convert.add_argument("--batch", action="store_true")
    cmd_convert.add_argument("--input", type=str, metavar="file|folder")
    cmd_convert.add_argument("--output", type=str, metavar="folder")

    cmd_setup = subparsers.add_parser("setup")

    run_tests_parser = subparsers.add_parser("run-tests")

    handlers = {
        "setup": setup,
        "dump-xfl": dump_xfl,
        "dump-samples": dump_samples,
        "dump-texture-atlas": dump_texture_atlas,
        "convert": convert,
        "run-tests": run_tests,
    }

    print("""Here are the basic commands:
  setup
  - This will walk you through setting up Adobe Animate and the animation
    data.
  convert
  - This will ask for an FLA file and a destination. It will convert the
    FLA to XFL and it will convert all shape objects to SVG. This is the
    command for converting FLA into a usable format.
  dump-samples
  - This will ask for an animation file and a destination. It will dump a
    sample image of every symbol in the animation file. This is the command
    for turning FLA into files we can label easily.
  dump-xfl
  - This will ask for an FLA file and a destination. It will convert the
    FLA to XFL.
  dump-texture-atlas
  - This will ask for an Animation Assets directory, a symbol sample
    image (which you can get from dump-samples), and a destination folder.
    It will dump the animation data for that symbol in texture atlas format.

You can add --batch to all of these. When you add, it will ask for folders
instead of files. For example:
  dump-xfl --batch
  - This will convert a folder of FLA files, and it will search all sub-
  directories.

Adobe Animate will take focus when you execute any of these commands.
REMEMBER that you can always hit Ctrl+Shift+C to stop the script. This will
be important if you're running a long batch process and want to stop in
the middle.""")

    while True:
        command = input("celestia@animation-data:.$ ")
        if not command:
            continue

        try:
            command_parts = shlex.split(command)
            if command_parts[0] == "exit":
                break
            args = parser.parse_args(command_parts)
        except:
            continue

        handlers[args.command](args)


if __name__ == "__main__":
    main()
