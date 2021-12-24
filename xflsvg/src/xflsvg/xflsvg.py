"""
This class is for parsing and rendering XFL files.

Example usage:
    
    xfl = XflReader('/path/to/file.xfl')
    timeline = xfl.get_timeline('Scene 1')
    for i, frame in enumerate(timeline):
        with SvgRenderer() as renderer:
            frame.render()
        svg = renderer.compile(xfl.width, xfl.height)
        with open(f'frame{i}.svg', 'w') as outfile:
            svg.write(outfile, encoding='unicode')

Overview of XFL:
    An XFL file consists of a Document file and Asset files. A Document contains one or
    more timelines. An Asset contains a single timeline.
    
    Each timeline contains one or more layers. Some layers are designated as mask
    layers, and some layers have parent mask layers. A mask layer, when rendered,
    defines which portion of child layers should get rendered. Layers are rendered
    in reverse order.

    A layer contains one or more element bundles. An element bundle is a collection of
    elements whose frames follow the same loop length. An element bundle contains one
    or more frames and one or more elements.

    An element can be a symbol, shape, or group. A symbol describes a transformation
    and how to loop over an asset to generate frames. A shape define a single
    primitive frame. Shapes are described in Adobe's proprietary format, and they are
    parsed in the domshape/ package provided by PluieElectrique. A group consists of a
    collection of other elements that share a transformation.

    A transformation can describe a linear transformation and a translation of pixel
    positions and colors.

Overview of rendering:
    The XFLReader class provide is a visitor interface for rendering. Renderers should
    subclass the XflRenderer class and implement the relevant methods. A complete
    renderer should implement EITHER:
        render_shape - Render an SVG shape
        push_transform, pop_transform - Start and end position and color transformations
        push_mask, pop_mask - Start and end mask definitions
        push_masked_render, pop_masked_render - Start/end renders with the last mask

    OR
        on_frame_rendered - Should handle Frame, ShapeFrame, and MaskedFrame
    
    The first set of methods are better for actual rendering since they convert the XFL
    file into a sequence. The second method is better for transforming the data into a
    new tree-structured format.

"""

from contextlib import contextmanager
import copy
from dataclasses import dataclass
from glob import glob
import json
import html
import os
import re
import shutil
import threading
from typing import Sequence
import warnings

from bs4 import BeautifulSoup
import xml.etree.ElementTree as etree

from .domshape import xfl_domshape_to_svg

_frame_index = 0


class Frame:
    def __init__(self, matrix=None, color=None, children=None):
        global _frame_index
        self.identifier = _frame_index
        _frame_index += 1

        self.matrix = matrix
        self.color = color
        self.owner_element = None
        self.parent_frame = None
        self.frame_index = -1
        self.children = []

    def add_child(self, child_frame):
        self.children.append(child_frame)
        child_frame.parent_frame = self

    def prepend_child(self, child_frame):
        self.children.insert(0, child_frame)
        child_frame.parent_frame = self
    
    def render(self, *args, **kwargs):
        renderer = XflRenderer.current()
        renderer.push_transform(self, *args, **kwargs)

        for child in self.children:
            child.render(*args, **kwargs)

        renderer.pop_transform(self, *args, **kwargs)
        renderer.on_frame_rendered(self, *args, **kwargs)
    

class ShapeFrame(Frame):
    def __init__(self, normal_svg, mask_svg):
        super().__init__()
        self.normal_svg = normal_svg
        self.mask_svg = mask_svg

    def render(self, *args, **kwargs):
        renderer = XflRenderer.current()
        renderer.render_shape(self, *args, **kwargs)
        renderer.on_frame_rendered(self, *args, **kwargs)


def _transformed_frame(original, matrix=None, color=None):
    result = Frame(matrix, color)
    result.add_child(original)
    return result


class MaskedFrame(Frame):
    def __init__(self, mask):
        super().__init__()
        self.mask = mask
        mask.parent_frame = self

    def render(self, *args, **kwargs):
        renderer = XflRenderer.current()

        renderer.push_mask(self, *args, **kwargs)
        self.mask.render()
        renderer.pop_mask(self, *args, **kwargs)

        renderer.push_masked_render(self, *args, **kwargs)
        for child in self.children:
            child.render()
        renderer.pop_masked_render(self, *args, **kwargs)

        renderer.on_frame_rendered(self, *args, **kwargs)


class AnimationObject(Sequence):
    def __init__(self):
        pass

    def __getitem__(self, k: int) -> Frame:
        pass

    def __len__(self) -> int:
        pass

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]


@dataclass(frozen=True)
class ColorObject:
    mr: float = 1
    mg: float = 1
    mb: float = 1
    ma: float = 1
    dr: float = 0
    dg: float = 0
    db: float = 0
    da: float = 0

    def __matmul__(self, other):
        return ColorObject(
            self.mr * other.mr,
            self.mg * other.mg,
            self.mb * other.mb,
            self.ma * other.ma,
            self.mr * other.dr + self.dr,
            self.mg * other.dg + self.dg,
            self.mb * other.db + self.db,
            self.ma * other.da + self.da,
        )

    def is_identity(self):
        return (
            self.mr == 1
            and self.mg == 1
            and self.mb == 1
            and self.ma == 1
            and self.dr == 0
            and self.dg == 0
            and self.db == 0
            and self.da == 0
        )

    @property
    def id(self):
        """Unique ID used to dedup SVG elements in <defs>."""
        return f"Filter_{hash(self) & 0xFFFFFFFFFFFFFFFF:16x}"


def _get_matrix(xmlnode):
    outer = xmlnode.findChild('matrix', recursive=False)
    if outer == None:
        return None

    inner = outer.findChild('Matrix', recursive=False)
    if inner == None:
        return None

    result = [
        inner.get("a", default="1"),
        inner.get("b", default="0"),
        inner.get("c", default="0"),
        inner.get("d", default="1"),
        inner.get("tx", default="0"),
        inner.get("ty", default="0"),
    ]

    if result == ["1", "0", "0", "1", "0", "0"]:
        return None

    return result


def _get_color(xmlnode):
    outer = xmlnode.findChild('color', recursive=False)
    if outer == None:
        return None

    inner = outer.findChild('Color', recursive=False)
    if inner == None:
        return None

    inner = inner.attrs
    result = None

    count = 0
    if "brightness" in inner:
        count += 1
        brightness = float(inner["brightness"])
        if brightness < 0:
            # linearly interpolate towards black
            result = ColorObject(
                mr=1+brightness, mg=1+brightness, mb=1+brightness,
            )
        else:
            # linearly interpolate towards white
            result = ColorObject(
                mr=1-brightness,
                mg=1-brightness,
                mb=1-brightness,
                dr=brightness,
                dg=brightness,
                db=brightness,
            )
    if "tintMultiplier" in inner or "tintColor" in inner:
        count += 1
        # color*(1-tint_multiplier) + tint_color*tint_multiplier
        tint_multiplier = float(inner.get("tintMultiplier", 0))
        tint_color = inner.get("tintColor", "#000000")

        result = ColorObject(
            mr=1-tint_multiplier,
            mg=1-tint_multiplier,
            mb=1-tint_multiplier,
            dr=tint_multiplier * int(tint_color[1:3], 16) / 255,
            dg=tint_multiplier * int(tint_color[3:5], 16) / 255,
            db=tint_multiplier * int(tint_color[5:7], 16) / 255,
        )

    if set(inner.keys()) & {
        "redMultiplier",
        "greenMultiplier",
        "blueMultiplier",
        "alphaMultiplier",
        "redOffset",
        "greenOffset",
        "blueOffset",
        "alphaOffset",
    }:
        count += 1
        result = ColorObject(
            mr=float(inner.get("redMultiplier", 1)),
            mg=float(inner.get("greenMultiplier", 1)),
            mb=float(inner.get("blueMultiplier", 1)),
            ma=float(inner.get("alphaMultiplier", 1)),
            dr=float(inner.get("redOffset", 0)) / 255,
            dg=float(inner.get("greenOffset", 0)) / 255,
            db=float(inner.get("blueOffset", 0)) / 255,
            da=float(inner.get("alphaOffset", 0)) / 255,
        )

    assert count < 2
    return result


class Element(AnimationObject):
    def __init__(self, xmlnode):
        super().__init__()
        self.xmlnode = xmlnode
        self.matrix = _get_matrix(xmlnode)
        self.color = _get_color(xmlnode)

    def __getitem__(self, k: int) -> Frame:
        result = Frame()
        result.owner_element = self
        result.frame_index = k
        return result


class SymbolElement(Element):
    def __init__(self, xflsvg, duration, xmlnode):
        super().__init__(xmlnode)
        self.xflsvg = xflsvg
        self.loop_type = xmlnode.get("loop")
        self.asset = xflsvg.get_safe_asset(xmlnode.get("libraryItemName"))
        self.first_frame = int(xmlnode.get("firstFrame", default=0))
        self.first_frame = min(self.asset.frame_count - 1, self.first_frame)
        self.duration = duration

    def __getitem__(self, iteration: int) -> Frame:
        if self.loop_type in ("single frame", None):
            frame_index = self.first_frame
        elif self.loop_type == "play once":
            frame_index = min(self.first_frame + iteration, self.asset.frame_count - 1)
        elif self.loop_type == "loop":
            loop_size = self.asset.frame_count - self.first_frame
            frame_index = self.first_frame + (iteration % loop_size)
        else:
            raise Exception(f"Unknown loop type: {self.loop_type}")

        result = _transformed_frame(self.asset[frame_index], self.matrix, self.color)
        result.owner_element = self
        result.frame_index = frame_index
        return result

    def __len__(self) -> int:
        return self.duration


class ShapeElement(Element):
    def __init__(
        self, xflsvg, asset, layer, start_frame_index, duration, path, xmlnode
    ):
        super().__init__(xmlnode)
        self.xflsvg = xflsvg
        self.asset = asset
        self.layer = layer
        self.duration = duration
        self.path = tuple(path)
        self.svg_frame = xflsvg.get_shape(
            xmlnode, asset.id, layer.index, start_frame_index, self.path,
        )

        self.svg_frame.owner = self
        self.svg_frame.frame_index = 0

    def __getitem__(self, iteration: int) -> Frame:
        result = _transformed_frame(self.svg_frame, self.matrix, self.color)
        result.owner_element = self
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
    def __init__(
        self, xflsvg, asset, layer, start_frame_index, duration, path, xmlnode
    ):
        super().__init__(xmlnode)
        self.xflsvg = xflsvg
        self.asset = asset
        self.layer = layer
        self.start_frame_index = start_frame_index
        self.duration = duration
        self.path = path
        self.elements = []

        for i, element_xmlnode in enumerate(
            xmlnode.findChild('members', recursive=False).findChildren(recursive=False)
        ):
            element_type = element_xmlnode.name
            if element_type == "DOMShape":
                element = ShapeElement(
                    self.xflsvg,
                    self.asset,
                    self.layer,
                    self.start_frame_index,
                    self.duration,
                    [*path, i],
                    element_xmlnode,
                )
            elif element_type == "DOMSymbolInstance":
                element = SymbolElement(self.xflsvg, self.duration, element_xmlnode)
            elif element_type == "DOMGroup":
                element = GroupElement(
                    self.xflsvg,
                    self.asset,
                    self.layer,
                    self.start_frame_index,
                    self.duration,
                    [*path, i],
                    element_xmlnode,
                )
            else:
                element = Element(element_xmlnode)

            element.owner_element = self
            self.elements.append(element)

    def __getitem__(self, iteration: int) -> Frame:
        result = Frame(color=self.color)
        result.owner_element = self
        result.frame_index = iteration
        for child in self.elements:
            result.add_child(child[iteration])

        result.owner_element = self
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
        self._frames = {}
        self.element_index = 0
        self.elements = []

        for i, element_xmlnode in enumerate(
            xmlnode.elements.findChildren(recursive=False)
        ):
            element_type = element_xmlnode.name
            if element_type == "DOMShape":
                element = ShapeElement(
                    self.xflsvg,
                    self.asset,
                    self.layer,
                    self.start_frame_index,
                    self.duration,
                    [i],
                    element_xmlnode,
                )
            elif element_type == "DOMSymbolInstance":
                element = SymbolElement(self.xflsvg, self.duration, element_xmlnode)
            elif element_type == "DOMGroup":
                element = GroupElement(
                    self.xflsvg,
                    self.asset,
                    self.layer,
                    self.start_frame_index,
                    self.duration,
                    [i],
                    element_xmlnode,
                )
            else:
                element = Element(element_xmlnode)

            element.owner_element = self
            self.elements.append(element)

    def __getitem__(self, frame_index: int) -> Frame:
        if frame_index in self._frames:
            return self._frames[frame_index]

        new_frame = Frame()

        if not self.has_index(frame_index):
            return new_frame

        iteration = frame_index - self.start_frame_index
        for element in self.elements:
            new_frame.add_child(element[iteration])

        self._frames[frame_index] = new_frame
        new_frame.owner_element = self
        new_frame.frame_index = frame_index
        return new_frame

    def __len__(self) -> int:
        return self.duration

    @property
    def frames(self):
        for i in range(self.start_frame_index, self.end_frame_index):
            yield self[i]

    def has_index(self, frame_index):
        if frame_index < self.start_frame_index:
            return False

        if frame_index >= self.end_frame_index:
            return False

        return True


def _get_mask_layer(asset, xmlnode):
    layer_index = xmlnode.get("parentLayerIndex", None)
    if not layer_index:
        return None

    parent_layer = asset.layers[int(layer_index)]
    if parent_layer.layer_type == "mask":
        return parent_layer

    return None


class Layer(AnimationObject):
    def __init__(self, xflsvg, asset: "Asset", id: str, index: int, xmlnode):
        super().__init__()
        self.xflsvg = xflsvg
        self.asset = asset
        self.id = id
        self.index = index
        self.xmlnode = xmlnode
        self.name = xmlnode.get("name", None)
        self.visible = xmlnode.get("visible", "true") != "false"
        self.bundles = []
        self.end_frame_index = 0
        self.layer_type = xmlnode.get("layerType", "normal")
        self.mask_layer = _get_mask_layer(asset, xmlnode)
        self._frames = {}

        if self.xmlnode.frames:
            for bundle_xmlnode in self.xmlnode.frames.findChildren(recursive=False):
                new_bundle = ElementBundle(xflsvg, self, bundle_xmlnode)
                new_bundle.owner_element = self
                self.bundles.append(new_bundle)

                if self.end_frame_index == None:
                    self.end_frame_index = new_bundle.end_frame_index
                else:
                    self.end_frame_index = max(
                        self.end_frame_index, new_bundle.end_frame_index
                    )

    def __getitem__(self, frame_index: int) -> Frame:
        if frame_index in self._frames:
            return self._frames[frame_index]

        new_frame = Frame()
        for bundle in self.bundles:
            if bundle.has_index(frame_index):
                new_frame.add_child(bundle[frame_index])

        self._frames[frame_index] = new_frame
        new_frame.owner_element = self
        new_frame.frame_index = frame_index

        return new_frame

    def __len__(self) -> int:
        return self.end_frame_index

    @property
    def frames(self):
        for i in range(self.end_frame_index):
            yield self[i]


class Asset(AnimationObject):
    def __init__(self, xflsvg, id: str, xmlnode, timeline=None):
        super().__init__()
        print(id)
        self.xflsvg = xflsvg
        self.id = id
        self.layers = []
        self._frames = {}
        self.frame_count = 0

        timeline = timeline or xmlnode.timeline
        
        for index, xmlnode in enumerate(
            timeline.layers.findChildren(recursive=False)
        ):
            layer_id = f"{self.id}_L{index}"
            layer = Layer(xflsvg, self, layer_id, index, xmlnode)
            layer.owner_element = self
            self.layers.append(layer)
            self.frame_count = max(self.frame_count, layer.end_frame_index)

    def __getitem__(self, frame_index: int) -> Frame:
        if frame_index in self._frames:
            return self._frames[frame_index]

        new_frame = Frame()
        masked_frames = {}
        for layer in self.layers:
            if layer.layer_type == "mask":
                layer_frame = MaskedFrame(layer[frame_index])
                masked_frames[layer.index] = layer_frame
                new_frame.prepend_child(layer_frame)

            elif layer.layer_type == "normal":
                layer_frame = layer[frame_index]
                if layer.mask_layer:
                    masked_frames[layer.mask_layer.index].prepend_child(layer_frame)
                else:
                    new_frame.prepend_child(layer_frame)

        self._frames[frame_index] = new_frame
        new_frame.owner_element = self
        new_frame.frame_index = frame_index
        return new_frame

    def __len__(self) -> int:
        return self.frame_count

    @property
    def frames(self):
        for i in range(self.frame_count):
            yield self[i]


class Document(Asset):
    def __init__(self, xflsvg, xmlnode, timeline=0):
        available_timelines = xmlnode.timelines.findChildren('DOMTimeline', recursive=False)
        if isinstance(timeline, int):
            dom_timeline = available_timelines[timeline]
        elif isinstance(timeline, str):
            for dom_timeline in available_timelines:
                if dom_timeline.get('name') == timeline:
                    break
        
        assert dom_timeline, 'Unable to find timeline in XFL document'
        timeline_name = dom_timeline.get('name')

        super().__init__(xflsvg, f"file:///{xflsvg.id}.xfl/{timeline_name}", xmlnode, timeline=dom_timeline)
    
        


class XflReader:
    def __init__(self, xflsvg_dir: str):
        self.filepath = os.path.normpath(xflsvg_dir)  # deal with trailing /
        self.id = os.path.basename(self.filepath)  # MUST come after normpath
        self._assets = {}
        self._shapes = {}

        document_path = os.path.join(xflsvg_dir, "DOMDocument.xml")
        with open(document_path) as document_file:
            self.xmlnode = BeautifulSoup(document_file, "xml")

        self.width = int(self.xmlnode.DOMDocument["width"])
        self.height = int(self.xmlnode.DOMDocument["height"])
        self.background = self.xmlnode.DOMDocument.get("backgroundColor", "#FFFFFF")
    
    def get_timeline(self, timeline=0):
        return Document(self, self.xmlnode, timeline)

    def get_safe_asset(self, safe_asset_id):
        asset_id = html.unescape(safe_asset_id)

        if asset_id in self._assets:
            return self._assets[asset_id]

        default_asset_path = os.path.join(
            self.filepath, "LIBRARY", f"{safe_asset_id}.xml"
        )
        if os.path.exists(default_asset_path):
            asset_path = default_asset_path
        else:
            asset_path = default_asset_path.replace("&", "_")

        with open(asset_path) as asset_file:
            asset_soup = BeautifulSoup(asset_file, "xml")

        asset = Asset(self, asset_id, asset_soup)
        self._assets[asset_id] = asset
        return asset

    def get_asset(self, asset_id):
        return self.get_safe_asset(html.escape(asset_id))

    def get_shape(self, xmlnode, asset_id, layer_index, frame_index, path):
        key = (asset_id, layer_index, frame_index, tuple(path))
        if key in self._shapes:
            return self._shapes[key]

        xmlnode = etree.fromstring(str(xmlnode))
        normal_svg = xfl_domshape_to_svg(xmlnode, False)
        mask_svg = xfl_domshape_to_svg(xmlnode, True)
        result = ShapeFrame(normal_svg, mask_svg)

        self._shapes[key] = result
        return result


class XflRenderer:
    _contexts = threading.local()
    _contexts.stack = []

    @classmethod
    def current(cls):
        if XflRenderer._contexts.stack == []:
            raise Exception(
                "render() should only be called within an XflRenderer context."
            )
        return XflRenderer._contexts.stack[-1]

    def render_shape(self, svg_frame, *args, **kwargs):
        pass

    def push_transform(self, transformed_frame, *args, **kwargs):
        pass

    def pop_transform(self, transformed_frame, *args, **kwargs):
        pass

    def push_mask(self, masked_frame, *args, **kwargs):
        pass

    def pop_mask(self, masked_frame, *args, **kwargs):
        pass

    def push_masked_render(self, masked_frame, *args, **kwargs):
        pass

    def pop_masked_render(self, masked_frame, *args, **kwargs):
        pass

    def on_frame_rendered(self, *args, **kwargs):
        pass

    def __enter__(self):
        XflRenderer._contexts.stack.append(self)
        return self

    def __exit__(self, *exc):
        XflRenderer._contexts.stack.pop()
