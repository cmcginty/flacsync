"""
   Test module for Encoder.py
"""

from __future__ import absolute_import

import unittest
from nose.tools import *
from mock import *

from .. import encoder
from .. import util

__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'


class TestCovers(unittest.TestCase):
   WALK_VALUE = [('root_dir', 'dummy',
                        ('file1.flac','file2.flac','cover.jpg'))]

   WALK_NO_COVER = [('root_dir', 'dummy',
                        ('file1.flac','file2.flac','file3.flac'))]

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

   def test_get_cover_without_cover(self):
      "Cover is not set when no cover file is present"
      E = self._new_encoder( walk_value=self.WALK_NO_COVER)
      eq_( E.cover, None )

   @patch('flacsync.util.newer')
   def test_is_cover_newer_no_cover( self, mock_newer ):
      "No update of covers is detect if cover file does not exist."
      mock_newer.return_value = False
      # getmtime return values: dest file, src file
      E = self._new_encoder( walk_value=self.WALK_NO_COVER)
      val = E.skip_encode()
      eq_( val, True )
      eq_( len(mock_newer.call_args_list), 1)
