import copy
import json
import os
import shutil

from bs4 import BeautifulSoup, element

from . import xflsvg


TEMPLATE_PATH = f"{os.path.dirname(__file__)}/xfl_template"

class RecordingSVGSnapshot(xflsvg.Snapshot):
    def __init__(self, identifier, loader):
        super().__init__()
        self.identifier = identifier
        self.loader = loader

    def render(self, context):
        context.record(self.identifier, self.owner)


class RecordingTransformedSnapshot(xflsvg.Snapshot):
    def __init__(self, child, origin, matrix):
        super().__init__()
        self.child = child

    def render(self, context):
        self.child.render(context)


class RecordingXflSvg(xflsvg.XflSvg):
    def __init__(self, xflsvg_dir):
        super().__init__(RecordingSVGSnapshot, RecordingTransformedSnapshot, xflsvg_dir)
        self.shapes = set()
        self.elements = {}

        for snapshot in self.frames.snapshots:
            snapshot.render(self)

    def record(self, identifier, element):
        self.shapes.add(identifier)
        self.elements[identifier] = element

    def to_json(self):
        data = []
        for index, identifier in enumerate(self.shapes):
            data.append(
                {
                    "id": index,
                    "symbol": identifier[0],
                    "layer": identifier[1],
                    "frame": identifier[2],
                    "elementIndexes": identifier[3],
                }
            )

        return json.dumps(data, indent=4)

    def to_xfl(self, output):
        os.makedirs(output, exist_ok=True)
        try:
            shutil.rmtree(output)
        except:
            pass

        template_path = TEMPLATE_PATH
        shutil.copytree(template_path, output)
        target_symbol = os.path.join(output, "LIBRARY/SymbolName.xml")
        with open(target_symbol) as template:
            soup = BeautifulSoup(template, "xml")

        base_frame = soup.DOMFrame
        element_bundle = base_frame.parent
        soup.DOMFrame.extract()

        for index, identifier in enumerate(self.shapes):
            element = self.elements[identifier]
            clone = copy.copy(base_frame)
            clone["index"] = index
            clone.DOMShape.replace_with(element.xmlnode)
            element_bundle.append(clone)

        with open(target_symbol, "w") as output:
            output.write(str(soup.DOMSymbolItem))
