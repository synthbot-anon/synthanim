import os
import re


_EXPLICIT_FLA = re.compile(r"f-(.*)\.fla", re.IGNORECASE)
_EXPLICIT_SYM = re.compile(r"s-(.*)_f[0-9]{0,4}\.sym", re.IGNORECASE)
_EXPLICIT_SHORTSYM = re.compile(r"s-(.*)\.sym", re.IGNORECASE)


class SymbolFile:
    def __init__(self, full_path, rel_path=None):
        self.full_path = full_path
        self._fla_name = None
        self._symbol_name = None
        self._full_name = None
        self._base_name = None
        self._ext = None

    @property
    def fla_name(self):
        if self._fla_name:
            return self._fla_name

        for file_part in self.full_path.split(os.sep)[::-1]:
            matches = _EXPLICIT_FLA.search(file_part)
            if matches:
                self._fla_name = matches.group(1)
                return self._fla_name

        raise Exception("Missing FLA file in path: %s" % (self.full_path,))

    @property
    def symbol_name(self):
        if self._symbol_name:
            return self._symbol_name

        for file_part in self.full_path.split(os.sep)[::-1]:
            matches = _EXPLICIT_SYM.search(file_part)
            if matches:
                self._symbol_name = matches.group(1)
                return self._symbol_name

        for file_part in self.full_path.split(os.sep)[::-1]:
            matches = _EXPLICIT_SHORTSYM.search(file_part)
            if matches:
                self._symbol_name = matches.group(1)
                return self._symbol_name

        raise Exception("Missing symbol name in path: %s" % (self.full_path,))

    def _parse_base_ext(self):
        base_name, ext = os.path.splitext(self.full_name)
        self._base_name = base_name
        self._ext = ext[1:]

    @property
    def base_name(self):
        if self._base_name:
            return self._base_name

        self._parse_base_ext()
        return self._base_name

    @property
    def extension(self):
        if self._ext:
            return self._ext

        self._parse_base_ext()
        return self._ext


# class SymbolLabels:
#     def __init__(self, path):
#         self.path = path

#     def collect_files(self):
#         for root, dirs, files in os.walk(self.path):
#             for fn in files:
#                 full_path = os.path.join(root, fn)
#                 rel_path = os.path.relpath(full_path, start=self.path)
#                 yield SymbolFile(full_path, rel_path)


class AnimationAssets:
    def __init__(self, path):
        self.path = path
        self.files = {}

    def collect_files(self):
        for root, dirs, files in os.walk(self.path):
            for fn in files:
                full_path = os.path.join(root, fn)
                self.files[fn.lower()] = full_path.replace("\\", "/")

    def get_path(self, short_name):
        return self.files.get(short_name.lower(), None)
