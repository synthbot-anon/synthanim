from setuptools import setup

setup(
    name='autoanimate',
    version='0.1.0',
    description='''A tool for automating Adobe Animate.''',
    long_description_content_type="text/x-rst",
    long_description='''
This library is part of the Pony Preservation Project. It is designed to
support the development of 2D animation AI. Its function is to convert FLA
files into formats more suitable for machine learning tasks. Currently, it:

    - Converts FLA files to XFL
    - Converts EdgeFormat data into SVG data (written to spritemaps/)
    - Converts XFL structure to a tabular format (written to tables/)

To run this project:

    - Run python -m synthrunner
    - In the prompt, run "setup" (without quotes). You only need to do this
      once. This will walk you through the process for setting up Adobe
      Animate and downloading the relevant data.
    - Dump the data for a single FLA file using the dump-shapes command. This
      will walk you through the process for selecting the input file and
      output folder.
    - Dump batch data for many FLA files using "dump-shapes --batch".

This project is currently in an early stage. The export format will change
over time as we identify exactly what XFL data is necessary to recreate
animations.
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
    packages=['autoanimate'],
    package_dir={'': 'src'},
    install_requires=['xflsvg','keyboard', 'pywin32==225', 'watchdog'],
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
