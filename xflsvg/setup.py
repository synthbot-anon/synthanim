from setuptools import setup

setup(
    name='xflsvg',
    version='0.1.2',
    description='''A tool for working with XFL/XflSvg data.''',
    long_description_content_type="text/x-rst",
    long_description='''
This library is part of the Pony Preservation Project. It is designed to
support the development of 2D animation AI. It has three main functions:

    - Support to creation for SVG spritemaps for XFL files. Since there's no
      publicly-known way to render Adobe's Edge format, this library assumes
      that Adobe Animate is required to render shape objects. The XflSvgRecorder
      class simplifies the process by exporting (1) a simplified XFL file
      containing a single symbol, whose frames contain all of the shapes in the
      parent XFL files, and (2) a JSON object mapping parent XFL shapes to their
      location in the simplified XFL file.
    - Convert XFL files and exported SVG shapes (xflsvg files) into a tabular
      data format. The tabular data will eventually contain ALL data necessary
      to fully recreate the original animation, and the data will be
      hierarchically structured to match the original XFL file. This is done
      using the XflSvgRecorder class's to_json() and to_xfl() methods.
    - Render tabular animation data. The tabular data may be exported from
      existing xflsvg files, or they may be programmatically generated. This
      is done using the XflSvgRenderer class.

This project is currently in an early stage. The xflsvg format will change
over time as we identify exactly what XFL data is necessary to recreate
animations, as will the rendering code.

If you're using pip to install xflsvg, you'll need to install cairocffi
and cairosvg to use XflSvgRenderer. If you're using conda to install xflsvg,
both will be automatically installed. Note that pip doesn't seem to install
cairocffi properly.
''',
    url='https://github.com/synthbot-anon/synthanim',
    author='Synthbot',
    author_email='synthbot.anon@gmail.com',
    license='''Copyright 2021 Synthbot

You may only use this project to process publicly-available data. You may not
use this project to process private or proprietary data. This applies even if
you are a student or an academic researcher. You may modify any part of this
project arbitrarily EXCEPT:

    - This license.
    - Any file explicitly marked as unmodifiable under the license.
    - Any line of code explicitly marked with the comment "DO NOT MODIFY".

If you use this project to process non-public data, you must make the data
publicly available within 30 days of execution, and you must inform
synthbot.anon@gmail.com with details on how to download the data.

For exceptions to this license, please contact synthbot.anon@gmail.com.
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
