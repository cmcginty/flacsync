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
      'replay_gain':'REPLAYGAIN_TRACK_GAIN',
      }

   def __init__(self, name):
      self.name = name

   @property
   def tags(self):
      return dict((k,self._read_tag(v)) for k,v in self.FLAC_TAGS.items())

   def _read_tag(self,field):
      val = sp.Popen( 'metaflac --show-tag=%s "%s"' % (field,self.name),
            shell=True, stdout=sp.PIPE).communicate()[0]
      return val.split('=')[1].strip()

