"""
   Test module for __init__.py
"""

from __future__ import absolute_import

import unittest
from nose.tools import *
from mock import *

import flacsync

__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'


class TestMainCmdArgs(unittest.TestCase):

   def setUp(self):
      self.f_enc_orig = flacsync.ENCODERS
      self.mock_aac_enc = Mock()
      # mock encoder object dict object
      flacsync.ENCODERS = {'aac':self.mock_aac_enc}

   def tearDown(self):
      flacsync.ENCODERS = self.f_enc_orig

   @patch('multiprocessing.dummy.Pool')
   @patch('flacsync.get_src_files')
   def test_no_force( self, mock_get_src_files, mock_pool):
      "Skip encoding a single flac file when it is up to date."
      # mock encoder.skip_encode return value
      self.mock_aac_enc.return_value.skip_encode.return_value = True
      # mock src file list
      mock_get_src_files.return_value = iter(['file1.flac'])
      flacsync.main(argv=['/flac']) # <-- test function
      # assert encoder object creation to for 'skip_encode' method
      assert self.mock_aac_enc.called
      eq_( self.mock_aac_enc.call_args[1]['src'], 'file1.flac' )
      self.mock_aac_enc.return_value.skip_encode.assert_called()
      # file was skiped, so verify it was not called
      assert not mock_pool.return_value.apply_async.called

   @patch('multiprocessing.dummy.Pool')
   @patch('flacsync.get_src_files')
   def test_force( self, mock_get_src_files, mock_pool):
      """Do not skip encoding a single flac file when it is up to date and
      'force' option is enabled."""
      # mock encoder.skip_encode return value
      self.mock_aac_enc.return_value.skip_encode.return_value = True
      # mock src file list
      mock_get_src_files.return_value = iter(['file1.flac'])
      flacsync.main(argv=['-f','/flac']) # <-- test function
      # assert encoder object creation to for 'skip_encode' method
      self.mock_aac_enc.return_value.skip_encode.assert_called()
      # file was skiped, so verify it was not called
      assert mock_pool.return_value.apply_async.called
