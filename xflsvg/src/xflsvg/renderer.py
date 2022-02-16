from numpy.lib.twodim_base import mask_indices
from .xflsvg import Frame
from .xflsvg import XflReader, XflRenderer, Layer
import pandas
from contextlib import contextmanager
import threading
import xml.etree.ElementTree as ET

_EMPTY_SVG = '<svg height="1px" width="1px" viewBox="0 0 1 1" />'
_IDENTITY_MATRIX = ["1", "0", "0", "1", "0", "0"]


def _color_to_svg_filter(color):
    # fmt: off
    matrix = (
        "{0} 0 0 0 {4} "
        "0 {1} 0 0 {5} "
        "0 0 {2} 0 {6} "
        "0 0 0 {3} {7}"
    ).format(
        color.mr, color.mg, color.mb, color.ma,
        color.dr, color.dg, color.db, color.da,
    )
    # fmt: on

    filter = ET.Element(
        "filter",
        {
            "id": color.id,
            "x": "-20%",
            "y": "-20%",
            "width": "140%",
            "height": "140%",
            "color-interpolation-filters": "sRGB",
        },
    )

    ET.SubElement(
        filter,
        "feColorMatrix",
        {
            "in": "SourceGraphic",
            "type": "matrix",
            "values": matrix,
        },
    )

    return filter


class SvgRenderer(XflRenderer):
    HREF = ET.QName("http://www.w3.org/1999/xlink", "href")

    def __init__(self) -> None:
        super().__init__()
        self.defs = {}
        self.context = [
            [],
        ]

        self.mask_depth = 0
        self.cache = {}

    def render_shape(self, shape_snapshot, *args, **kwargs):
        if self.mask_depth == 0:
            fill_g, stroke_g, extra_defs = shape_snapshot.normal_svg
        else:
            fill_g, stroke_g, extra_defs = shape_snapshot.mask_svg

        self.defs.update(extra_defs)
        id = f"Shape{shape_snapshot.identifier}"

        if fill_g is not None:
            fill_id = f"{id}_FILL"
            fill_g.set("id", fill_id)
            self.defs[fill_id] = fill_g

            fill_use = ET.Element("use", {SvgRenderer.HREF: "#" + fill_id})
            self.context[-1].append(fill_use)

        if stroke_g is not None:
            stroke_id = f"{id}_STROKE"
            stroke_g.set("id", stroke_id)
            self.defs[stroke_id] = stroke_g

            self.context[-1].append(
                ET.Element("use", {SvgRenderer.HREF: "#" + stroke_id})
            )

    def push_transform(self, transformed_snapshot, *args, **kwargs):
        self.context.append([])

    def pop_transform(self, transformed_snapshot, *args, **kwargs):
        transform_data = {}
        if (
            transformed_snapshot.matrix
            and transformed_snapshot.matrix != _IDENTITY_MATRIX
        ):
            matrix = " ".join(transformed_snapshot.matrix)
            transform_data["transform"] = f"matrix({matrix})"

        if self.mask_depth == 0:
            color = transformed_snapshot.color
            if color and not color.is_identity():
                filter_element = _color_to_svg_filter(transformed_snapshot.color)
                self.defs[color.id] = filter_element
                transform_data["filter"] = f"url(#{color.id})"

        if transform_data != {}:
            transform_element = ET.Element("g", transform_data)
            transform_element.extend(self.context.pop())
            self.context[-1].append(transform_element)
        else:
            items = self.context.pop()
            self.context[-1].extend(items)

    def push_mask(self, masked_snapshot, *args, **kwargs):
        self.mask_depth += 1
        self.context.append([])

    def pop_mask(self, masked_snapshot, *args, **kwargs):
        mask_id = f"Mask_{masked_snapshot.identifier}"
        mask_element = ET.Element("mask", {"id": mask_id})
        mask_element.extend(self.context.pop())

        self.defs[mask_id] = mask_element
        self.context[-1].append(mask_element)

        masked_items = ET.Element("g", {"mask": f"url(#{mask_id})"})
        self.context[-1].append(masked_items)
        self.mask_depth -= 1

    def push_masked_render(self, masked_snapshot, *args, **kwargs):
        self.context.append([])

    def pop_masked_render(self, masked_snapshot, *args, **kwargs):
        children = self.context.pop()
        masked_items = self.context[-1][-1]
        masked_items.extend(children)

    def compile(self, width, height, x=0, y=0):
        svg = ET.Element(
            "svg",
            {
                # `xmlns:xlink` is automatically added if any element uses
                # `xlink:href`. We don't explicitly use the SVG namespace,
                # though, so we need to add it here.
                "xmlns": "http://www.w3.org/2000/svg",
                "version": "1.1",
                "preserveAspectRatio": "none",
                "x": f"{x}px",
                "y": f"{y}px",
                "width": f"{width}px",
                "height": f"{height}px",
                "viewBox": f"0 0 {width} {height}",
            },
        )

        defs_element = ET.SubElement(svg, "defs")
        defs_element.extend(self.defs.values())
        svg.extend(self.context[0])
        # for item in self.context[0]:
        # svg.extend(item)

        return ET.ElementTree(svg)


class DataFrameRenderer:
    def __init__(self, tables_dir, spritemap_dir):
        self.shapes = pandas.read_parquet(f"{tables_dir}/shapes.parquet")
        self.frames = pandas.read_parquet(f"{tables_dir}/frames.parquet")
        self.assets = pandas.read_parquet(f"{tables_dir}/assets.data.parquet")
        self.documents = pandas.read_parquet(f"{tables_dir}/documents.data.parquet")
        self.spritemap = SvgSpritemap(None, spritemap_dir)

        self.cached_shapes = {}

    def render_frame(self, frame_id, context=None):
        context = context or _cairo_context.stack[-1]
        if not self.shapes[self.shapes["frameId"] == frame_id].empty:
            self.render_shape(frame_id, context)
            return

        data = self.frames[self.frames["frameId"] == frame_id].iloc[0]

        context.save()
        if data["origin"]:
            context.translate(*data["origin"])
        if data["matrix"]:
            context.transform(cairo.Matrix(*data["matrix"]))

        for child in data["childFrameIds"][::-1]:
            self.render_frame(child, context)

        context.restore()

    def render_shape(self, frame_id, context=None):
        context = context or _cairo_context.stack[-1]
        if frame_id in self.cached_shapes:
            self.cached_shapes[frame_id].render(context)
            return

        data = self.shapes[self.shapes["frameId"] == frame_id].iloc[0]
        loader = SvgLoader(
            load_sprite=lambda: self.spritemap.get_sprite_ex(data),
            load_origin=lambda: self.spritemap.get_origin_ex(data),
        )
        result = RenderableSVGSnapshot(loader)
        self.cached_shapes[frame_id] = result

        result.render(context)
