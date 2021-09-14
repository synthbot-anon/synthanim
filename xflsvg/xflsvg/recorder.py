import copy
import json
import os
import shutil

from bs4 import BeautifulSoup, element
import pandas

from . import xflsvg
from .xflsvg import TransformedSnapshot, SVGSnapshot, CompositeSnapshot, Layer


TEMPLATE_PATH = f"{os.path.dirname(__file__)}/xfl_template"

class RecordingXflSvg(xflsvg.XflSvg):
    def __init__(self, xflsvg_dir):
        super().__init__(xflsvg_dir)
        self.shape_snapshots = {}
        self.known_assets = set()
        self.known_frames = set()

        self._shapes = []
        self._assets = []
        self._frames = []

        for snapshot in self.frames.snapshots:
            self._add_frames_recursively(snapshot)
    
    
    def _add_frames_recursively(self, snapshot):
        pending = [snapshot]
        while pending:
            current_snapshot = pending.pop()
            if current_snapshot.identifier in self.known_frames:
                raise Exception('invalid file... contains recursive frames')
            
            if type(current_snapshot) == SVGSnapshot:
                self._shapes.append((current_snapshot.identifier, *current_snapshot.path))
            if type(current_snapshot) == TransformedSnapshot:
                pending.append(current_snapshot.original)
                self._frames.append((current_snapshot.identifier, [current_snapshot.original.identifier]))
            elif type(current_snapshot) == CompositeSnapshot:
                children = []
                for child_snapshot in current_snapshot.children:
                    pending.append(child_snapshot)
                    children.append(child_snapshot.identifier)
                
                if children:
                    self._frames.append((current_snapshot.identifier, children))
            
            if type(current_snapshot.owner) == Layer:
                asset_id = current_snapshot.owner.asset.id
                layer_index = current_snapshot.owner.index
                frame_index = current_snapshot.frame_index

                asset_path = (asset_id, layer_index, frame_index)
                if asset_path in self.known_assets:
                    return

                self.known_assets.add(asset_path)
                self._assets.append((asset_id, layer_index, frame_index, snapshot.identifier))


    def to_json(self):
        data = []
        for index, path in enumerate(self._shapes):
            data.append(
                {
                    "id": index,
                    "symbol": path[0],
                    "layer": path[1],
                    "frame": path[2],
                    "elementIndexes": path[3],
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

        for index, path in enumerate(self._shapes):
            element = self.shape_snapshots[path].owner
            clone = copy.copy(base_frame)
            clone["index"] = index
            clone.DOMShape.replace_with(element.xmlnode)
            element_bundle.append(clone)

        with open(target_symbol, "w") as output:
            output.write(str(soup.DOMSymbolItem))
    
    def to_pandas(self):
        shapes = pandas.DataFrame(
            data=self._shapes,
            columns=["shapeId", "assetId", "layerIndex", "frameIndex", "elementIndexes"],
        )
        shapes.set_index('shapeId', inplace=True, drop=True)

        assets = pandas.DataFrame(
            data=self._assets,
            columns=["assetId", "layerIndex", "frameIndex", "frameId"],
        )
        assets.set_index(['assetId', 'layerIndex', 'frameIndex'], inplace=True, drop=True)

        frames = pandas.DataFrame(
            data=self._frames,
            columns=["frameId", "childFrameIds"],
        )
        frames.set_index('frameId', inplace=True, drop=True)

        return {
            'shapes': shapes,
            'assets': assets,
            'frames': frames,
        }
