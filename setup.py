#!/usr/bin/env python

#  Copyright (c) 2011, Patrick C. McGinty
#
#  This program is free software: you can redistribute it and/or modify it
#  under the terms of the Simplified BSD License.
#
#  See LICENSE text for more details.
"""
Distools setup file for the flacsync application.
"""

import os
from setuptools import setup
from textwrap import dedent

import flacsync as pkg
NAME     = pkg.__name__
VERSION  = pkg.__version__
AUTHOR   = pkg.__author__
EMAIL    = pkg.__email__

setup(
   name=NAME,
   version=VERSION,
   description= 'Recursively mirror a directory tree of FLAC '
                'audio files to AAC or OGG.',
   long_description=dedent(pkg.__doc__),
   author=AUTHOR,
   author_email=EMAIL,
   url='http://packages.python.org/%s/' % NAME,
   download_url=(
      'https://github.com/cmcginty/%s/raw/master/dist/%s-%s.tar.gz' %
         (NAME,NAME,VERSION,)),
   packages=[NAME],
   entry_points = {
      'console_scripts': ['flacsync = flacsync:main',],
   },
   keywords = 'flac aac conversion transcode compressedaudio ipod soundcheck '
              'replaygain albumart metaflac tags neroaacenc ogg music',
   classifiers=[
      'Development Status :: 5 - Production/Stable',
      'Environment :: Console',
      'Intended Audience :: End Users/Desktop',
      'License :: OSI Approved :: GNU General Public License (GPL)',
      'Operating System :: OS Independent',
      'Operating System :: POSIX :: Linux',
      'Programming Language :: Python',
      'Topic :: Multimedia :: Sound/Audio :: Conversion',
   ]
)

