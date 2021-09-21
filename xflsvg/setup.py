from setuptools import setup

setup(
    name='xflsvg',
    version='0.1.0',    
    description='''A tool for working with XflSvg files and tabular animation data.

This library is part of the Pony Preservation Project. It is designed to support
the development of 2D animation AI. It will have three main functions:
  - Support to creation for SVG spritemaps for XFL files. Since there's no
    publicly-known way to render Adobe's Edge format, this library assumes
    that Adobe Animate is required to render shape objects. The RecordingXflSvg
    class simplifies the process by exporting (1) a simplified XFL file
    containing a single symbol, whose frames contain all of the shapes in the
    parent XFL files, and (2) a JSON object mapping parent XFL shapes to their
    location in the simplified XFL file.
  - Convert XFL files and exported SVG shapes (xflsvg files) into a tabular data
    format. The tabular data will eventually contain ALL data necessary to
    fully recreate the original animation, and the data will be hierarchically
    structured to match the original XFL file. This is done using the
    RecordingXflSvg class's to_json() and to_xfl() methods.
  - Render tabular animation data. The tabular data may be exported from
    existing xflsvg files, or they may be programmatically generated. This
    is done using the RenderingXflSvg class.

This project is currently in an early stage. The xflsvg format will change over
time as we identify exactly what XFL data is necessary to recreate animations,
as will the rendering code.

You need to install cairocffi and cairosvg to render things.
''',
    url='https://github.com/synthbot-anon/synthanim',
    author='Synthbot',
    author_email='synthbot.anon@gmail.com',
    license='''Copyright 2021 Synthbot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.''',
    packages=['xflsvg'],
    install_requires=['bs4', 'html5lib', 'lxml', 'pandas', 'fastparquet'],
    include_package_data=True,

    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',  
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
)