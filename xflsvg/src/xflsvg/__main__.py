import argparse
import json
import logging
import os
import traceback

from .xflsvg import XflReader
from .exporter import TableExporter, get_table_frame
from .svgrenderer import SvgRenderer

def export(input_folder, output_folder):
    xfl = XflReader(input_folder)
    timeline = xfl.get_timeline()
    exporter = TableExporter()

    for frame in list(timeline):
        with exporter:
            frame.render()
        exporter.save_frame()
    
    shapes, frames, labels, rendered = exporter.compile_frames()
    with open(os.path.join(output_folder, 'shapes.json'), 'w') as outp:
        json.dump(shapes, outp)
    with open(os.path.join(output_folder, 'frames.json'), 'w') as outp:
        json.dump(frames, outp)
    with open(os.path.join(output_folder, 'labels.json'), 'w') as outp:
        json.dump(labels, outp)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # export to tables
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--export', required=False, action='store_true')
    group.add_argument('--render', required=False, action='store_true')

    args = parser.parse_known_args()[0]
    if args.export:
        parser = argparse.ArgumentParser()
        parser.add_argument('--export', required=True, action='store_true')
        parser.add_argument('input_folder', type=str)
        parser.add_argument('output_folder', type=str)
        
        args = parser.parse_args()
        input_folder = os.path.normpath(args.input_folder)

        for root, dirs, files in os.walk(input_folder):
            if not os.path.exists(os.path.join(root, 'DOMDocument.xml')):
                continue
            
            relpath = os.path.relpath(root, input_folder)
            target_folder = os.path.join(args.output_folder, relpath)
            
            has_shapes = os.path.exists(os.path.join(target_folder, 'shapes.json'))
            has_frames = os.path.exists(os.path.join(target_folder, 'frames.json'))
            has_labels = os.path.exists(os.path.join(target_folder, 'labels.json'))
            if has_shapes and has_frames and has_labels:
                print('-- skipping', root)
                continue
            
            print('-- exporting', root)
            os.makedirs(target_folder, exist_ok=True)
            logging.basicConfig(filename=os.path.join(target_folder, 'logs.txt'), level=logging.DEBUG, force=True)
            logging.captureWarnings(True)

            try:
                export(root, target_folder)
            except:
                print('error on', root)
                logging.exception(traceback.format_exc())

    elif args.render:
        parser = argparse.ArgumentParser()
        parser.add_argument("--render", required=True, action='store_true')
        parser.add_argument('format', type=str)
        parser.add_argument('input_folder', type=str)
        parser.add_argument('--timeline', required=False, type=str)
        parser.add_argument('output_folder', type=str)
        parser.add_argument('--width', required=False, type=float)
        parser.add_argument('--height', required=False, type=float)
        parser.add_argument('--x', required=False, type=float)
        parser.add_argument('--y', required=False, type=float)
        parser.add_argument('--scale', required=False, type=float)

        args = parser.parse_args()

        os.makedirs(args.output_folder, exist_ok=True)
        with open(os.path.join(args.input_folder, 'shapes.json'), 'r') as inp:
            shapes = json.load(inp)
        with open(os.path.join(args.input_folder, 'frames.json'), 'r') as inp:
            frames = json.load(inp)
        with open(os.path.join(args.input_folder, 'labels.json'), 'r') as inp:
            labels = json.load(inp)
        
        timeline = []
        for frame_id, label in labels.items():
            if 'timeline' not in label:
                continue
            if args.timeline:
                if label['timeline'] != args.timeline:
                    continue
                timeline.append((frame_id, label['frame']))
            else:
                if label['timeline'].startswith('file://'):
                    timeline.append((frame_id, label['frame']))
        
        timeline = sorted(timeline, key=lambda x: x[1])
        for i, frame_id in enumerate(timeline):
            frame_id = frame_id[0]
            print('=== rendering frame', frame_id, '===')
            frame = get_table_frame(shapes, frames, frame_id)
            with SvgRenderer() as renderer:
                frame.render()
            x = args.x or 0
            y = args.y or 0
            width = args.width or labels[frame_id].get('width', 550)
            height = args.height or labels[frame_id].get('height', 400)
            scale = args.scale or 1
            svg = renderer.compile(width, height, x, y, scale)

            with open(os.path.join(args.output_folder, '%04d.svg' % i), 'w') as outp:
                svg.write(outp, encoding='unicode')


        


        


