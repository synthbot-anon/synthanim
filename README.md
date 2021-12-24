
# SynthAnim
SynthAnim was developed for the Pony Preservation Project. SynthAnim is a collection
of tools for puppet-based animation data collection. It consists of the following projects:
- xflsvg, which parses and renders XFL files. xflsvg borrows heavily from [PluieElectrique](https://github.com/PluieElectrique)
for XFL rendering.
- autoanimate, which automates Adobe Animate for complex batch processing. autoanimate requires a modded version of Adobe Animate, which is not provided with this repository.
- animate-scripts, which includes JSFL scripts used by autoanimate.

## xflsvg
Example usage:
    
    xfl = XflReader('/path/to/file.xfl')
    timeline = xfl.get_timeline('Scene 1')
    for i, frame in enumerate(timeline):
        with SvgRenderer() as renderer:
            frame.render()
        svg = renderer.compile(xfl.width, xfl.height)
        with open(f'frame{i}.svg', 'w') as outfile:
            svg.write(outfile, encoding='unicode')

The XFLReader class provide is a visitor interface for rendering. Renderers
should subclass the XflRenderer class and implement the relevant methods. A
complete renderer should implement EITHER:

    render_shape - Render an SVG shape
    push_transform, pop_transform - Start and end position and color transformations
    push_mask, pop_mask - Start and end mask definitions
    push_masked_render, pop_masked_render - Start/end renders with the last mask

OR

    on_frame_rendered - Should handle Frame, ShapeFrame, and MaskedFrame

The first set of methods are better for actual rendering since they convert the
XFL file into a sequence of instructions. The second method is better for
transforming the data into a new tree-structured format.

## autoanimate
~~~
setup
  - This will walk you through setting up Adobe Animate and the animation
    data.
convert
  - This will ask for an FLA file and a destination. It will convert the
    FLA to XFL and it will convert all shape objects to SVG. This is the
    command for converting FLA into a usable format.
dump-samples
  - This will ask for an animation file and a destination. It will dump a
    sample image of every symbol in the animation file. This is the command
    for turning FLA into files we can label easily.
dump-xfl
  - This will ask for an FLA file and a destination. It will convert the
    FLA to XFL.
dump-texture-atlas
  - This will ask for an Animation Assets directory, a symbol sample
    image (which you can get from dump-samples), and a destination folder.
    It will dump the animation data for that symbol in texture atlas format.
check-data
  - This will ask for a directory and a value, and it will check the
    directory for any occurences of that value. This is intended to check
    for personal data that might have been written to a file. It will check
    both binary and text files, ignoring case and spaces, partial and
    complete matches. It will output the top matches, along with any files
    it's unable to check for whatever reason.

You can add --batch to all of these. When you add, it will ask for folders
instead of files. For example:
  dump-xfl --batch
  - This will convert a folder of FLA files, and it will search all sub-
  directories.
~~~

# License
Check the LICENSE file. The xflsvg/domshape/ package is covered by the license
from PluieElectrique. It was taken from https://github.com/PluieElectrique/xfl2svg. Everything else is covered by the license from Synthbot.

Make sure to follow this part:

    The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

That applies to both the code and any compiled versions of the code.
