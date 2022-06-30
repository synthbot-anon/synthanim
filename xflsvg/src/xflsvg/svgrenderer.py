import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


from .xflsvg import XflReader, XflRenderer
from xfl2svg.shape.shape import xfl_domshape_to_svg
from .tweens import get_color_map
import os
import math

_EMPTY_SVG = '<svg height="1px" width="1px" viewBox="0 0 1 1" />'
_IDENTITY_MATRIX = [1, 0, 0, 1, 0, 0]


def color_to_svg_filter(color):
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


def _with_border(domshape):
    soup = BeautifulSoup(domshape, 'xml').DOMShape

    if soup.fills:
        fills = get_color_map(soup.fills, 'FillStyle')
    else:
        fills = {}
    
    if soup.strokes:
        strokes = get_color_map(soup.strokes, 'StrokeStyle')
    else:
        strokes = {}
        new_strokes = BeautifulSoup("""
            <strokes />
        """, 'xml')
        soup.append(new_strokes)

    reverse_strokes_map = dict([(x[1], x[0]) for x in strokes.items()])
    
    modified = False
    for edge in soup.edges.findChildren('Edge', recursive=False):
        if edge.get('strokeStyle'):
            continue

        fillStyle0 = edge.get('fillStyle0')
        fillStyle1 = edge.get('fillStyle1')
        if not fillStyle0 and not fillStyle1:
            continue
        
        useFillStyle = int(fillStyle0 or fillStyle1)
        color = fills[useFillStyle]
        stroke_index = reverse_strokes_map.get(color, None)
        if not stroke_index:
            stroke_index = len(strokes) + 1
            
            color_attr = f'color="{color[0]}"'
            alpha_attr = ""
            if color[1] != 1:
                alpha_attr = f'alpha="{color[1]}"'

            new_stroke = BeautifulSoup(f"""
                    <StrokeStyle index="{stroke_index}">
                        <SolidStroke scaleMode="normal" caps="none" vectorEffect="non-scaling-stroke" weight="0.1">
                            <fill>
                                <SolidColor {color_attr} {alpha_attr} />
                            </fill>
                        </SolidStroke>
                    </StrokeStyle>

                """, 'xml')
            
            soup.strokes.append(new_stroke.StrokeStyle)
            strokes[stroke_index] = color
            reverse_strokes_map[color] = stroke_index
            
        edge['strokeStyle'] = str(stroke_index)
        modified = True
    
    if not modified:
        return domshape
    
    return str(soup)


class SvgRenderer(XflRenderer):
    HREF = ET.QName("http://www.w3.org/1999/xlink", "href")

    def __init__(self) -> None:
        super().__init__()
        self.defs = {}
        self.context = [
            [],
        ]

        self.mask_depth = 0
        self.shape_cache = {}
        self.mask_cache = {}

        self._captured_frames = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

        self.force_x = None
        self.force_y = None
        self.force_width = None
        self.force_height = None

    def render_shape(self, shape_snapshot, *args, **kwargs):
        if self.mask_depth == 0:
            svg = self.shape_cache.get(shape_snapshot.identifier, None)
            if not svg:
                domshape = ET.fromstring(shape_snapshot.domshape)
                svg = xfl_domshape_to_svg(domshape, False)
                self.shape_cache[shape_snapshot.identifier] = svg
        else:
            svg = self.mask_cache.get(shape_snapshot.identifier, None)
            if not svg:
                domshape = ET.fromstring(shape_snapshot.domshape)
                svg = xfl_domshape_to_svg(domshape, True)
                self.mask_cache[shape_snapshot.identifier] = svg
        
        fill_g, stroke_g, extra_defs = svg

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
            matrix = " ".join([str(x) for x in transformed_snapshot.matrix])
            transform_data["transform"] = f"matrix({matrix})"

        if self.mask_depth == 0:
            color = transformed_snapshot.color
            if color and not color.is_identity():
                filter_element = color_to_svg_filter(transformed_snapshot.color)
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
    
    def save_frame(self, frame):
        self._captured_frames.append([self.defs, self.context])
        self.defs = {}
        self.context = [
            [],
        ]

        if self.x == None:
            self.x = frame.box[0]
            self.y = frame.box[1]
            self.width = frame.box[2] - frame.box[0]
            self.height = frame.box[3] - frame.box[1]
        else:
            self.x = min(self.x, frame.box[0])
            self.y = min(self.y, frame.box[1])
            self.width = max(self.width, frame.box[2] - frame.box[0])
            self.height = max(self.height, frame.box[3] - frame.box[1])
        
    def set_camera(self, x, y, width, height):
        self.force_x = x
        self.force_y = y
        self.force_width = width
        self.force_height = height
    

    # def compile(self, width, height, x=0, y=0, scale=1):
    def compile(self, output_filename=None, scale=1, padding=0):
        result = []
        x = _conditional(self.force_x, self.x) - padding
        y = _conditional(self.force_y, self.y) - padding
        width = _conditional(self.force_width, self.width) + 2*padding
        height = _conditional(self.force_height, self.height) + 2*padding

        for i, data in enumerate(self._captured_frames):
            defs, context = data
            svg = ET.Element(
                "svg",
                {
                    "xmlns": "http://www.w3.org/2000/svg",
                    "version": "1.1",
                    "preserveAspectRatio": "none",
                    "x": f"{x*scale}px",
                    "y": f"{y*scale}px",
                    "width": f"{width*scale}px",
                    "height": f"{height*scale}px",
                    "viewBox": f"{x} {y} {width} {height}",
                },
            )

            defs_element = ET.SubElement(svg, "defs")
            defs_element.extend(defs.values())
            svg.extend(context[0])
            image = ET.ElementTree(svg)

            if output_filename:
                name, ext = os.path.splitext(output_filename)
                with open(f'{name}{"%04d" % i}{ext}', 'w') as outp:
                    image.write(outp, encoding='unicode')
            
            result.append(image)

        return result

def _conditional(forced_value, calculated_value):
    if forced_value != None:
        return forced_value
    return calculated_value