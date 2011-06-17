#  Copyright (c) 2011, Patrick C. McGinty
#
#  This program is free software: you can redistribute it and/or modify it
#  under the terms of the Simplified BSD License.
#
#  See LICENSE text for more details.
"""
   flacsync.encoder
   ~~~~~~~~~~~~~~~~

   Define interface to encoders available for processing FLAC files.
"""

import os
import subprocess as sp
import tempfile
import Image

from . import util

__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'


#: File handle to ``/dev/null``
NULL = file('/dev/null')

#: List of album covers, in preferential order.
COVERS = ['cover.jpg', 'folder.jpg', 'front.jpg', 'album.jpg']
#: Resolution of re-sized album covers.
THUMBSIZE = 250,250


#############################################################################
class _Encoder(object):
   """
   Base encoder class provides common methods. This should not be used
   directly.
   """
   # dimensions of cover thumbnails in pixels
   def __init__( self, src, ext, base_dir, dest_dir ):
      super( _Encoder, self).__init__()
      self.src = src
      self.dst = util.fname(src, base_dir, dest_dir, ext)
      self.cover = self._get_cover() or None

   def skip_encode( self ):
      """Return 'True' if entire encode step can be skipped."""
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
      """
      Return the soundcheck hex string converted from a replay_gain float
      value.
      """
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
   """
   FLAC to AAC encoder.
   """
   def __init__( self, aac_q, **kwargs  ):
      """
      :param aac_q:  AAC encoder quality value [0 - 1]
      :type  aac_q:  str
      """
      super( AacEncoder, self).__init__( ext='.m4a', **kwargs)
      assert type(aac_q) == str, "q value is: %s" % (aac_q,)
      self.q = aac_q

   def encode( self, force=False ):
      """
      Performs audio encoding process.

      :param force:  When :data:`True`, encoding will be done, even if
                     destination file exists.
      :type  force:  boolean

      :return: :data:`True` if (re)encoding occurred and no errors,
               :data:`False` otherwise
      """
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
      """
      Copies FLAC tags into destination AAC file.

      :param tags: Source tag values from FLAC file.
      :type  tags: dict
      """
      # AAC tags, matches order of FLAC_TAGS
      aac_fields = {
         'artist' :tags['artist'],        'title':tags['title'],
         'album'  :tags['album'],         'year' :tags['year'],
         'track'  :tags['track'],         'genre':tags['genre'],
         'comment':tags['comment'],       'disc' :tags['disc'],
         'composer':tags['composer'],
         'totaltracks':tags['totaltracks'],
      }
      aac_fields = dict((k,v) for k,v in aac_fields.items() if v)
      # itunes fields:
      #     'album artist' contentgroup description episode episodename
      #     itunescompilation itunespodcast network season show sortalbum
      #     sortartist sortband sortshow sorttitle sortwriter writer
      user_fields = {
         'writer'          :tags['composer'],
         'album artist'    :tags['album_artist'],
         'albumartist'     :tags['album_artist'],
         'compilation'     :tags['compilation'],
         'itunescompilation':tags['compilation'],
         'replaygain_track_gain':tags['rg_track_gain'],
         'replaygain_track_peak':tags['rg_track_peak'],
         'replaygain_album_gain':tags['rg_album_gain'],
         'replaygain_album_peak':tags['rg_album_peak'],
         'iTunNORM':self._rg_to_soundcheck(tags['rg_track_gain']),
      }
      user_fields = dict((k,v) for k,v in user_fields.items() if v)
      # tag AAC file
      cmd = ['-meta:"%s"="%s"'%(x,y) for x,y in aac_fields.items()]
      cmd += ['-meta-user:"%s"="%s"'%(x,y) for x,y in user_fields.items()]
      err = sp.call( 'neroAacTag "%s" %s' % (self.dst,' '.join(cmd)),
            shell=True, stderr=NULL)
      return self._check_err( err, "AAC tag failed:" )

   def set_cover( self, force=False ):
      """
      Attach album cover image to AAC file.

      :param force:  When :data:`True`, encoding will be done, even if
                     destination file exists.
      :type  force:  boolean
      """
      if self.cover and (force or util.newer(self.cover,self.dst)):
         tmp_cover = self._cover_thumbnail()
         err = sp.call( 'neroAacTag "%s" -remove-cover:all -add-cover:front:"%s"' %
                  (self.dst, tmp_cover.name,), shell=True, stderr=NULL)
         return self._check_err( err, "AAC add-cover failed:" )


import base64
import struct
class OggEncoder( _Encoder ):
   """
   FLAC to OGG encoder.
   """
   def __init__( self, ogg_q, **kwargs  ):
      """
      :param ogg_q:  OGG encoder quality value [1 - 10]
      :type  ogg_q:  str
      """
      super( OggEncoder, self).__init__( ext='.ogg', **kwargs)
      assert type(ogg_q) == str, "q value is: %s" % (ogg_q,)
      self.q = ogg_q

   def encode( self, force=False ):
      """
      Performs audio encoding process.

      :param force:  When :data:`True`, encoding will be done, even if
                     destination file exists.
      :type  force:  boolean

      :return: :data:`True` if (re)encoding occurred and no errors,
               :data:`False` otherwise
      """
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

   def tag( self, tags):
      """
      No-op, since tags are automatically updated during encoding.

      :return: :data:`True`
      """
      return True

   def set_cover( self, force=False ):
      """
      Attach album cover image to OGG file.

      This function is experimental, since not many players support embedded
      images in OGG files.

      .. seealso::

         Refer to the `METADATA_BLOCK_PICTURE
         <http://flac.sourceforge.net/format.html#metadata_block_picture>`_
         specification for more details regarding embedded vorbis images.

      :param force:  When :data:`True`, encoding will be done, even if
                     destination file exists.
      :type  force:  boolean
      """
      # define METADATA_BLOCK_PICTURE binary structure
      #     int:     Picture type, 0-20 (3=cover front)
      #     int:     Length of MIME type string in bytes
      #     string:  MIME type string
      #     int:     length of description in bytes
      #     string:  picture description
      #     int:     picture width, pixels
      #     int:     picture height, pixels
      #     int:     color depth
      #     int:     number of colors in index, 0 for non-indexed pic
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


from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import APIC
class Mp3Encoder( _Encoder ):
   def __init__( self, mp3_q, **kwargs  ):
      super( Mp3Encoder, self).__init__( ext='.mp3', **kwargs)
      assert type(mp3_q) == str, "q value is: %s" % (mp3_q,)
      self.q = mp3_q

   def encode( self, force=False ):
      if force or util.newer( self.src, self.dst):
         self._pre_encode()
         # encode to MP3
         #   --add-id3v2 forces creation of an empty tag
         err = sp.call( 'flac -d "%s" -c -s | lame --add-id3v2 -V %s - "%s"' %
               (self.src, self.q, self.dst), shell=True, stderr=NULL)
         if err == -2:  # keyboard interrupt
            os.remove(self.dst) # clean-up partial file
            raise KeyboardInterrupt
         return self._check_err( err, "MP3 encoder failed:" )
      else:
         return False

   # uses mutagen tagging library
   def tag( self, tags):
      mp3_fields = {
         'artist':tags['artist'],         'title':tags['title'],
         'album':tags['album'],           'date':tags['year'],
         'tracknumber':tags['track'],     'genre':tags['genre'],
         'discnumber':tags['disc'],       'composer':tags['composer'],
         'replaygain_track_gain':tags['rg_track_gain'],
         'replaygain_track_peak':tags['rg_track_peak'],
         'replaygain_album_gain':tags['rg_album_gain'],
         'replaygain_album_peak':tags['rg_album_peak'],
      }
      mp3_fields = dict((k,v) for k,v in mp3_fields.items() if v)
      # tag MP3 file
      audio = EasyID3(self.dst)
      for x,y in mp3_fields.items():
        audio[x] = y
      err = audio.save()
      return self._check_err( err, "MP3 tag failed:" )

   # See section 4.14 at http://www.id3.org/id3v2.4.0-frames
   # for more details regarding embedded ID3 pictures
   def set_cover( self, force=False ):
     if self.cover and (force or util.newer(self.cover,self.dst)):
         tmp_cover = self._cover_thumbnail()
         imagedata = open(tmp_cover.name, 'rb').read()
         audio = MP3(self.dst)
         audio.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Front Cover", data=imagedata))
         err = audio.save()
     return self._check_err( err, "MP3 add-cover failed:" )

