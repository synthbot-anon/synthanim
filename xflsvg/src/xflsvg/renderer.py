try:
    import cairosvg
    import cairocffi as cairo
except:
    pass

from .xflsvg import Snapshot
from .xflsvg import XflSvg, SvgSpritemap, SvgLoader
import pandas
from contextlib import contextmanager
import threading

_EMPTY_SVG = '<svg height="1px" width="1px" viewBox="0 0 1 1" />'
_IDENTITY_MATRIX = [1, 0, 0, 1, 0, 0]
_ORIGIN_POINT = [0, 0]

_cairo_context = threading.local()
_cairo_context.stack = []

@contextmanager
def png_canvas(path, width, height):
    try:
        output = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        with cairo.Context(output) as context:
            _cairo_context.stack.append(context)
            context.translate(width * 0.5, height * 0.5)
            yield context
    finally:
        _cairo_context.stack.pop()
        output.write_to_png(path)


class RenderableSVGSnapshot:
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






class XflSvgRenderer(XflSvg):
    def __init__(self, xflsvg_dir) -> None:
        super().__init__(xflsvg_dir)
        self.svg_cache = {}
    
    def render_svg(self, svg_snapshot, context=None):
        context = context or _cairo_context.stack[-1]
        path = svg_snapshot.path
        if path not in self.svg_cache:
            self.svg_cache[path] = RenderableSVGSnapshot(svg_snapshot.loader)

        self.svg_cache[path].render(context)

    def push_transform(self, transformed_snapshot, context=None):
        context = context or _cairo_context.stack[-1]
        context.save()

        if transformed_snapshot.origin:
            context.translate(*transformed_snapshot.origin)
        if transformed_snapshot.matrix:
            matrix = cairo.Matrix(*transformed_snapshot.matrix)
            context.transform(matrix)

    def pop_transform(self, transformed_snapshot, context=None):
        context = context or _cairo_context.stack[-1]
        context.restore()


class DataFrameRenderer:
    def __init__(self, tables_dir, spritemap_dir):
        self.shapes = pandas.read_parquet(f'{tables_dir}/shapes.parquet').drop_duplicates().rename(columns={'svgfilename': 'filename'})
        self.frames = pandas.read_parquet(f'{tables_dir}/frames.parquet')
        self.assets = pandas.read_parquet(f'{tables_dir}/assets.data.parquet')
        self.spritemap = SvgSpritemap(None, spritemap_dir)

        self.cached_shapes = {}
    
    def render_frame(self, frame_id, context=None):
        context = context or _cairo_context.stack[-1]
        if frame_id in self.shapes.index:
            self.render_shape(frame_id, context)
            return
        
        data = self.frames.loc[frame_id]
        children = data['childFrameIds']
        matrix = cairo.Matrix(*(data['matrix'] or _IDENTITY_MATRIX))
        origin = data['origin'] or _ORIGIN_POINT

        context.save()
        context.translate(*origin)
        context.transform(matrix)

        for child in children[::-1]:
            self.render_frame(child, context)
        
        context.restore()

    
    def render_shape(self, frame_id, context=None):
        context = context or _cairo_context.stack[-1]
        if frame_id in self.cached_shapes:
            self.cached_shapes[frame_id].render(context)
            return

        data = self.shapes.loc[frame_id]
        print(data)
        loader = SvgLoader(
            load_sprite=lambda: self.spritemap.get_sprite_ex(data),
            load_origin=lambda: self.spritemap.get_origin_ex(data))
        result = RenderableSVGSnapshot(loader)
        self.cached_shapes[frame_id] = result

        result.render(context)


