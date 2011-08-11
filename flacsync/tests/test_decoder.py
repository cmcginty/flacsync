#  Copyright (c) 2011, Patrick C. McGinty
#
#  This program is free software: you can redistribute it and/or modify it
#  under the terms of the Simplified BSD License.
#
#  See LICENSE text for more details.
"""
   Unit testing framework for flacsync.decoder module.
"""

from __future__ import absolute_import

from mock import Mock,patch
import unittest
from .. import decoder

class TestFlacTags( unittest.TestCase ):

   def setUp(self):
      self.d = decoder.FlacDecoder('temp_file.flac')

   @patch('subprocess.Popen')
   def testTags(self,mock_popen):
      popen_ret = Mock()
      popen_ret.communicate.return_value = ('artist=metallica',[])
      mock_popen.return_value = popen_ret
      t = self.d._read_tag('artist')
      self.assertEquals( t, 'metallica' )

      popen_ret.communicate.return_value = ('artist=metallica\n'+
                                            'artist=iron maiden',[])
      t = self.d._read_tag('artist')
      self.assertEquals( t, 'metallica - iron maiden' )
