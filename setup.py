#!/usr/bin/env python

#  Copyright 2009, Patrick C. McGinty

#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>

"""
Distools setup file for the flacsync application.
"""

import sys
import os
from distutils.core import setup

sys.path.insert(0,'flacsync')
import flacsync as pkg
name = pkg.__name__

def _read( *path_name ):
   return open( os.path.join(os.path.dirname(__file__), *path_name)).read()

long_doc = pkg.__doc__ + '\n' + _read('INSTALL.txt')

setup(
   name=name,
   version=pkg.__version__,
   description="""\
      Recursively mirror a directory of FLAC files to AAC.
      """,
   long_description=long_doc,
   author=pkg.__author__,
   author_email=pkg.__email__,
   url='http://%s.googlecode.com' % (name,),
   download_url=(
      'http://%s.googlecode.com/files/%s-%s.tar.gz' %
         (name,name,pkg.__version__,)),
   packages=[name],
   scripts=['scripts/%s'%(name,)],
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

