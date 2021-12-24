from setuptools import setup

setup(
    name='xflsvg',
    version='0.1.2',
    description='''A tool for working with XFL/XflSvg data.''',
    long_description_content_type="text/x-rst",
    long_description='''
This library is part of the Pony Preservation Project. It is designed to
support the development of 2D animation AI. It has three main functions:

    - Support to creation for SVG spritemaps for XFL files.
    - Convert XFL files into a tabular data format. The tabular data will
      eventually contain ALL data necessary to fully recreate the original
      animation, and the data will be hierarchically structured to match the
      original XFL file.
    - Render tabular animation data. The tabular data may be exported from
      existing XFL files, or they may be programmatically generated.

This project is currently in an early stage. The format will change over
time as we identify exactly what XFL data is necessary to recreate
animations, as will the rendering code.

''',
    url='https://github.com/synthbot-anon/synthanim',
    author='Synthbot',
    author_email='synthbot.anon@gmail.com',
    license='''The domshape/ package is covered by the license from PluieElectrique. It was taken from https://github.com/PluieElectrique/xfl2svg.
Everything else is covered by the license from Synthbot.

===
MIT License

Copyright (c) 2021 Synthbot, /mlp/ Pony Preservation Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

===
MIT License

Copyright (c) 2021 PluieElectrique

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

''',
    packages=['xflsvg', 'xflsvg.domshape'],
    package_dir={'': 'src'},
    install_requires=['bs4', 'html5lib', 'lxml', 'pandas', 'fastparquet'],
    include_package_data=True,

    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
)
