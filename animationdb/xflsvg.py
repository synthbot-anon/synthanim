"""
A Snapshot is either a single image (given by SVG) or a collection of sub-Snapshots.
Each sub-Snapshot is defined by an Element and an iteration number.

Snapshots are bundled together by Elements. An Element is a sequence of Snapshots,
indexed by iteration. The sequence can go on indefinitely.

Elements are bundled together by SnapshotBundles. A SnapshotBundle is a collection
of Elements that all align to the same iteration number.

SnapshotBundles are bundled together by Layers. A Layer is a sequence of
SnapshotBundles.

An Asset is a 2D array of Snapshots, indexed by layer_index and frame_index. Assets
are composed of Layers. The main XFL DOMDocument and LIBRARY items are represented
by Assets. Assets have a fixed number of layers and fixed duration.

"""

import json
import html
import os
from typing import (
    Mapping,
    Sequence,
)
from xml.etree import ElementTree


class Snapshot:
    pass


class SVGSnapshot(Snapshot):
    def __init__(self, filename):
        self.filename = filename


class CompositeSnapshot(Snapshot):
    def __init__(self):
        self.children = []

    def add_child(self, child_snapshot):
        self.children.append(child_snapshot)


class Element(Sequence):
    def __getitem__(self, k: int) -> Snapshot:
        pass

    def __len__(self) -> int:
        pass


class SymbolElement(Element):
    def __init__(self, xflsvg, xmlnode, duration):
        self.loop_type = xmlnode.get("loop")
        self.asset = xflsvg.get_asset(xmlnode.get("libraryItemName"))
        self.first_frame = int(xmlnode.get("firstSnapshot", default=1)) - 1
        self.first_frame = min(self.asset.frame_count - 1, self.first_frame)
        self.duration = duration

    def __getitem__(self, iteration: int) -> Snapshot:
        if self.loop_type in ("single frame", None):
            frame_index = self.first_frame
        elif self.loop_type == "play once":
            frame_index = min(self.first_frame + iteration, self.asset.frame_count - 1)
        elif self.loop_type == "loop":
            loop_size = self.asset.frame_count - self.first_frame
            frame_index = self.first_frame + (iteration % loop_size)
        else:
            raise Exception(f"Unknown loop type: {self.loop_type}")

        result = self.asset.get_frame(frame_index)

    def __len__(self) -> int:
        return self.duration


class ShapeElement(Element):
    def __init__(self, xflsvg, asset, layer, frame_index, element_index, duration):
        self.asset = asset
        self.layer = layer
        self.frame_index = frame_index
        self.element_index = element_index
        self.duration = duration
        self.svg_snapshot = xflsvg.get_shape(
            asset.id, layer.index, frame_index, element_index
        )

    def __getitem__(self, iteration: int) -> Snapshot:
        return self.svg_snapshot

    def __len__(self) -> int:
        return self.duration


# TODO: parent should be changed to frametable
class ElementBundle(Element):
    def __init__(self, xflsvg, layer: "Layer", xmlnode):
        self._xflsvg = xflsvg
        self.layer = layer
        self.xmlnode = xmlnode
        self.start_frame_index = int(xmlnode.get("index"))
        self.duration = int(xmlnode.get("duration", default=1))
        self.end_frame_index = self.start_frame_index + self.duration
        self._snapshots = {}
        self.elements = []

        for i, element_xmlnode in enumerate(self.xmlnode.findall("{*}elements/*")):
            element_type = element_xmlnode.tag

            if element_type == "{http://ns.adobe.com/xfl/2008/}DOMShape":
                element = ShapeElement(
                    xflsvg, layer.asset, layer, self.start_frame_index, i, self.duration
                )
            elif element_type == "{http://ns.adobe.com/xfl/2008/}DOMSymbolInstance":
                element = SymbolElement(xflsvg, element_xmlnode, self.duration)
            else:
                element = Element()

            self.elements.append(element)

    def __getitem__(self, frame_index: int) -> Snapshot:
        if frame_index in self._snapshots:
            return self._snapshots[frame_index]

        new_snapshot = CompositeSnapshot()

        if not self.has_index(frame_index):
            return new_snapshot

        iteration = frame_index - self.start_frame_index
        for element in self.elements:
            new_snapshot.add_child(element[iteration])

        self._snapshots[frame_index] = new_snapshot
        return new_snapshot

    def __len__(self) -> int:
        return self.duration

    @property
    def snapshots(self):
        for i in range(self.start_frame_index, self.end_frame_index):
            yield self[i]

    def has_index(self, frame_index):
        if frame_index < self.start_frame_index:
            return False

        if frame_index >= self.end_frame_index:
            return False

        return True


class Layer(Element):
    def __init__(self, xflsvg, asset: "Asset", id: str, xmlnode):
        self.asset = asset
        self.id = id
        self.xmlnode = xmlnode
        self.name = xmlnode.get("name")
        self.bundles = []
        self.end_frame_index = 0
        self._snapshots = {}

        for bundle_xmlnode in self.xmlnode.findall("{*}frames/*"):
            new_bundle = ElementBundle(xflsvg, self, bundle_xmlnode)
            self.bundles.append(new_bundle)

            if self.end_frame_index == None:
                self.end_frame_index = new_bundle.end_frame_index
            else:
                self.end_frame_index = max(
                    self.end_frame_index, new_bundle.end_frame_index
                )

    def __getitem__(self, frame_index: int) -> Snapshot:
        if frame_index in self._snapshots:
            return self._snapshots[frame_index]

        new_snapshot = CompositeSnapshot()
        for bundle in self.bundles:
            if bundle.has_index(frame_index):
                new_snapshot.add_child(bundle[frame_index])

        self._snapshots[frame_index] = new_snapshot
        return new_snapshot

    def __len__(self) -> int:
        return self.end_frame_index

    @property
    def snapshots(self):
        for i in range(self.end_frame_index):
            yield self[i]


class Asset(Element):
    def __init__(self, xflsvg, id: str, xmlnode):
        self._xflsvg = xflsvg
        self.id = id
        self.layers = []
        self._snapshots = {}
        self.frame_count = 0

        timelines = xmlnode.findall("{*}*/{*}DOMTimeline")
        if len(timelines) > 1:
            raise Exception("this library isn't built to handle multiple timelines")

        for index, xmlnode in enumerate(timelines[0].findall("{*}layers/*")):
            layer_id = f"{self.id}_L{index}"
            layer = Layer(xflsvg, self, layer_id, xmlnode)
            self.layers.append(layer)
            self.frame_count = max(self.frame_count, layer.end_frame_index)

    def __getitem__(self, frame_index: int) -> Snapshot:
        if frame_index in self._snapshots:
            return self._snapshots[frame_index]

        new_snapshot = CompositeSnapshot()
        for layer in self.layers:
            new_snapshot.add_child(layer[frame_index])

        self._snapshots[frame_index] = new_snapshot
        return new_snapshot

    def __len__(self) -> int:
        return self.frame_count

    @property
    def snapshots(self):
        for i in range(self.frame_count):
            yield self[i]


class XflSvg:
    def __init__(self, xflsvg_dir: str):
        self.filepath = os.path.normpath(xflsvg_dir)
        self.id = os.path.basename(self.filepath)  # MUST come after normpath
        self._assets = {}

        document_path = os.path.join(xflsvg_dir, "DOMDocument.xml")
        document_xmlnode = ElementTree.parse(document_path).getroot()
        self.document = Asset(self, self.id, document_xmlnode)

    def get_shape(*args):
        pass

    def get_asset(self, safe_asset_id):
        asset_id = html.unescape(safe_asset_id)

        if asset_id in self._assets:
            return self._assets[asset_id]

        print("opening", asset_id)

        asset_path = os.path.join(self.filepath, "LIBRARY", f"{safe_asset_id}.xml")
        asset_xmlnode = ElementTree.parse(asset_path).getroot()
        asset = Asset(self, asset_id, asset_xmlnode)
        self._assets[asset_id] = asset
        return asset
