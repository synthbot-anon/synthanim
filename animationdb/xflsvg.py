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

import contextlib
from glob import glob
import json
import html
import os
import re
from typing import Sequence
from xml.etree import ElementTree

from bs4 import BeautifulSoup
import cairosvg
import cairocffi as cairo

tabs = 0
def enter(*s):
    global tabs
    # print('--' * tabs, *s)
    tabs += 1

def exit():
    global tabs
    tabs -= 1

_error = False
def seterror():
    global _error
    _error = True

class ShapeRecorder(contextlib.AbstractContextManager):
    stack = []

    def __init__(self):
        super().__init__()
        self.shapes = []

    def __enter__(self):
        ShapeRecorder.stack.append(self)
        surface = cairo.RecordingSurface(cairo.CONTENT_ALPHA, None)
        context = cairo.Context(surface)
        return context
    
    def __exit__(self, __exc_type, __exc_value, __traceback):
        ShapeRecorder.stack.pop()
        return None
    
    def record(self, loader):
        self.shapes.append(loader)
    
    def to_json(self):
        # TODO: sort by asset, frame
        data = []
        for sh in self.shapes:
            data.append({
                'symbol': sh.asset_id,
                'layer': sh.layer_index,
                'frame': sh.frame_index,
                'indexes': sh.path
            })
        return json.dumps(data)
    


class Snapshot:
    def __init__(self):
        self.owner = None
        self.parent = None
        self.frame_index = -1

class EmptySnapshot:
    def __init__(self):
        self.parent = None
    
    def render(self, context):
        pass

_EMPTY_SVG = '<svg height="1px" width="1px" viewBox="0 0 1 1" />'
iter = 0

class SVGSnapshot(Snapshot):
    def __init__(self, name, loader):
        super().__init__()
        self.name = name
        self.loader = loader
        self._svg = None
        self._png = None
        self._surface = None
        self._width = None
        self._height = None

    @property
    def png(self):
        if not self._png:
            self._png = self.cairo.write_to_png(None)
        return self._png
    
    @property
    def svg(self):
        if self._svg != None:
            return self._svg
        
        svg = self.loader.load()
        if svg == None:
            svg = _EMPTY_SVG
        
        self._svg = svg
        return svg

    @property
    def surface(self):
        if self._surface:
            return self._surface

        tree = cairosvg.parser.Tree(bytestring=self.svg)
        surface = cairosvg.surface.SVGSurface(tree, output=None, dpi=72)
        self._width = surface.width
        self._height = surface.height

        global iter
        with open(f'/data/shapes/{iter}.svg', 'w') as output:
            output.write(self.svg)
        iter += 1

        self._surface = surface.cairo
        return surface.cairo

    def render(self, context):
        if ShapeRecorder.stack:
            for recorder in ShapeRecorder.stack:
                recorder.record(self.loader)
            return

        context.save()
        surface = self.surface
        context.translate(-self._width / 2, -self._height / 2)
        context.set_source_surface(self.surface)
        context.paint()
        context.restore()


class CompositeSnapshot(Snapshot):
    def __init__(self):
        super().__init__()
        self.children = []

    def add_child(self, child_snapshot):
        self.children.append(child_snapshot)
        child_snapshot.parent = self

    def render(self, context):
        for child in self.children[::-1]:
            child.parent = self
            child.render(context)


class TransformedSnapshot(Snapshot):
    def __init__(self, original, origin=[0,0], matrix=cairo.Matrix()):
        super().__init__()
        self.original = original
        self.origin = origin
        self.matrix = matrix
        self.original.parent = self

    def render(self, context):
        self.original.parent = self
        context.save()
        context.translate(self.origin[0], self.origin[1])
        context.transform(self.matrix)
        self.original.render(context)

        context.restore()


class AnimationObject(Sequence):
    def __init__(self):
        self.parent = None

    def __getitem__(self, k: int) -> Snapshot:
        pass

    def __len__(self) -> int:
        pass

def _get_matrix(xmlnode):
    outer = xmlnode.find("{*}matrix")
    if outer == None:
        return cairo.Matrix()
    
    inner = outer.find("{*}Matrix")
    if inner == None:
        return cairo.Matrix()
    
    result = cairo.Matrix(
        float(inner.get("a", default=1)),
        float(inner.get("b", default=0)),
        float(inner.get("c", default=0)),
        float(inner.get("d", default=1)),
        float(inner.get("tx", default=0)),
        float(inner.get("ty", default=0)),
    )
    return result


def _get_origin(xmlnode):
    outer = xmlnode.find("{*}transformationPoint")
    if outer == None:
        return [0, 0]
    
    inner = outer.find("{*}Point")
    if inner == None:
        return [0, 0]
    
    result = [float(inner.get("x", default=0)), float(inner.get("y", default=0))]
    return result



class Element(AnimationObject):
    def __init__(self, xmlnode):
        super().__init__()
        self.xmlnode = xmlnode
        matrix = xmlnode.find("{*}matrix")
        self.matrix = _get_matrix(xmlnode)
        self.origin = _get_origin(xmlnode)
    
    def __getitem__(self, k: int) -> Snapshot:
        result = EmptySnapshot()
        result.owner = self
        result.frame_index = k
        return result


class SymbolElement(Element):
    def __init__(self, bundle_context, xmlnode):
        super().__init__(xmlnode)
        self.loop_type = xmlnode.get("loop")
        self.asset = bundle_context.xflsvg.get_asset(xmlnode.get("libraryItemName"))
        self.first_frame = int(xmlnode.get("firstFrame", default=0))
        self.first_frame = min(self.asset.frame_count - 1, self.first_frame)
        self.duration = bundle_context.duration

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

        result = TransformedSnapshot(self.asset[frame_index], self.origin, self.matrix)
        result.owner = self
        result.frame_index = frame_index
        return result

    def __len__(self) -> int:
        return self.duration


class ShapeElement(Element):
    def __init__(self, bundle_context, path, xmlnode):
        super().__init__(xmlnode)
        self.asset = bundle_context.asset
        self.layer = bundle_context.layer
        self.duration = bundle_context.duration
        self.path = tuple(path)
        self.svg_snapshot, self.origin = bundle_context.xflsvg.get_shape(
            bundle_context.asset.id,
            bundle_context.layer.index,
            bundle_context.start_frame_index,
            self.path,
        )

        self.svg_snapshot.owner = self
        self.svg_snapshot.frame_index = 0

    def __getitem__(self, iteration: int) -> Snapshot:
        result = TransformedSnapshot(self.svg_snapshot, self.origin, self.matrix)
        result.owner = self
        result.frame_index = 0
        return result

    def __len__(self) -> int:
        return self.duration



class BundleContext:
    def __init__(self):
        self.xflsvg = None
        self.asset = None
        self.layer = None
        self.start_frame_index = None
        self.duration = None
        self.element_index = 0


class GroupElement(Element, BundleContext):
    def __init__(self, bundle_context, path, xmlnode):
        super().__init__(xmlnode)

        self.xflsvg = bundle_context.xflsvg
        self.asset = bundle_context.asset
        self.layer = bundle_context.layer
        self.start_frame_index = bundle_context.start_frame_index
        self.duration = bundle_context.duration
        self.path = path
        self.elements = []

        for i, element_xmlnode in enumerate(xmlnode.findall('{*}members/*')):
            element_type = element_xmlnode.tag
            if element_type == "{http://ns.adobe.com/xfl/2008/}DOMShape":
                element = ShapeElement(self, [*path, i], element_xmlnode,)
            elif element_type == "{http://ns.adobe.com/xfl/2008/}DOMSymbolInstance":
                element = SymbolElement(self, element_xmlnode)
            elif element_type == "{http://ns.adobe.com/xfl/2008/}DOMGroup":
                element = GroupElement(self, [*path, i], element_xmlnode)
            else:
                element = Element(element_xmlnode)

            element.parent = self
            self.elements.append(element)


    def __getitem__(self, iteration: int) -> Snapshot:
        result = CompositeSnapshot()
        result.owner = self
        result.frame_index = iteration
        for child in self.elements:
            result.add_child(child[iteration])

        result = TransformedSnapshot(result, self.origin, self.matrix)
        result.owner = self
        result.frame_index = iteration
        return result

    def __len__(self) -> int:
        return self.duration



class ElementBundle(AnimationObject, BundleContext):
    def __init__(self, xflsvg, layer: "Layer", xmlnode):
        super().__init__()
        self.xflsvg = xflsvg
        self.layer = layer
        self.asset = self.layer.asset
        self.xmlnode = xmlnode
        self.start_frame_index = int(xmlnode.get("index"))
        self.duration = int(xmlnode.get("duration", default=1))
        self.end_frame_index = self.start_frame_index + self.duration
        self._snapshots = {}
        self.element_index = 0
        self.elements = []
        
        for i, element_xmlnode in enumerate(xmlnode.findall('{*}elements/*')):
            element_type = element_xmlnode.tag
            if element_type == "{http://ns.adobe.com/xfl/2008/}DOMShape":
                element = ShapeElement(self, [i], element_xmlnode,)
            elif element_type == "{http://ns.adobe.com/xfl/2008/}DOMSymbolInstance":
                element = SymbolElement(self, element_xmlnode)
            elif element_type == "{http://ns.adobe.com/xfl/2008/}DOMGroup":
                element = GroupElement(self, [i], element_xmlnode)
            else:
                element = Element(element_xmlnode)

            element.parent = self
            self.elements.append(element)


    def __getitem__(self, frame_index: int) -> Snapshot:
        if frame_index in self._snapshots:
            return self._snapshots[frame_index]

        new_snapshot = CompositeSnapshot()

        if not self.has_index(frame_index):
            return new_snapshot

        iteration = frame_index - self.start_frame_index
        for element in self.elements[::-1]:
            new_snapshot.add_child(element[iteration])

        self._snapshots[frame_index] = new_snapshot
        new_snapshot.owner = self
        new_snapshot.frame_index = frame_index
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


class Layer(AnimationObject):
    def __init__(self, xflsvg, asset: "Asset", id: str, index: int, xmlnode):
        super().__init__()
        self.asset = asset
        self.id = id
        self.index = index
        self.xmlnode = xmlnode
        self.name = xmlnode.get("name")
        self.visible = xmlnode.get('visible', default=None) != 'false'
        self.bundles = []
        self.end_frame_index = 0
        self.layer_type = xmlnode.get('layerType', default='normal')
        self._snapshots = {}

        for bundle_xmlnode in self.xmlnode.findall("{*}frames/*"):
            new_bundle = ElementBundle(xflsvg, self, bundle_xmlnode)
            new_bundle.parent = self
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
        new_snapshot.owner = self
        new_snapshot.frame_index = frame_index
        return new_snapshot

    def __len__(self) -> int:
        return self.end_frame_index

    @property
    def snapshots(self):
        for i in range(self.end_frame_index):
            yield self[i]


class Asset(AnimationObject):
    def __init__(self, xflsvg, id: str, xmlnode):
        super().__init__()
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
            layer = Layer(xflsvg, self, layer_id, index, xmlnode)
            layer.parent = self
            self.layers.append(layer)
            self.frame_count = max(self.frame_count, layer.end_frame_index)

    def __getitem__(self, frame_index: int) -> Snapshot:
        if frame_index in self._snapshots:
            return self._snapshots[frame_index]

        new_snapshot = CompositeSnapshot()
        for layer in self.layers:
            if layer.layer_type == 'normal' or ShapeRecorder.stack:
                new_snapshot.add_child(layer[frame_index])

        self._snapshots[frame_index] = new_snapshot
        new_snapshot.owner = self
        new_snapshot.frame_index = frame_index
        return new_snapshot

    def __len__(self) -> int:
        return self.frame_count

    @property
    def snapshots(self):
        for i in range(self.frame_count):
            yield self[i]


class Document(Asset):
    def __init__(self, xflsvg, xmlnode):
        super().__init__(xflsvg, "", xmlnode)
        self.width = int(xmlnode.get('width'))
        self.height = int(xmlnode.get('height'))


class SvgFile:
    def __init__(self, filepath):
        self.filepath = filepath

        with open(filepath) as file:
            self.root = BeautifulSoup(file, "html5lib")

        self.svg = self.root.svg
        self.defs = self.svg.defs
        self.objects = {}

        for asset in self.svg.findChildren("g", recursive=False):
            obj = asset.find("use")
            if obj:
                id = obj["xlink:href"][1:]
                self.objects[id] = asset


class SvgSpritemap:
    def __init__(self, spritemap_dir: str):
        self.filepath = os.path.normpath(spritemap_dir)
        self.spritemaps = {}

        with open(f"{spritemap_dir}/spritemap.json") as metadata_file:
            self.metadata = json.load(metadata_file)

        for spritemap_fn in glob(f"{spritemap_dir}/spritemap*.svg"):
            spritemap_id = os.path.basename(spritemap_fn)
            self.spritemaps[spritemap_id] = SvgFile(spritemap_fn)

    def get_sprite(self, asset_id, layer_index, frame_index, element_index, buffer=20):
        found_match = False
        for data in self.metadata["sprites"]:
            if data["symbolname"] != asset_id:
                continue
            if data["layerindex"] != layer_index:
                continue
            if data["frameindex"] != frame_index:
                continue
            if data["elementindex"] != element_index:
                continue
            
            found_match = True
            break
        
        if not found_match:
            seterror()
            print('no data for', asset_id, layer_index, frame_index, element_index)
            return None
        
        sheet = self.spritemaps[data["filename"]]

        root = BeautifulSoup("<svg/>", "html5lib")
        root.svg.attrs = sheet.svg.attrs.copy()
        root.svg.attrs["width"] = f'{data["width"]}px'
        root.svg.attrs["height"] = f'{data["height"]}px'

        left = data["x"] - data["width"] / 2
        top = data["y"] - data["height"] / 2

        root.svg.attrs["viewBox"] = f"{left} {top} {data['width']} {data['height']}"
        root.svg.append(sheet.defs)

        prefix = re.sub(r"[^a-zA-Z0-9]", "_", data["svgprefix"])
        found = False
        for id in sheet.objects:
            if id.startswith(prefix) or id.startswith(f'FL_{prefix}'):
                found = True
                root.svg.append(sheet.objects[id])
        
        if not found:
            print('unable to find svg for', prefix, 'in', data['filename'])
            return None

        return str(root.svg)
    
    def get_origin(self, asset_id, layer_index, frame_index, element_index):
        found_match = False
        for data in self.metadata["sprites"]:
            if data["symbolname"] != asset_id:
                continue
            if data["layerindex"] != layer_index:
                continue
            if data["frameindex"] != frame_index:
                continue
            if data["elementindex"] != element_index:
                continue
            
            found_match = True
            break
        
        if not found_match:
            seterror()
            return None

        return [data['transformX'], data['transformY']]


class SvgLoader:
    def __init__(self, spritemap, asset_id, layer_index, frame_index, path):
        self.spritemap = spritemap
        self.asset_id = asset_id
        self.layer_index = layer_index
        self.frame_index = frame_index
        self.path = path
    
    def load(self):
        return self.spritemap.get_sprite(asset_id, layer_index, frame_index, path)

class XflSvg:
    def __init__(self, xflsvg_dir: str):
        self.filepath = os.path.normpath(xflsvg_dir)
        self.spritemap = SvgSpritemap(f'{self.filepath}/spritemaps')
        self.id = os.path.basename(self.filepath)  # MUST come after normpath
        self._assets = {}
        self._shapes = {}

        document_path = os.path.join(xflsvg_dir, "DOMDocument.xml")
        document_xmlnode = ElementTree.parse(document_path).getroot()
        self.frames = Document(self, document_xmlnode)

    def get_shape(self, asset_id, layer_index, frame_index, path):
        key = (asset_id, layer_index, frame_index, path)
        if key in self._shapes:
            return self._shapes[key]

        loader = SvgLoader(self.spritemap, asset_id, layer_index, frame_index, path)
        result = SVGSnapshot(key, loader)
        self._shapes[key] = result

        origin = self.spritemap.get_origin(asset_id, layer_index, frame_index, path)
        if origin == None:
            origin = [0, 0]
            
        return result, origin
    

    def get_asset(self, safe_asset_id):
        asset_id = html.unescape(safe_asset_id)

        if asset_id in self._assets:
            return self._assets[asset_id]

        asset_path = os.path.join(self.filepath, "LIBRARY", f"{safe_asset_id}.xml")
        asset_xmlnode = ElementTree.parse(asset_path).getroot()
        asset = Asset(self, asset_id, asset_xmlnode)
        self._assets[asset_id] = asset
        return asset
