import argparse
import collections
import difflib
from glob import glob
import json
import os.path
import re
import queue
import shlex
import shutil
import tempfile
import time
import traceback
import webbrowser

import pandas
import xflsvg

from .config import SynthConfigParser, ConfigArgAction
from . import files
from .i_hate_windows import make_windows_usable


def print_deque(x):
    for item in x:
        print(item)


def dump_xfl(args):
    animate = files.select_animate(args)
    input_files = files.select_source(args, [("FLA file", "*.fla")])
    output_path = files.select_destination(args)

    # print_deque(animate.open_animate())

    input_files = list(input_files)
    ignore_prefix = os.path.dirname(os.path.commonprefix(input_files))
    ignore_prefix_len = len(ignore_prefix)
    
    for inp in input_files:
        relpath = inp[ignore_prefix_len:].lstrip('/\\')
        reldir = os.path.dirname(relpath)
        basename = os.path.splitext(os.path.basename(relpath))[0]
        outp = f"{os.path.join(output_path, reldir, basename)}.xfl"
        outdir = os.path.dirname(outp)

        if os.path.exists(f'{outdir}/{basename}'):
            continue

        os.makedirs(outdir, exist_ok=True)
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
    input_files = files.select_source(
        args, [("FLA file", "*.fla"), ("XFL file", "*.xfl")]
    )
    output_path = files.select_destination(args)

    print_deque(animate.open_animate())

    for inp in input_files:
        basename = os.path.splitext(os.path.basename(inp))[0]
        outp = os.path.join(output_path, basename)
        print_deque(animate.convert(sourceFile=inp, outputDir=outp))

        # clear personal data
        with open(f"{outp}/PublishSettings.xml") as publish_settings:
            data = publish_settings.read()
        data = re.sub(r"\\[^\\]*\\AppData", r"\\anonymous\\AppData", data)
        with open(f"{outp}/PublishSettings.xml", "w") as publish_settings:
            publish_settings.write(data)


def dump_shapes(args):
    animate = files.select_animate(args)
    input_files = files.select_source(
        args, [("FLA file", "*.fla"), ("XFL file", "*.xfl")]
    )
    output_path = files.select_destination(args)

    # print_deque(animate.open_animate())

    for inp in input_files:
        basename = os.path.splitext(os.path.basename(inp))[0]
        outp = os.path.join(output_path, basename)

        print_deque(animate.dump_xfl(sourceFile=inp, outputFile=f"{outp}.xfl"))

        # clear personal data
        with open(f"{outp}/PublishSettings.xml") as publish_settings:
            data = publish_settings.read()
        data = re.sub(r"\\[^\\]*\\AppData", r"\\Anonymous\\AppData", data)
        with open(f"{outp}/PublishSettings.xml", "w") as publish_settings:
            publish_settings.write(data)

        recorder = xflsvg.XflSvgRecorder(outp)
        for snapshot in recorder.frames.snapshots:
            snapshot.render()

        xflmap = recorder.get_shapes()

        shape_xfl_dir = os.path.join(outp, "__ppp_temp")
        shape_xfl_path = os.path.join(shape_xfl_dir, "xfl_template.xfl")
        recorder.to_shapes_xfl(shape_xfl_dir)

        spritemap_path = os.path.join(outp, "spritemaps")
        print_deque(animate.dump_shapes(shape_xfl_path, spritemap_path))

        xflmap_path = os.path.join(spritemap_path, "xflmap.json")
        with open(xflmap_path, "w+") as xflmap_file:
            xflmap_file.write(json.dumps(xflmap, indent=4))

        tables = recorder.to_pandas()
        shape_table = merge_shape_table(tables["pre-shapes"], spritemap_path, xflmap)
        
        pandas_path = os.path.join(outp, "tables")
        os.mkdir(pandas_path)
        tables['frames'].to_parquet(f'{pandas_path}/frames.parquet')
        shape_table.to_parquet(f'{pandas_path}/shapes.parquet')
        tables['assets'].to_parquet(f'{pandas_path}/assets.data.parquet')
        tables['documents'].to_parquet(f'{pandas_path}/documents.data.parquet')

        shutil.rmtree(shape_xfl_dir)


def merge_shape_table(xfl_shapes, spritemaps_dir, xflmap):
    with open(f"{spritemaps_dir}/spritemap.json") as spritemap_file:
        spritemap_data = spritemap_file.read()
        spritemap = json.loads(spritemap_data)

    spritemap_rows = []
    for sprite in spritemap["sprites"]:
        id = sprite["id"]
        xfl_data = xflmap[id]
        new_spritemap = (
            xfl_data["symbol"],
            xfl_data["layer"],
            xfl_data["frame"],
            xfl_data["elementIndexes"],
            sprite["filename"],
            sprite["svgObjectPrefix"],
            sprite["x"],
            sprite["y"],
            sprite["width"],
            sprite["height"],
            sprite["originX"],
            sprite["originY"],
            sprite["rescale"],
        )
        spritemap_rows.append(new_spritemap)

    spritemap_dataframe = pandas.DataFrame(
        data=spritemap_rows,
        columns=[
            "assetId",
            "layerIndex",
            "frameIndex",
            "elementIndexes",
            "filename",
            "svgObjectPrefix",
            "x",
            "y",
            "width",
            "height",
            "originX",
            "originY",
            "rescale",
        ],
    )

    return (
        xfl_shapes.merge(
            spritemap_dataframe,
            how="right",
            on=["assetId", "layerIndex", "frameIndex", "elementIndexes"],
        ).drop(columns=["assetId", "layerIndex", "frameIndex", "elementIndexes"])
    )


def debug(args):
    path = (
        r"C:\Users\synthbot\Desktop\berry-dest\dump-test\dump4\second-draft\MLP422_100"
    )

    with xflsvg.ShapeRecorder() as recorder:
        xfl = xflsvg.XflSvg(path)


class DataChecker:
    def __init__(self, value, sensitivity):
        self.value = value
        self.sensitivity = sensitivity
        self.matches = {}

    def _check_string(self, descr, filename, matcher, orig, string):
        match = matcher.find_longest_match()
        if match.size == 0:
            return

        match_str = string[match.b : match.b + match.size]

        ratio = difflib.SequenceMatcher(
            None, a=orig, b=match_str, autojunk=False
        ).ratio()
        if ratio < 1.0 - self.sensitivity:
            return

        print(descr, match_str)
        self.matches.setdefault(filename, []).append((ratio, match_str))

    def check_string(self, filename, string):
        literal_checker = difflib.SequenceMatcher(
            None, a=self.value, b=string, autojunk=False
        )
        self._check_string(
            "Literal match:", filename, literal_checker, self.value, string
        )

        lowercase_nospace_value = re.sub(r"\s", "", self.value.lower())
        lowercase_nospace = re.sub(r"\s", "", string.lower())
        lowercase_checker = difflib.SequenceMatcher(
            None, a=lowercase_nospace_value, b=lowercase_nospace, autojunk=False
        )
        self._check_string(
            "Normalized match:",
            filename,
            lowercase_checker,
            lowercase_nospace_value,
            lowercase_nospace,
        )

    def check_binary(self, filename, data):
        hex_data = " ".join("%02x" % x for x in data)
        hex_value = " ".join("%02x" % ord(x) for x in self.value)
        hex_checker = difflib.SequenceMatcher(
            None, a=hex_value, b=hex_data, autojunk=False
        )
        self._check_string("Hex match:", filename, hex_checker, hex_value, hex_data)

    def print_top_matches(self):
        print(" == Top matches ==")
        top_per_file = []
        for filename in self.matches:
            top_per_file.append(
                [filename, *max(self.matches[filename], key=lambda x: x[0])]
            )

        n = 10
        last_ratio = None

        for match in sorted(top_per_file, key=lambda x: x[1], reverse=True):
            ratio = match[1]

            if n == 0 and ratio < last_ratio:
                break

            print("%.1f%%" % (match[1] * 100), "match", f"({match[2]})", "in", match[0])
            if ratio < 1.0 and n > 0:
                n -= 1
                last_ratio = ratio


def check_data(args):
    input_dir = files.select_input_folder("Select a folder to check", None)
    check_str = input("Value to check for (incl. capitals and spaces): ").strip()
    sensitivity = float(input("Sensitivity (0.0 to 1.0, default 0.5): ").strip() or 0.5)
    checker = DataChecker(check_str, sensitivity)
    unchecked = []

    for root, dirs, filenames in os.walk(input_dir):
        for f in filenames:
            path = os.path.join(root, f)
            with open(path) as input_file:
                # print('=== Checking', path, '===')
                try:
                    data = input_file.read()
                    checker.check_string(path, data)
                except:
                    try:
                        with open(path, "rb") as input_file:
                            data = input_file.read()
                            checker.check_binary(path, data)
                    except:
                        unchecked.append(path)
                        raise

    checker.print_top_matches()
    if len(unchecked):
        print(" == Unable to check these files ==")
        print("\n".join(unchecked))


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
    data_location = (
        "https://drive.google.com/drive/u/2/folders/1kk8Xb5Xht4wahyHYOIVpMRtB69eg3Yhl"
    )
    have_animate = input(
        """
--- ---
The setup process does four things:
  1. If needed, walk you through downloading Adobe Animate.
  2. It walks you through downloading the data.

You can quit at any time by pressing Ctrl+Shift+C simultaneously. [Enter]
"""
    )
    open_browser = input(
        f"""
--- ---
To run Adobe Animate, you'll first need to install Microsoft Visual
C++. If you don't already have it installed (or don't know), you
should try installing it now. Do you want to open a browser to the
download page? [y/n]
"""
    )
    if open_browser and open_browser[0].lower() == "y":
        proceed = input(
            """
When your browser opens to the page, look for the section titled
"Visual Studio 2015, 2017 and 2019". [Enter]
"""
        )
        webbrowser.open(vcpp_location)

    open_browser = input(
        f"""
--- ---
Once you have Visual C++ installed, you'll need the patched Adobe
Animate. The patched Adobe Animate is here under
"Adobe Animate 21.0.5.zip":
- {animate_location}
Do you want to open a browser to this location? [y/n]
"""
    )
    if open_browser and open_browser[0].lower() == "y":
        webbrowser.open(animate_location)

    input(
        """
--- ---
Unzip the file to any location. The password is iwtcird. Once you do,
come back here and hit enter to continue. Inside the unzipped folder,
you'll see a file called "Animate - fully patched.exe". In the next
step, make sure to select that file. [Enter]
"""
    )

    animate = files.config_animate(args)

    open_browser = input(
        f"""
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
    if open_browser and open_browser[0].lower() == "y":
        webbrowser.open(data_location)

    input(
        """
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
  check-data
  - This will ask for a directory and a value, and it will check the
    directory for any occurences of that value. This is intended to check
    for personal data that might have been written to a file. It will check
    both binary and text files, ignoring case and spaces, partial and
    complete matches. It will output the top matches, along with any files
    it's unable to check for whatever reason.

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
"""
    )


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

    cmd_dump_shapes = subparsers.add_parser("dump-shapes")
    cmd_dump_shapes.add_argument("--batch", action="store_true")
    cmd_dump_shapes.add_argument("--input", type=str, metavar="file|folder")
    cmd_dump_shapes.add_argument("--output", type=str, metavar="folder")

    cmd_debug = subparsers.add_parser("debug")
    cmd_debug.add_argument("--input", type=str, metavar="file|folder")
    cmd_debug.add_argument("--batch", action="store_true")

    cmd_setup = subparsers.add_parser("setup")
    cmd_check_data = subparsers.add_parser("check-data")
    run_tests_parser = subparsers.add_parser("run-tests")

    handlers = {
        "setup": setup,
        "dump-xfl": dump_xfl,
        "dump-samples": dump_samples,
        "dump-texture-atlas": dump_texture_atlas,
        "convert": convert,
        "dump-shapes": dump_shapes,
        "run-tests": run_tests,
        "check-data": check_data,
        "debug": debug,
    }

    print(
        """Here are the basic commands:
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
  check-data
  - This will ask for a directory and a value, and it will check the
    directory for any occurences of that value. This is intended to check
    for personal data that might have been written to a file. It will check
    both binary and text files, ignoring case and spaces, partial and
    complete matches. It will output the top matches, along with any files
    it's unable to check for whatever reason.

You can add --batch to all of these. When you add, it will ask for folders
instead of files. For example:
  dump-xfl --batch
  - This will convert a folder of FLA files, and it will search all sub-
  directories.

Adobe Animate will take focus when you execute any of these commands.
REMEMBER that you can always hit Ctrl+Shift+C to stop the script. This will
be important if you're running a long batch process and want to stop in
the middle."""
    )

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
    try:
        main()
    except Exception as err:
        print(err)
        traceback.print_exc()
    input('Press any key to continue')
