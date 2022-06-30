from contextlib import contextmanager
import json
import pandas
from .xflsvg import DOMShape, Frame, MaskedFrame, XflRenderer, consume_frame_identifier
from .xflsvg import ShapeFrame
from xfl2svg.shape.shape import xfl_domshape_to_svg
from .util import ColorObject
import os

_IDENTITY_MATRIX = [1, 0, 0, 1, 0, 0]

def color_to_filter(color):
    return {
        'multiply': [color.mr, color.mg, color.mb, color.ma],
        'shift': [color.dr, color.dg, color.db, color.da]
    }


class RenderTracer(XflRenderer):
    def __init__(self):
        self.mask_depth = 0
        self.shapes = {}
        self.context = [[]]
        self.frames = {}
        self._captured_frames = []
        self.labels = {}
    
    def set_camera(self, x, y, width, height):
        pass
    
    def on_frame_rendered(self, frame, *args, **kwargs):
        if frame.data:
            self.labels.setdefault(frame.identifier, {}).update(frame.data)

    def render_shape(self, shape_snapshot, *args, **kwargs):
        self.shapes[shape_snapshot.identifier] = shape_snapshot.domshape
        self.labels
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

    def save_frame(self, frame=None):
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
    
    def set_box(*args, **kwargs):
        pass
    
    def compile(self, output_folder=None):
        if path:        
            os.makedirs(output_folder, exist_okay=True)
            with open(os.path.join(output_folder, 'shapes.json'), 'w') as outp:
                json.dump(shapes, outp)
            with open(os.path.join(output_folder, 'frames.json'), 'w') as outp:
                json.dump(frames, outp)
            with open(os.path.join(output_folder, 'labels.json'), 'w') as outp:
                json.dump(labels, outp)
        
        return self.shapes, self.frames, self.labels
        
        



class RenderTraceReader:
    def __init__(self, input_folder):
        with open(os.path.join(input_folder, 'shapes.json'), 'r') as inp:
            self.shapes = json.load(inp)
        with open(os.path.join(input_folder, 'frames.json'), 'r') as inp:
            self.frames = json.load(inp)
        with open(os.path.join(input_folder, 'labels.json'), 'r') as inp:
            self.labels = json.load(inp)
        self.frame_cache = {}
        self._box = None
    
    def get_camera(self):
        if self._box:
            return self._box
        
        for frame_id, label in self.labels.items():
            if 'timeline' not in label:
                continue
            
            if not label['timeline'].lower().startswith('file://'):
                continue
            
            break
        
        self._box = [0, 0, label['width'], label['height']]
        return self._box

    
    def get_timeline(self, id=None):
        available_scenes = set()
        result = []
        for frame_id, label in self.labels.items():
            if 'timeline' not in label:
                continue
            
            if id:
                if label['timeline'] == id:
                    result.append((frame_id, label['frame']))
                continue

            if not label['timeline'].lower().startswith('file://'):
                continue
            available_scenes.add(label['timeline'])
            result.append((frame_id, label['frame']))
        
        if not id:
            if len(available_scenes) == 0:
                raise Exception('No default scene found in the input rendertrace. Please specify a timeline to use.')
            if len(available_scenes) != 1:
                option_str = "\n".join(available_scenes)
                raise Exception(f'You need to specify which timeline to use from this rendertrace. Options:\n{option_str}')
        
        result = sorted(result, key=lambda x: x[1])
        for frame_id, i in result:
            yield self.get_table_frame(frame_id)
        
        print('done')
    
    def get_table_frame(self, render_index):
        if str(render_index) in self.shapes:
            domshape = self.shapes[str(render_index)]
            shape = ShapeFrame(domshape)
            shape.identifier = render_index
            self.frame_cache[render_index] = shape
            return shape
        else:
            frame_data = self.frames[str(render_index)]
            children = [self.get_table_frame(x) for x in frame_data['children']]

            if 'mask' in frame_data:
                mask = self.get_table_frame(frame_data['mask'])
                frame = MaskedFrame(mask, children)
                frame.identifier = int(render_index)
                self.frame_cache[render_index] = frame
                return frame

            transform = frame_data.get('transform', None)
            filter = frame_data.get('filter', None)
            if filter:
                filter = ColorObject(*filter['multiply'], *filter['shift'])
            frame = Frame(transform, filter, children)
            frame.identifier = int(render_index)
            self.frame_cache[render_index] = frame
            return frame
        

            




