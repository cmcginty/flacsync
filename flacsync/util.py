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
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
   flacsync.util
   ~~~~~~~~~~~~~

   Define shared utility functions.
"""

import os

__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'


def fname( file_, base=None, new_base=None, new_ext=None ):
   """
   Convert a file name to a new base + extensions.

   :param file_: Source file name
   :type  file_: str

   :param base: Base string, found in the :data:`file_`
   :type  base: str

   :param new_base: Destination base string, to replace :data:`base`
   :type  new_base: str

   :param new_ext: Destination extention (.aac), to replace :data:`file_`
                   extenstion
   :type  new_ext: str
   """
   if base and new_base:
      file_ = file_.replace(base, new_base, 1)
   if new_ext:
      file_ = os.path.splitext(file_)[0] + new_ext
   return file_

def newer( f1, f2 ):
   """
   :returns: :data:`True` if file :data:`f1` is newer than file :data:`f2`.

   .. warning ::

      Assumes File :data:`f1` exists.
   """
   assert os.path.exists(f1), "File not found: '%s'" %(f1,)
   return (not os.path.exists(f2) or
         os.path.getmtime(f1) > os.path.getmtime(f2))

