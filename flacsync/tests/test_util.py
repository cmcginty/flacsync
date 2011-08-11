"""
   Test module for Util.py
"""

from __future__ import absolute_import

import unittest
from nose.tools import *
from mock import *

from .. import util

__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'


class TestUtil(unittest.TestCase):
   @patch( 'os.path.exists' )
   @patch( 'os.path.getmtime' )
   def test_is_cover_newer_true(self, mock_getmtime, mock_exists):
      "Update of covers is detected if newer than dest file."
      mock_exists.return_value = True
      # getmtime return values: dest file, src file
      time = ['0','1']
      def getmtime_ret(*args,**kwargs): return time.pop()
      mock_getmtime.side_effect = getmtime_ret
      val = util.newer('f1','f2')
      eq_( val, True )

   @patch( 'os.path.exists' )
   @patch( 'os.path.getmtime' )
   def test_is_cover_newer_false(self, mock_getmtime, mock_exists):
      "No update of covers is detected if dest file is newer than source."
      mock_exists.return_value = True
      # getmtime return values: dest file, src file
      time = ['1','0']
      def getmtime_ret(*args,**kwargs): return time.pop()
      mock_getmtime.side_effect = getmtime_ret
      val = util.newer('f1','f2')
      eq_( val, False )


