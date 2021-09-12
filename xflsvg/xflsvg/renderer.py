import cairosvg
import cairocffi as cairo

from .xflsvg import Snapshot
from .xflsvg import XflSvg


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
        context.save()
        surface = self.surface
        origin = self.loader.load_origin()
        context.translate(*origin)
        context.translate(-self._width / 2, -self._height / 2)
        context.set_source_surface(self.surface)
        context.paint()
        context.restore()


_IDENTITY_MATRIX = [1, 0, 0, 1, 0, 0]


class TransformedSnapshot(Snapshot):
    def __init__(self, original, origin=[0, 0], matrix=None):
        super().__init__()
        self.original = original
        self.origin = origin
        matrix = matrix or _IDENTITY_MATRIX
        self.matrix = cairo.Matrix(*matrix)
        self.original.parent = self

    def render(self, context):
        self.original.parent = self

        context.save()
        context.translate(self.origin[0], self.origin[1])
        context.transform(self.matrix)
        self.original.render(context)
        context.restore()


def to_png(self, width, height):
    output = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    with cairo.Context(output) as context:
        context.translate(width * 0.5, height * 0.5)
        self.render(context)

    return output.write_to_png(None)

class RenderingXflSvg(XflSvg):
    def __init__(self, xflsvg_dir) -> None:
        super().__init__(self, SVGSnapshot, TransformedSnapshot, xflsvg_dir)
    
    # add methods for rendering a shape, asset, frame, etc
