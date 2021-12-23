import copy
import json
import os
import shutil

from bs4 import BeautifulSoup, element
import pandas

from . import xflsvg
from .xflsvg import TransformedSnapshot, SVGSnapshot, CompositeSnapshot, Layer, Document


TEMPLATE_PATH = f"{os.path.dirname(__file__)}/xfl_template"


class XflSvgRecorder(xflsvg.XflReader):
    def __init__(self, xflsvg_dir):
        super().__init__(xflsvg_dir)
        self.shape_xmlnodes = {}
        self.known_assets = set()
        self.known_frames = set()

        self._pre_shapes = set()
        self._assets = set()
        self._frames = []
        self._document = [(self.frames.id, self.frames.width, self.frames.height)]

    def on_frame_rendered(self, snapshot, *args, **kwargs):
        if snapshot.identifier not in self.known_frames:
            children = list(map(lambda x: x.identifier, snapshot.children))
            self._frames.append(
                (snapshot.identifier, children, snapshot.matrix, snapshot.origin)
            )
            self.known_frames.add(snapshot.identifier)

        if type(snapshot) == SVGSnapshot:
            self._pre_shapes.add((snapshot.identifier, *snapshot.path))
            self.shape_xmlnodes[snapshot.path] = snapshot.owner

        if type(snapshot.owner) == Layer:
            asset_id = snapshot.owner.asset.id
            layer_index = snapshot.owner.index
            frame_index = snapshot.frame_index

            asset_path = (asset_id, layer_index, frame_index)
            if asset_path not in self.known_assets:
                self.known_assets.add(asset_path)
                self._assets.add(
                    (asset_id, layer_index, frame_index, snapshot.identifier)
                )

    def get_shapes(self):
        result = []
        for index, path in enumerate(self.shape_xmlnodes):
            result.append(
                {
                    "id": index,
                    "symbol": path[0],
                    "layer": path[1],
                    "frame": path[2],
                    "elementIndexes": path[3],
                }
            )

        return result

    def to_shapes_xfl(self, output):
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

        for index, path in enumerate(self.shape_xmlnodes):
            element = self.shape_xmlnodes[path]
            clone = copy.copy(base_frame)
            clone["index"] = index
            clone.DOMShape.replace_with(element.xmlnode)
            element_bundle.append(clone)

        with open(target_symbol, "w") as output:
            output.write(str(soup.DOMSymbolItem))

    def to_pandas(self):
        pre_shapes = pandas.DataFrame(
            data=self._pre_shapes,
            columns=[
                "frameId",
                "assetId",
                "layerIndex",
                "frameIndex",
                "elementIndexes",
            ],
        )

        assets = pandas.DataFrame(
            data=self._assets,
            columns=["assetId", "layerIndex", "frameIndex", "frameId"],
        )

        frames = pandas.DataFrame(
            data=self._frames,
            columns=["frameId", "childFrameIds", "matrix", "origin", "color", "mask"],
        )

        documents = pandas.DataFrame(
            data=self._document, columns=["assetId", "width", "height"]
        )

        return {
            "pre-shapes": pre_shapes,
            "assets": assets,
            "frames": frames,
            "documents": documents,
        }
