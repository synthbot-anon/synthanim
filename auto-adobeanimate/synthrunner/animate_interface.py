import atexit
import io
import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading

from string import Template
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import msvcrt
import win32file


def _readonly_file(filename):
    try:
        detached_handle = win32file.CreateFile(
            filename,
            win32file.GENERIC_READ,
            win32file.FILE_SHARE_DELETE
            | win32file.FILE_SHARE_READ
            | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_ATTRIBUTE_NORMAL,
            None,
        ).Detach()
    except:
        return io.StringIO("")

    file_descriptor = msvcrt.open_osfhandle(detached_handle, os.O_RDONLY)

    return open(file_descriptor)


def _read_offset(filename, offset):
    file = _readonly_file(filename)
    file.seek(offset)
    return file.read()


class ScriptTemplate(Template):
    delimiter = "%"


class ScriptWatcher(FileSystemEventHandler):
    def __init__(self, ipc):
        self.ipc = ipc
        self.q = queue.Queue()

    def on_modified(self, event):
        if event.src_path != self.ipc:
            return
        self.q.put_nowait("update")

    def on_created(self, event):
        if event.src_path != f"{self.ipc}.completed":
            return

        self.completed = True
        self.q.put_nowait("creation")

    def start_watching(self):
        self.observer = Observer()
        monitor_dir = os.path.dirname(self.ipc)
        self.observer.schedule(self, monitor_dir, recursive=False)
        self.observer.start()

    def messages(self):
        unused_data = ""
        seek = 0

        while True:
            next_data = _read_offset(self.ipc, seek)
            seek += len(next_data)

            next_lines = next_data.split("\n")
            for completed_line in next_lines[:-1]:
                if completed_line.strip():
                    yield f"{unused_data}{completed_line}"
                    unused_data = ""

            unused_data = next_lines[-1]

            if os.path.exists(f"{self.ipc}.completed"):
                if unused_data.strip():
                    yield unused_data
                break

            try:
                next_event = self.q.get(timeout=0.1)
            except queue.Empty:
                pass

    def stop_watching(self):
        self.observer.stop()


def run_async(*args, **kwargs):
    def subprocess_run():
        proc = subprocess.run(*args, **kwargs)

    threading.Thread(target=subprocess_run, daemon=True).start()


class AnimateInterface:
    def __init__(self, animate_path, memory_limit=None):
        self.animate_path = animate_path

    def open_animate(self):
        return self.run_script("./animate-scripts-dist/OpenAnimate.jsfl")

    def close(self):
        pass

    def restart(self):
        pass

    def run_script(self, script_path, **kwargs):
        if "ipc" in kwargs:
            print("not allowed to assign the special variable 'ipc'")
            return

        ipc_dirname = tempfile.mkdtemp(prefix="ppp_")
        atexit.register(shutil.rmtree, ipc_dirname, ignore_errors=True)

        ipc_filename = f"{ipc_dirname}\\ipc.txt"
        kwargs["ipc"] = ipc_filename.replace("\\", "/")

        # escape the string for JavaScript
        for key in kwargs:
            kwargs[key] = json.dumps(kwargs[key])[1:-1]

        # generate the script with args filled in
        script = open(script_path).read()
        modified_script = ScriptTemplate(script).safe_substitute(**kwargs)

        modified_script_path = f"{ipc_dirname}\\script.jsfl"
        modified_script_file = open(modified_script_path, "w")
        modified_script_file.write(modified_script)
        modified_script_file.close()

        # run the script
        watcher = ScriptWatcher(ipc_filename)
        watcher.start_watching()

        run_async([self.animate_path, modified_script_path, "-AlwaysRunJSFL"])
        for msg in watcher.messages():
            yield msg

        watcher.stop_watching()

    def test_animate(self):
        return self.run_script(
            "./animate-scripts-dist/TestAnimate.jsfl", input="success"
        )

    def dump_symbol_samples(self, sourceFile, outputDir):
        return self.run_script(
            "./animate-scripts-dist/DumpSymbolSamples.jsfl",
            sourceFile=os.path.realpath(sourceFile).replace("\\", "/"),
            outputDir=os.path.realpath(outputDir).replace("\\", "/"),
        )

    def dump_texture_atlas(self, symbols):
        print(symbols)
        return self.run_script(
            "./animate-scripts-dist/DumpTextureAtlas.jsfl",
            symbols=json.dumps(symbols),
        )

    def dump_xfl(self, sourceFile, outputFile):
        return self.run_script(
            "./animate-scripts-dist/DumpXFL.jsfl",
            sourceFile=os.path.realpath(sourceFile).replace("\\", "/"),
            outputFile=os.path.realpath(outputFile)
            .replace("\\", "/")
            .replace(":", "|"),
        )

    def convert(self, sourceFile, outputDir):
        return self.run_script(
            "./animate-scripts-dist/Convert.jsfl",
            sourceFile=os.path.realpath(sourceFile).replace("\\", "/"),
            outputDir=os.path.realpath(outputDir).replace("\\", "/"),
        )

    def dump_shapes(self, sourceFile, outputDir):
        return self.run_script(
            "./animate-scripts-dist/DumpShapes.jsfl",
            sourceFile=os.path.realpath(sourceFile).replace("\\", "/"),
            outputDir=os.path.realpath(outputDir).replace("\\", "/"),
        )

    def open_file(self, sourceFile):
        return self.run_script(
            "./animate-scripts-dist/TestFile.jsfl",
            sourceFile=os.path.realpath(sourceFile).replace("\\", "/"),
        )

    def debug(self, sourceFile):
        return self.run_script(
            "./animate-scripts-dist/Debug.jsfl",
            sourceFile=os.path.realpath(sourceFile).replace("\\", "/"),
        )
