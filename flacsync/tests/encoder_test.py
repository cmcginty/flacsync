"""
   Test module for Encoder.py
"""

from __future__ import absolute_import
from nose.tools import *
from mock import *

from .. import encoder

__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'


class TestCovers():

   WALK_VALUE = [('root_dir', 'dummy',
                        ('file1.flac','file2.flac','cover.jpg'))]

   @patch( 'os.walk' )
   def _new_encoder( self, mock_walk, walk_value=WALK_VALUE):
      mock_walk.return_value = iter(walk_value)
      E = encoder._Encoder( src='./sample.flac', ext='ext',
            base_dir='base', dest_dir='dest')
      mock_walk.assert_called_with('.') # base of 'src' arg
      return E

   def test_get_cover(self):
      "Valid covers are found in the album directories."
      E = self._new_encoder()
      eq_( E.cover, 'root_dir/cover.jpg' )

   @patch( 'os.path.getmtime' )
   def test_is_cover_newer_true(self, mock_getmtime):
      "Update of covers is detected if newer than dest file."
      # getmtime return values: dest file, src file
      time = ['0','1']
      def getmtime_ret(*args,**kwargs): return time.pop()
      mock_getmtime.side_effect = getmtime_ret
      val = self._new_encoder()._is_cover_newer()
      eq_( val, True )

   @patch( 'os.path.getmtime' )
   def test_is_cover_newer_false(self, mock_getmtime):
      "No update of covers is detected if dest file is newere than source."
      # getmtime return values: dest file, src file
      time = ['1','0']
      def getmtime_ret(*args,**kwargs): return time.pop()
      mock_getmtime.side_effect = getmtime_ret
      val = self._new_encoder()._is_cover_newer()
      eq_( val, False )

   def test_is_cover_newer_no_cover(self ):
      "No update of covers is detect if cover file does not exsist."
      # getmtime return values: dest file, src file
      walk_no_cover = [('root_dir', 'dummy',
                        ('file1.flac','file2.flac','file3.flac'))]
      E = self._new_encoder( walk_value=walk_no_cover)
      val = E._is_cover_newer()
      eq_( val, False )
