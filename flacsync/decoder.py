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
   Define interface to decoder for processing FLAC files.
"""

import subprocess as sp

__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'


#############################################################################
class FlacDecoder( object ):

   FLAC_TAGS = {
      'artist':'artist',
      'title':'title',
      'album':'album',
      'year':'date',
      'track':'tracknumber',
      'genre':'genre',
      'rg_track_gain':'replaygain_track_gain',
      'rg_track_peak':'replaygain_track_peak',
      'rg_album_gain':'replaygain_album_gain',
      'rg_album_peak':'replaygain_album_peak',
      }

   def __init__(self, name):
      self.name = name

   @property
   def tags(self):
      return dict((k,self._read_tag(v)) for k,v in self.FLAC_TAGS.items())

   def _read_tag(self,field):
      val = sp.Popen( 'metaflac --show-tag=%s "%s"' % (field,self.name),
            shell=True, stdout=sp.PIPE).communicate()[0]
      return val.split('=')[1].strip() if val else None

