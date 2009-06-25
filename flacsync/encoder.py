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
COVERS = ['cover.jpg', 'folder.jpg', 'frong.jpg', 'album.jpg']
THUMBSIZE = 250,250


#############################################################################
class Encoder(object):
   # dimensions of cover thumbnails in pixels
   def __init__( self, src, ext, base_dir, dest_dir, **kwargs ):
      super( Encoder, self).__init__()
      self.src = src
      self.dst = util.fname(src,base_dir,dest_dir,ext)
      self.cover = self._get_cover()

   def _is_newer( self ):
      return (not os.path.exists(self.dst) or
            os.path.getmtime(self.src) > os.path.getmtime(self.dst))

   def _is_cover_newer( self ):
      return (os.path.getmtime(self.cover) > os.path.getmtime(self.dst))

   def _get_cover( self ):
      root,files = os.walk( os.path.dirname(self.src)).next()[::2]
      match = (f for f in files for c in COVERS if f==c).next()
      if match: # cover image found
         return os.path.join(root,match)
      else:
         return None

   def _pre_encode( self ):
      try:
         os.makedirs( os.path.dirname(self.dst) )
      except OSError: pass  # ignore if dir already exists

   def _rg_to_soundcheck( self, replay_gain ):
      """Return the soundcheck hex string converted from a replay_gain float
      value."""
      if replay_gain is None:
         return None
      rg_f = float(replay_gain.split()[0])
      sc = 1000 * pow(10,(-rg_f/10.0))
      return ' '.join(["%08X" % (sc,)]*10)

   def _cover_thumbnail(self):
      if not self.cover: return None
      im = Image.open(self.cover)
      im.thumbnail(THUMBSIZE)
      ofile = tempfile.mkstemp()[1]
      im.save(ofile, "JPEG")
      return ofile

   @staticmethod
   def _check_err( err, msg):
      if err:
         print msg,
         print err
         return False
      else:
         return True


#############################################################################
class AacEncoder( Encoder ):
   def __init__( self, q, **kwargs  ):
      super( AacEncoder, self).__init__( ext='.m4a', **kwargs)
      self.q = q

   def encode( self, force=False ):
      if not force and not self._is_newer():
         return False
      self._pre_encode()
      # encode to AAC
      err = sp.call( 'flac -d "%s" -c -s | neroAacEnc -q %s -if - -of "%s"' %
            (self.src, self.q, self.dst), shell=True, stderr=NULL)
      return self._check_err( err, "AAC encoder failed:" )

   def tag( self, artist=None, title=None, album=None, year=None, track=None,
               genre=None, replay_gain=None ):
      # aac tags, matches order of FLAC_TAGS
      aac_fields = {
            'artist':artist, 'title':title, 'album':album, 'year':year,
            'track':track, 'genre':genre,
            }
      # tag AAC file
      sc_val = self._rg_to_soundcheck(replay_gain)
      cmd = ['-meta-user:iTunNORM="%s"' % (sc_val,)]
      cmd.extend('-meta:%s="%s"'%(x,y) for x,y in aac_fields.items())
      err = sp.call( 'neroAacTag "%s" %s' % (self.dst,' '.join(cmd)),
            shell=True, stderr=NULL)
      return self._check_err( err, "AAC tag failed:" )

   def set_cover( self, force ):
      if not force and not self._is_cover_newer():
         return
      tmp_cover = self._cover_thumbnail()
      err = sp.call( 'neroAacTag "%s" -remove-cover:all -add-cover:front:"%s"' %
               (self.dst, tmp_cover,), shell=True, stderr=NULL)
      # delete temp file
      os.remove( tmp_cover )
      return self._check_err( err, "AAC add-cover failed:" )


