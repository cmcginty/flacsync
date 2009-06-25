"""
   Define shared utility functions.
"""

import os

__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'


def fname( file_, base=None, new_base=None, new_ext=None ):
   """Convert a file name to a new base + extensions."""
   if base and new_base:
      file_ = file_.replace(base, new_base, 1)
   if new_ext:
      file_ = os.path.splitext(file_)[0] + new_ext
   return file_


