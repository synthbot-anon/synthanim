import numpy
import math
import xml.etree.ElementTree as etree
from collections.abc import Iterable
from bs4 import BeautifulSoup

from .util import ColorObject
from .domshape.edge import EDGE_TOKENIZER

def deserialize_matrix(matrix):
    if matrix == None:
        return numpy.identity(2), numpy.zeros(2)

    linear = numpy.array([
        [matrix[0], matrix[1]],
        [matrix[2], matrix[3]]
    ])
    translation = numpy.array([matrix[4], matrix[5]])
    return linear, translation

def serialize_matrix(linear, translation):
    return [
        linear[0,0],
        linear[0,1],
        linear[1,0],
        linear[1,1],
        translation[0],
        translation[1]
    ]

def matrix_interpolation(start, end, n_frames, ease):
    start_linear, start_translation = deserialize_matrix(start)
    end_linear, end_translation = deserialize_matrix(end)

    srot, sshear, sx, sy = adobe_decomposition(start_linear)
    erot, eshear, ex, ey = adobe_decomposition(end_linear)

    if abs(erot - srot) > math.pi:
        srot += (erot - srot) / abs(erot - srot) * 2 * math.pi

    for i in range(n_frames):
        frot = ease['rotation'](i / (n_frames - 1)).y
        fscale = ease['scale'](i / (n_frames - 1)).y
        fpos = ease['position'](i / (n_frames - 1)).y
        
        interpolated_linear = adobe_matrix(
            frot*erot + (1-frot)*srot,
            frot*eshear + (1-frot)*sshear,
            fscale*ex + (1-fscale)*sx,
            fscale*ey + (1-fscale)*sy
        )
        interpolated_translation = fpos*end_translation + (1-fpos)*start_translation

        yield serialize_matrix(interpolated_linear, interpolated_translation)


def adobe_decomposition(a):
    rotation = math.atan2(a[1,0], a[0,0])
    shear = math.pi/2 + rotation - math.atan2(a[1,1], a[0,1])
    if math.cos(shear) < 0:
        shear = shear % (math.pi*2) - 2 * math.pi
    scale_x = math.sqrt(a[0,0]**2 + a[1,0]**2)
    scale_y = math.sqrt(a[0,1]**2 + a[1,1]**2)
    
    return rotation, shear, scale_x, scale_y


def adobe_matrix(rotation, shear, scale_x, scale_y):    
    rotation_matrix = numpy.array([
        [math.cos(rotation), -math.sin(rotation)],
        [math.sin(rotation), math.cos(rotation)]
    ])
    
    skew_matrix = numpy.array([
        [1, math.tan(shear)],
        [0, 1]
    ])
    
    scale_matrix = numpy.array([
        [scale_x, 0],
        [0, scale_y * math.cos(shear)]
    ])
    
    return rotation_matrix @ skew_matrix @ scale_matrix


def color_interpolation(start, end, n_frames, ease):
    if start == None:
        start = ColorObject()
    if end == None:
        end = ColorObject()

    for i in range(n_frames):
        frac = ease['color'](i / (n_frames - 1)).y
        # need to do filters too
        yield frac*end + (1-frac)*start


def interpolate_points(start, end, i, duration, ease):
    sx, sy = start
    ex, ey = end
    frac = ease['position'](i / (duration - 1)).y
    return [(ex-sx)*frac + sx, (ey-sy)*frac + sy]

def split_colors(color):
    if not color:
        return 0, 0, 0
    if not color.startswith('#'):
        raise Exception(f'invalid color: {color}')
    assert len(color) == 7
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    return r, g, b

def interpolate_value(x, y, idx, duration, ease):
    frac = ease(idx / (duration - 1)).y
    result = (1-frac)*x + frac*y
    return result

def interpolate_color(x, y, i, duration, ease):
    rx, gx, bx = split_colors(x)
    ry, gy, by = split_colors(y)
    ri = round(interpolate_value(rx, ry, i, duration, ease['color']))
    gi = round(interpolate_value(gx, gy, i, duration, ease['color']))
    bi = round(interpolate_value(bx, by, i, duration, ease['color']))
    return '#%02X%02X%02X' % (ri, gi, bi)

def _get_color_map(xmlnode, name):
    result = {}
    for child in xmlnode.findChildren(name, recursive=False):
        index = int(child.get('index'))
        color = child.SolidColor.get('color')
        result[index] = color
    return result

def interpolate_color_map(name, start, end, i, duration, ease):
    start_map = _get_color_map(start, name)
    end_map = _get_color_map(end, name)

    if not start_map:
        return start

    interp_map = {}
    for key, scol in start_map.items():
        ecol = end_map[key]
        interp_map[key] = interpolate_color(scol, ecol, i, duration, ease)
    
    result = BeautifulSoup(str(start), 'xml')
    for child in list(result.findChildren(name, recursive=False)):
        key = int(child.get('index'))
        child.SolidColor.set('color', interp_map[key])

    return result

def _segment_index(index):
    if index == None:
        return None
    return int(index) + 1

def _xfl_point(point):
    x, y = point
    return f'{round(x, 6)} {round(y, 6)}'

def _parse_number(num: str) -> float:
    """Parse an XFL edge format number."""
    if num[0] == "#":
        # Signed, 32-bit number in hex
        parts = num[1:].split(".")
        # Pad to 8 digits
        hex_num = "{:>06}{:<02}".format(*parts)
        num = int.from_bytes(bytes.fromhex(hex_num), "big", signed=True)
        # Account for hex scaling and Animate's 20x scaling
        return num
    else:
        # Decimal number. Account for Animate's 20x scaling
        return float(num) * 256

def _get_start_point(shape):
    edges = shape.xmlnode.Edge.get('edges')
    tokens = iter(EDGE_TOKENIZER.findall(edges))

    moveTo = next(tokens)
    x = _parse_number(next(tokens))
    y = _parse_number(next(tokens))
    return x, y


def _parse_coord(coord):
    x, y = coord.split(', ')
    print(x, y)
    return _parse_number(x), _parse_number(y)

def shape_interpolation(segment_xmlnode, start, end, n_frames, ease):
    yield start.xmlnode

    for i in range(1, n_frames-1):
        fills = interpolate_color_map(
            'FillStyle', start.xmlnode.fills, end.xmlnode.fills, i, n_frames, ease)
        strokes = interpolate_color_map(
            'StrokeStyle', start.xmlnode.strokes, end.xmlnode.strokes, i, n_frames, ease)
        
        fillStyle1 = _segment_index(segment_xmlnode.get('fillIndex1', None))
        strokeStyle = _segment_index(segment_xmlnode.get('strokeIndex1', None))
        points = []
        
        startA = segment_xmlnode.get('startPointA', None)
        startB = segment_xmlnode.get('startPointB', None)
        if startA:
            startA = _parse_coord(startA)
        else:
            startA = _get_start_point(start)
        if startB:
            startB = _parse_coord(startB)
        else:
            startB = startB or _get_start_point(end)

        prev_point = interpolate_points(startA, startB, i, n_frames, ease)
        points.append(f'!{_xfl_point(prev_point)}')
        
        for curve in segment_xmlnode.findChildren('MorphCurves', recursive=False):
            anchA = _parse_coord(curve.get('anchorPointA'))
            anchB = _parse_coord(curve.get('anchorPointB'))
            
            if curve.get('isLine', None):
                lineTo = interpolate_points(anchA, anchB, i, n_frames, ease)
                points.append(f'|{_xfl_point(lineTo)}')
            else:
                ctrlA = _parse_coord(curve.get('controlPointA'))
                ctrlB = _parse_coord(curve.get('controlPointB'))
                ctrl = interpolate_points(ctrlA, ctrlB, i, n_frames, ease)
                quadTo = interpolate_points(anchA, anchB, i, n_frames, ease)
                points.append(f'[{_xfl_point(ctrl)} {_xfl_point(quadTo)}')
        
        points.append(f'')
        points = ''.join(points)

        yield f"""<DOMShape>
                {fills.fills}
                {strokes.strokes}
                <edges>
                    <Edge fillStyle1="{fillStyle1}" strokeStyle="{strokeStyle}" edges="{points}"/>
                </edges>
            </DOMShape>"""
    
    yield end.xmlnode
