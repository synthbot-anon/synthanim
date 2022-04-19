from contextlib import contextmanager
import json
import pandas
from .xflsvg import DOMShape, Frame, MaskedFrame, XflRenderer, consume_frame_identifier
from .xflsvg import ShapeFrame
from .domshape.shape import xfl_domshape_to_svg
from .util import ColorObject

_IDENTITY_MATRIX = [1, 0, 0, 1, 0, 0]

def color_to_filter(color):
    return {
        'multiply': [color.mr, color.mg, color.mb, color.ma],
        'shift': [color.dr, color.dg, color.db, color.da]
    }


class TableExporter(XflRenderer):
    def __init__(self):
        self.mask_depth = 0
        self.shapes = {}
        self.context = [[]]
        self.frames = {}
        self._captured_frames = []


    def render_shape(self, shape_snapshot, *args, **kwargs):
        self.shapes[shape_snapshot.identifier] = shape_snapshot.domshape
        self.context[-1].append(shape_snapshot.identifier)


    def push_transform(self, transformed_snapshot, *args, **kwargs):
        self.context.append([])

    def pop_transform(self, transformed_snapshot, *args, **kwargs):
        frame_data = {}
        if self.mask_depth == 0:
            color = transformed_snapshot.color
            if color and not color.is_identity():
                frame_data["filter"] = color_to_filter(transformed_snapshot.color)

        if (
            transformed_snapshot.matrix
            and transformed_snapshot.matrix != _IDENTITY_MATRIX
        ):
            matrix = [float(x) for x in transformed_snapshot.matrix]
            frame_data["transform"] = matrix

        
        frame_data['children'] = self.context.pop()
        self.frames[transformed_snapshot.identifier] = frame_data
        self.context[-1].append(transformed_snapshot.identifier)


    def push_mask(self, masked_snapshot, *args, **kwargs):
        self.mask_depth += 1
        self.context.append([])

    def pop_mask(self, masked_snapshot, *args, **kwargs):
        mask_data = {
            'children': self.context.pop()
        }
        self.frames[masked_snapshot.identifier] = mask_data
        self.mask_depth -= 1

    def push_masked_render(self, masked_snapshot, *args, **kwargs):
        self.context.append([])

    def pop_masked_render(self, masked_snapshot, *args, **kwargs):
        frame_data = {
            'mask': masked_snapshot.identifier,
            'children': self.context.pop()
        }
        
        render_index = consume_frame_identifier()
        self.frames[render_index] = frame_data
        self.context[-1].append(render_index)

    def save_frame(self):
        assert len(self.context) == 1
        children = self.context[0]

        if len(children) > 1:
            frame_data = {
                'children': children
            }
            render_index = consume_frame_identifier()
            self.frames[render_index] = frame_data
        else:
            render_index = children[0]
        
        self._captured_frames.append(render_index)
        self.context = [[]]
        
    
    def compile_frames(self):
        return self.shapes, self.frames, self._captured_frames
        
def get_table_frame(shapes, frames, render_index):
    if render_index in shapes:
        domshape = shapes[render_index]
        shape = ShapeFrame(domshape)
        shape.identifier = render_index
        return shape
    else:
        frame_data = frames[render_index]
        children = [get_table_frame(shapes, frames, x) for x in frame_data['children']]

        if 'mask' in frame_data:
            mask = get_table_frame(shapes, frames, frame_data['mask'])
            frame = MaskedFrame(mask, children)
            frame.identifier = render_index
            return frame

        transform = frame_data.get('transform', None)
        filter = frame_data.get('filter', None)
        if filter:
            filter = ColorObject(*filter['multiply'], *filter['shift'])
        frame = Frame(transform, filter, children)
        frame.identifier = render_index
        return frame


