#  Copyright (c) 2011, Patrick C. McGinty
#
#  This program is free software: you can redistribute it and/or modify it
#  under the terms of the Simplified BSD License.
#
#  See LICENSE text for more details.
"""
   flacsync.decoder
   ~~~~~~~~~~~~~~~~

   Define interfaces for processing compressed audio files.
"""

import subprocess as sp

__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'


#############################################################################
class FlacDecoder( object ):
   """
   FLAC file deocder class. Provides interface for tag access.
   """
   #: Dictionary mapping from flacsync name -> FLAC tag name
   FLAC_TAGS = {
      'album'           :'album',
      'album_artist'    :'albumartist',
      'artist'          :'artist',
      'comment'         :'comment',
      'compilation'     :'compilation',
      'composer'        :'composer',
      'copyright'       :'copyright',
      'description'     :'description',
      'disc'            :'discnumber',
      'enc_by'          :'encoded-by',
      'genre'           :'genre',
      'license'         :'license',
      'performer'       :'performer',
      'rg_album_gain'   :'replaygain_album_gain',
      'rg_album_peak'   :'replaygain_album_peak',
      'rg_track_gain'   :'replaygain_track_gain',
      'rg_track_peak'   :'replaygain_track_peak',
      'title'           :'title',
      'totaltracks'     :'tracktotal',
      'track'           :'tracknumber',
      'year'            :'date',
      }

   def __init__(self, name):
      self.name = name

   @property
   def tags(self):
      """
      Dictionary of FLAC tag. Valid key names are:

      ===================  =====================
      Key                  Description
      ===================  =====================
      ``album``            Album title
      ``album_artist``     Album artist name
      ``artist``           Artist name
      ``comment``
      ``compilation``
      ``composer``         Composer name
      ``copyright``
      ``description``
      ``disc``             Disc number
      ``enc_by``           Encoder string
      ``genre``            Genre string
      ``license``
      ``performer``        Performer name
      ``rg_album_gain``    Album replay gain
      ``rg_album_peak``    Album peak
      ``rg_track_gain``    Track replay gain
      ``rg_track_peak``    Track peak
      ``title``            Track title
      ``totaltracks``      Total album tracks
      ``track``            Track number
      ``year``             Year (20XX)
      ===================  =====================
      """
      return dict((k,self._read_tag(v)) for k,v in self.FLAC_TAGS.items())

   def _read_tag(self,field):
      lines = sp.Popen( 'metaflac --show-tag="%s" "%s"' % (field,self.name),
            shell=True, stdout=sp.PIPE).communicate()[0]
      tags = []
      for l in lines.splitlines():
         key_val = l.split('=',1)
         if len(key_val) == 2:
            tags.append(key_val[1].strip())
      return ' - '.join(tags) if tags else None

