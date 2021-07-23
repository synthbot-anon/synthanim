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
import copy
from glob import glob
import json
import html
import os
import re
import shutil
from typing import Sequence

from bs4 import BeautifulSoup
import cairosvg
import cairocffi as cairo


class ShapeRecorder(contextlib.AbstractContextManager):
    stack = []

    def __init__(self):
        super().__init__()
        self.shapes = set()
        self.context = None

    def __enter__(self):
        ShapeRecorder.stack.append(self)
        
        surface = cairo.RecordingSurface(cairo.CONTENT_ALPHA, None)
        self._context = cairo.Context(surface)
        self.context = self._context.__enter__()

        return self
    
    def __exit__(self, __exc_type, __exc_value, __traceback):
        context = self.context
        self.context = None
        ShapeRecorder.stack.pop()
        
        return context.__exit__(__exc_type, __exc_value, __traceback)
    
    def record(self, loader, element):
        self.shapes.add((loader, element))
    
    def to_json(self):
        data = []
        for index, record in enumerate(self.shapes):
            sh, el = record
            data.append({
                'id': index,
                'symbol': sh.asset_id,
                'layer': sh.layer_index,
                'frame': sh.frame_index,
                'elementIndexes': sh.path
            })

        return json.dumps(data, indent=4)

    def to_xfl(self, output):
        os.makedirs(output, exist_ok=True)
        try:
            shutil.rmtree(output)
        except:
            pass

        template_path = r'C:\Users\synthbot\Desktop\berry-dest\dump-test\dump4\second-draft\simple'
        shutil.copytree(template_path, output)
        target_symbol = os.path.join(output, 'LIBRARY/SymbolName.xml')
        with open(target_symbol) as template:
            soup = BeautifulSoup(template,'xml')

        base_frame = soup.DOMFrame
        element_bundle = base_frame.parent
        soup.DOMFrame.extract()

        for index, data in enumerate(self.shapes):
            loader, element = data
            clone = copy.copy(base_frame)
            clone['index'] = index
            clone.DOMShape.replace_with(element.xmlnode)
            element_bundle.append(clone)

        with open(target_symbol, 'w') as output:
            output.write(str(soup.DOMSymbolItem))


width = None
height = None
def set_scale(x, y):
    global width, height
    width = x
    height = y

def get_scale():
    return width, height



class Snapshot:
    def __init__(self):
        self.owner = None
        self.parent = None
        self.frame_index = -1

    def to_png(self, width, height):
        output = cairo.ImageSurface(
            cairo.FORMAT_ARGB32, width, height
        )
        with cairo.Context(output) as context:
            set_scale(width, height)
            context.translate(width*0.5, height*0.5)
            self.render(context)

        return output.write_to_png(None)


class EmptySnapshot:
    def __init__(self):
        self.parent = None
    
    def render(self, context):
        pass

_EMPTY_SVG = '<svg height="1px" width="1px" viewBox="0 0 1 1" />'

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
    def svg(self):
        if self._svg != None:
            return self._svg
        
        svg = self.loader.load_sprite()
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
        self._surface = surface.cairo

        return surface.cairo

    def render(self, context):
        if ShapeRecorder.stack:
            for recorder in ShapeRecorder.stack:
                recorder.record(self.loader, self.owner)
            return

        context.save()
        surface = self.surface
        origin = self.loader.load_origin()
        context.translate(*origin)
        context.translate(-self._width/2, -self._height/2)
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
        # x, y = get_scale()
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
    outer = xmlnode.matrix
    if outer == None:
        return cairo.Matrix()
    
    inner = outer.Matrix
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
    outer = xmlnode.transformationPoint
    if outer == None:
        return [0, 0]
    
    inner = outer.Point
    if inner == None:
        return [0, 0]
    
    result = [float(inner.get("x", default=0)), float(inner.get("y", default=0))]
    return result

    # outer = xmlnode.matrix
    # if outer == None:
    #     # return cairo.Matrix()
    #     return [0, 0]
    
    # inner = outer.Matrix
    # if inner == None:
    #     # return cairo.Matrix()
    #     return [0, 0]
    
    # result = [
    #     float(inner.get("tx", default=0)),
    #     float(inner.get("ty", default=0)),
    # ]
    # return result



class Element(AnimationObject):
    def __init__(self, xmlnode):
        super().__init__()
        self.xmlnode = xmlnode
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
        self.asset = bundle_context.xflsvg.get_safe_asset(xmlnode.get("libraryItemName"))
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
        self.svg_snapshot = bundle_context.xflsvg.get_shape(
            bundle_context.asset.id,
            bundle_context.layer.index,
            bundle_context.start_frame_index,
            self.path,
        )

        self.origin = [0, 0]

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

        for i, element_xmlnode in enumerate(xmlnode.members.findChildren(recursive=False)):
            element_type = element_xmlnode.name
            if element_type == "DOMShape":
                element = ShapeElement(self, [*path, i], element_xmlnode,)
            elif element_type == "DOMSymbolInstance":
                element = SymbolElement(self, element_xmlnode)
            elif element_type == "DOMGroup":
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
        
        for i, element_xmlnode in enumerate(xmlnode.elements.findChildren(recursive=False)):
            element_type = element_xmlnode.name
            if element_type == "DOMShape":
                element = ShapeElement(self, [i], element_xmlnode,)
            elif element_type == "DOMSymbolInstance":
                element = SymbolElement(self, element_xmlnode)
            elif element_type == "DOMGroup":
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
        self.name = xmlnode.get("name", None)
        self.visible = xmlnode.get('visible', 'true') != 'false'
        self.bundles = []
        self.end_frame_index = 0
        self.layer_type = xmlnode.get('layerType', 'normal')
        self._snapshots = {}

        for bundle_xmlnode in self.xmlnode.frames.findChildren(recursive=False):
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

        timelines = xmlnode.timelines or xmlnode.timeline
        timelines = list(timelines.findChildren(recursive=False))
        if len(timelines) > 1:
            raise Exception("this library isn't built to handle multiple timelines")

        for index, xmlnode in enumerate(timelines[0].layers.findChildren(recursive=False)):
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
        self.width = int(xmlnode.DOMDocument['width'])
        self.height = int(xmlnode.DOMDocument['height'])


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
        self._spritemaps = None
        self._xflmaps = None
        self._metadata = None

    @property
    def spritemaps(self):
        if self._spritemaps:
            return self._spritemaps

        self._spritemaps = {}
        for spritemap_fn in glob(f"{self.filepath}/spritemap*.svg"):
            spritemap_id = os.path.basename(spritemap_fn)
            self._spritemaps[spritemap_id] = SvgFile(spritemap_fn)

        return self._spritemaps

    @property
    def metadata(self):
        if self._metadata:
            return self._metadata

        with open(f"{self.filepath}/spritemap.json") as spritemap_file:
            spritemap = json.load(spritemap_file)

        with open(f"{self.filepath}/xflmap.json") as xflmap_file:
            xflmap = json.load(xflmap_file)


        # re-structure the data for easy lookup
        shapes = {}
        for shape in xflmap:
            shape_id = shape['id']
            shapes[shape_id] = shape

        # map lookup details to sprite details
        self._metadata = {}
        for sprite in spritemap['sprites']:
            shape_id = sprite['id']
            shape = shapes[shape_id]
            key = (
                shape['symbol'],
                shape['layer'],
                shape['frame'],
                tuple(shape['elementIndexes'])
            )
            self._metadata[key] = sprite

        return self._metadata

    def get_sprite(self, asset_id, layer_index, frame_index, element_index, buffer=20):
        data = self.metadata.get((asset_id, layer_index, frame_index, element_index), None)
        if not data:
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
        if ShapeRecorder.stack:
            return [0, 0]

        data = self.metadata.get((asset_id, layer_index, frame_index, element_index), None)
        if not data:
            return None
        
        return data['transformX'], data['transformY']


class SvgLoader:
    def __init__(self, spritemap, asset_id, layer_index, frame_index, path):
        self.spritemap = spritemap
        self.asset_id = asset_id
        self.layer_index = layer_index
        self.frame_index = frame_index
        self.path = path
    
    def load_sprite(self):
        return self.spritemap.get_sprite(
            self.asset_id,
            self.layer_index,
            self.frame_index,
            self.path
        )

    def load_origin(self):
        return self.spritemap.get_origin(
            self.asset_id,
            self.layer_index,
            self.frame_index,
            self.path
        )


class XflSvg:
    def __init__(self, xflsvg_dir: str):
        self.filepath = os.path.normpath(xflsvg_dir)
        self.spritemap = SvgSpritemap(f'{self.filepath}/spritemaps')
        self.id = os.path.basename(self.filepath)  # MUST come after normpath
        self._assets = {}
        self._shapes = {}

        document_path = os.path.join(xflsvg_dir, "DOMDocument.xml")
        with open(document_path) as document_file:
            document_soup = BeautifulSoup(document_file, 'xml')

        self.frames = Document(self, document_soup)

    def get_shape(self, asset_id, layer_index, frame_index, path):
        key = (asset_id, layer_index, frame_index, path)
        if key in self._shapes:
            return self._shapes[key]

        loader = SvgLoader(self.spritemap, asset_id, layer_index, frame_index, path)
        result = SVGSnapshot(key, loader)
        self._shapes[key] = result

        return result
    

    def get_safe_asset(self, safe_asset_id):
        asset_id = html.unescape(safe_asset_id)

        if asset_id in self._assets:
            return self._assets[asset_id]

        asset_path = os.path.join(self.filepath, "LIBRARY", f"{safe_asset_id}.xml")
        with open(asset_path) as asset_file:
            asset_soup = BeautifulSoup(asset_file, 'xml')
        
        asset = Asset(self, asset_id, asset_soup)
        self._assets[asset_id] = asset
        return asset

    def get_asset(self, asset_id):
        return self._assets[asset_id]
