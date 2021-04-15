import io
import json
import os
import queue
import subprocess
import tempfile

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
			None
		).Detach()
	except:
		return io.StringIO('')

	file_descriptor = msvcrt.open_osfhandle(
		detached_handle, os.O_RDONLY)

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
		if event.src_path != f'{self.ipc}.completed':
			return
		self.q.put_nowait("completed")

	def messages(self):
		observer = Observer()
		monitor_dir = os.path.dirname(self.ipc)
		observer.schedule(self, monitor_dir, recursive=False)
		observer.start()

		unused_data = ""
		completed = False
		seek = 0

		while next_event := self.q.get():
			next_data = _read_offset(self.ipc, seek)
			seek += len(next_data)

			next_lines = next_data.split('\n')
			for completed_line in next_lines[:-1]:
				if completed_line.strip():
					yield f'{unused_data}{completed_line}'
					unused_data = ''

			unused_data = next_lines[-1]

			if next_event == "completed":
				if unused_data.strip():
					yield unused_data
				break

		observer.stop()


class AnimateInterface:
	def __init__(self, animate_path, memory_limit=None):
		self.animate_path = animate_path

	def open(self):
		# call run_script on an open.js script
		# wait until it's done
		pass

	def run_script(self, script_path, **kwargs):
		if "ipc" in kwargs:
			print("not allowed to assign the special variable 'ipc'")
			return

		with tempfile.TemporaryDirectory() as ipc_dirname:
			ipc_filename = f'{ipc_dirname}\\ipc.txt'
			kwargs["ipc"] = ipc_filename.replace("\\", "/");

			# escape the string for JavaScript
			for key in kwargs:
				kwargs[key] = json.dumps(kwargs[key])[1:-1]

			# generate the script with args filled in
			script = open(script_path).read()
			modified_script = ScriptTemplate(script).safe_substitute(**kwargs)

			modified_script_path = f'{ipc_dirname}\\script.jsfl'
			modified_script_file = open(modified_script_path, 'w')
			modified_script_file.write(modified_script)
			modified_script_file.close()

			# run the script
			subprocess.run([self.animate_path, modified_script_path])

			for msg in ScriptWatcher(ipc_filename).messages():
				yield msg

		# wait for results


		# write script to tmpfile
		# run animate.exe on the script
		# invoke callbacks on intermediate status messages
		# return the output

	def get_symbol_sample(self, filepath, symbolid):
		pass

	def dump_all_symbol_samples(self, filepath):
		pass

	def dump_full_symbol(self, filepath, symbolid):
		pass