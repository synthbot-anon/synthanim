try:
    import cairosvg
    import cairocffi as cairo
except:
    pass

from .xflsvg import Snapshot
from .xflsvg import XflSvg


_EMPTY_SVG = '<svg height="1px" width="1px" viewBox="0 0 1 1" />'


class SVGSnapshot:
    def __init__(self, loader):
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


def to_png(self, width, height):
    output = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    with cairo.Context(output) as context:
        context.translate(width * 0.5, height * 0.5)
        self.render(context)

    return output.write_to_png(None)

class RenderingXflSvg(XflSvg):
    def __init__(self, xflsvg_dir) -> None:
        super().__init__(xflsvg_dir)
        self.svg_cache = {}
    
    def render_svg(self, svg_snapshot, context):
        path = svg_snapshot.path
        if path not in self.svg_cache:
            self.svg_cache[path] = SVGSnapshot(svg_snapshot.loader)

        self.svg_cache[path].render(context)

    def push_transform(self, transformed_snapshot, context):
        matrix = cairo.Matrix(*transformed_snapshot.matrix)
        context.save()
        context.translate(*transformed_snapshot.origin)
        context.transform(matrix)

    def pop_transform(self, transformed_snapshot, context):
        context.restore()
