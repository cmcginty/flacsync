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
   Define interface to encoders available for processing FLAC files.
"""

import os
import subprocess as sp
import tempfile
import Image

from . import util

__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'


NULL = file('/dev/null')
# list of album covers, in preferential order
COVERS = ['cover.jpg', 'folder.jpg', 'front.jpg', 'album.jpg']
THUMBSIZE = 250,250


#############################################################################
class _Encoder(object):
   # dimensions of cover thumbnails in pixels
   def __init__( self, src, ext, base_dir, dest_dir ):
      super( _Encoder, self).__init__()
      self.src = src
      self.dst = util.fname(src, base_dir, dest_dir, ext)
      self.cover = self._get_cover() or None

   def skip_encode( self ):
      "Return 'True' if entire enocde step can be skipped"
      encode = util.newer(self.src, self.dst)
      cover  = self.cover and util.newer(self.cover, self.dst)
      return not (encode or cover)

   def _get_cover( self ):
      root,_,files = os.walk( os.path.dirname(self.src)).next()
      try:
         match = (f for f in files for c in COVERS if f==c).next()
         return os.path.join(root,match)
      except StopIteration:
         pass

   def _pre_encode( self ):
      try:
         os.makedirs( os.path.dirname(self.dst) )
      except OSError: pass  # ignore if dir already exists

   def _rg_to_soundcheck( self, replay_gain ):
      """Return the soundcheck hex string converted from a replay_gain float
      value."""
      if replay_gain is None:
         return None
      rg_f = float( replay_gain.split()[0])
      sc = 1000 * pow(10,(-rg_f/10.0))
      return ' '.join(["%08X" % (sc,)]*10)

   def _cover_thumbnail( self ):
      assert self.cover    # cover must be valid
      im = Image.open( self.cover)
      im.thumbnail( THUMBSIZE)
      ofile = tempfile.NamedTemporaryFile()
      im.save( ofile.name, "JPEG")
      return ofile

   @staticmethod
   def _check_err( err, msg ):
      if err:
         print msg, err
         return False
      else:
         return True


#############################################################################
class AacEncoder( _Encoder ):
   def __init__( self, aac_q, **kwargs  ):
      super( AacEncoder, self).__init__( ext='.m4a', **kwargs)
      assert type(aac_q) == str, "q value is: %s" % (aac_q,)
      self.q = aac_q

   def encode( self, force=False ):
      """Return True if (re)encoding occured and no errors, False otherwise"""
      if force or util.newer( self.src, self.dst):
         self._pre_encode()
         # encode to AAC
         err = sp.call( 'flac -d "%s" -c -s | neroAacEnc -q %s -if - -of "%s"' %
               (self.src, self.q, self.dst), shell=True, stderr=NULL)
         if err == -2:  # keyboard interrupt
            os.remove(self.dst) # clean-up partial file
            raise KeyboardInterrupt
         return self._check_err( err, "AAC encoder failed:" )
      else:
         return False

   def tag( self, tags ):
      # aac tags, matches order of FLAC_TAGS
      aac_fields = {
         'artist':tags['artist'],         'title':tags['title'],
         'album':tags['album'],           'year':tags['year'],
         'track':tags['track'],           'genre':tags['genre'],
         'comment':tags['comment'],       'disc':tags['disc'],
         'totaltracks':tags['totaltracks'],
      }
      aac_fields = dict((k,v) for k,v in aac_fields.items() if v)
      user_fields = {
         'writer':tags['composer'],
         'replaygain_track_gain':tags['rg_track_gain'],
         'replaygain_track_peak':tags['rg_track_peak'],
         'replaygain_album_gain':tags['rg_album_gain'],
         'replaygain_album_peak':tags['rg_album_peak'],
      }
      user_fields = dict((k,v) for k,v in user_fields.items() if v)
      # tag AAC file
      sc_val = self._rg_to_soundcheck(tags['rg_track_gain'])
      cmd = ['-meta-user:iTunNORM="%s"' % (sc_val,)]
      cmd.extend('-meta:%s="%s"'%(x,y) for x,y in aac_fields.items())
      cmd.extend('-meta-user:%s="%s"'%(x,y) for x,y in user_fields.items())
      err = sp.call( 'neroAacTag "%s" %s' % (self.dst,' '.join(cmd)),
            shell=True, stderr=NULL)
      return self._check_err( err, "AAC tag failed:" )

   def set_cover( self, force=False ):
      if self.cover and (force or util.newer(self.cover,self.dst)):
         tmp_cover = self._cover_thumbnail()
         err = sp.call( 'neroAacTag "%s" -remove-cover:all -add-cover:front:"%s"' %
                  (self.dst, tmp_cover.name,), shell=True, stderr=NULL)
         return self._check_err( err, "AAC add-cover failed:" )


#############################################################################
import base64
import struct
class OggEncoder( _Encoder ):
   def __init__( self, ogg_q, **kwargs  ):
      super( OggEncoder, self).__init__( ext='.ogg', **kwargs)
      assert type(ogg_q) == str, "q value is: %s" % (ogg_q,)
      self.q = ogg_q

   def encode( self, force=False ):
      if force or util.newer( self.src, self.dst):
         self._pre_encode()
         # encode to OGG
         err = sp.call( 'oggenc -q %s -o "%s" "%s"' %
               (self.q, self.dst, self.src), shell=True, stderr=NULL)
         if err == -2:  # keyboard interrupt
            os.remove(self.dst) # clean-up partial file
            raise KeyboardInterrupt
         return self._check_err( err, "OGG encoder failed:" )
      else:
         return False

   # no-op, since tags are automatically updated during encoding
   def tag( self, tags):
      return True

   # see http://flac.sourceforge.net/format.html#metadata_block_picture
   # for more details regarding embedded vorbis pictures
   def set_cover( self, force=False ):
      # define METADATA_BLOCK_PICTURE binary structure
      #     int:     Picture type, 0-20 (3=cover front)
      #     int:     Length of MIME type string in bytes
      #     string:  MIME type string
      #     int:     length of description in bytes
      #     string:  picture description
      #     int:     picture width, pixels
      #     int:     picture height, pixels
      #     int:     color depth
      #     int:     number of colors in index, 0 for non-indexeed pic
      #     int:     length of picture data in bytes
      #     string:  binary picture data
      pic_block_t = "=2I %ds I %ds 5I %ds"
      mime = 'image/jpeg'
      description = "album cover"
      if self.cover and (force or util.newer(self.cover,self.dst)):
         tmp_cover = self._cover_thumbnail()
         bin_cover = tmp_cover.read()
         meta_block = struct.pack(
               pic_block_t % (len(mime), len(description), len(bin_cover)),
               3,
               len(mime), mime,
               len(description), description,
               THUMBSIZE[0], THUMBSIZE[1], 24, 0,
               len(bin_cover),
               bin_cover)
         meta_block = base64.b64encode(meta_block)
         err = sp.call( 'vorbiscomment -a -t "META_BLOCK_PICTURE=%s" "%s"' %
                 (meta_block, self.dst), shell=True, stderr=NULL)
         return self._check_err( err, "OGG add-cover failed:" )


