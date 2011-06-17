#  Copyright (c) 2011, Patrick C. McGinty
#
#  This program is free software: you can redistribute it and/or modify it
#  under the terms of the Simplified BSD License.
#
#  See LICENSE text for more details.
"""
   Recursively mirror a directory tree of FLAC audio files to AAC/OGG. Source
   files can be filtered (by sub-directory, or full path) in order to limit the
   files converted. The script will also attempt to retain all meta-data fields
   in the output files.

   At a Glance
   ===========

   * Mirror directory tree of FLAC files audio files to AAC/OGG (re-encoded
     using NeroAacEnc).
   * Filter source tree using one or more sub-directory paths.
   * By default, will only re-encode missing or out-of-date AAC/OGG files.
   * Optionally deletes orphaned output files.
   * Multi-threaded encoding ensures full CPU utilization.
   * Supports transfer of FLAC meta-data including *title*, *artist*, *album*.
   * Converts FLAC replaygain field to Apple iTunes Sound Check.
   * Resizes and embeds album cover art JPEG files to destination files.

   Usage Model
   ===========

   * Hard disk space is cheap, but flash-based media players are still limited
     in capacity.
   * Create a lossy encoded "mirror" of your music files for portability.
   * Setup a daily cron job to always keep your FLAC and AAC/OGG files
     synchronized.
   * Re-encode your FLAC library to different AAC/OGG bit-rates in one command.

   Running and Options
   ===================

   Flacsync is run from the command-line, using the following format. ::

      flacsync [options] BASE_DIR [SOURCE ...]

   ``BASE_DIR``

   Define the root path of a directory hierarchy containing desired input files
   (FLAC).  A mirrored output directory will be created in the deepest path,
   parallel to ``BASE_DIR``, and named after the selected output file
   extension.

   For example, if ``BASE_DIR`` is ``/data/flac``, the output dir will be
   ``/data/aac``.

   ``SOURCE ...``

   Optional dir/file argument list to select source files for transcoding.  If
   not defined, all files in ``BASE_DIR`` will be transcoded.  The ``SOURCE``
   file/dir list must be relative from ``BASE_DIR`` or the current working
   directory.

   --version            show program's version number and exit

   -h, --help           show this help message and exit

   -c THREAD_COUNT, --threads=THREAD_COUNT
                        set max number of encoding threads [default:2]

   -f, --force          force re-encode of all files from the source dir; by
                        default source files will be skipped if it is
                        determined that an up-to-date copy exists in the
                        destination path

   -t ENC_TYPE, --type=ENC_TYPE
                        select the output transcode format; supported values
                        are 'aac','ogg' [default:aac]

   -o, --ignore-orphans
                        prevent the removal of files and directories in the
                        dest dir that have no corresponding source file

   -d DEST_DIR, --destination=DEST_DIR
                        define alternate destination output directory to
                        override the default. The standard default destination
                        directory will be created in the same parent directory
                        of BASE_DIR. See BASE_DIR above.

   AAC Encoder Options:
   ---------------------

    -q AAC_Q, --aac-quality=AAC_Q
                        set the AAC encoder quality value, must be a float
                        range of 0..1 [default:0.35]

   OGG Encoder Options:
   --------------------
    -g OGG_Q, --ogg-quality=OGG_Q
                        set the Ogg Vorbis encoder quality value, must be a
                        float range of -1..10 [default:5]

   Examples
   ========

   1. Encode a directory of FLAC files to AAC. Output file will be written to
      ``/music/aac``.
      ::

         flacsync /music/flac
         cd /music/flac; flacsync .

   2. Encode a directory of FLAC files to AAC. Output files will be written to
      ``/ipod``.
      ::

         flacsync -d /ipod /music/flac

   3. Encode a directory of FLAC files to high-quality OGG, using 4 CPU
      threads.
      ::

         flacsync -c 4 -t ogg -g 9 /music/flac

   4. Force re-encode two albums of FLAC files, even if the AAC files exist.
      ::

         flacsync -f /music/flac artist1/album artist2/album
         cd /music/flac; flacsync -f . artist1/album artist2/album
"""

import multiprocessing.dummy as mp
import optparse as op
import os
import sys
import textwrap

from . import decoder
from . import encoder
from . import util

__version__ = '0.3.1'
__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'

DEFAULT_ENCODER = 'aac'

# define a mapping of enocoder-types to implementation class name.
ENCODERS = {'aac':encoder.AacEncoder,
            'ogg':encoder.OggEncoder,
            'mp3':encoder.Mp3Encoder,
         }
CORES = mp.cpu_count()


#############################################################################
class WorkUnit( object ):
   """
   Processing unit for transcoding a single file.

   Multiple instances of this class are asynchronously executed in a
   multiprocessing worker pool queue.
   """
   def __init__( self, opts, max_work ):
      """
      :param opts:   Parsed command-line options.
      :type  opts:   :mod:`optparse`.Values

      :param max_work: Total number of workers in the pool.
      :type  max_work: int
      """
      self.abort = False
      self._opts = opts
      self._max_work = max_work
      self._count = 0
      self._dirs = {}

   def _log( self, file_ ):
      """Output progress of encoding to terminal."""
      lines = []
      dir_ = os.path.dirname(file_)
      if not dir_ in self._dirs:
         # print current directory
         lines.append( '-'*30 )
         lines.append( '%s/...' % (dir_[:74],))
         self._dirs[dir_] = True
      # print input file
      pos = '[%d of %d]' % (self._count,self._max_work)
      lines.append( '%15s %-60s' % (pos, os.path.basename(file_)[:60],) )
      return '\n'.join(lines)

   def do_work( self, encoder ):
      """
      Perform all process steps to convert FLAC file to the defined
      output format.

      :param encoder: Encoder instance object used for conversion.
      :type  encoder: :mod:`flacsync.encoder`._Encoder
      """
      if self.abort: return
      try:
         file_ = encoder.src
         self._count += 1
         print self._log( file_ )
         sys.stdout.flush()
         if encoder.encode( self._opts.force ):
            encoder.tag( decoder.FlacDecoder(file_).tags )
            encoder.set_cover(True)  # force new cover
         else: # update cover if newer
            encoder.set_cover()
      except KeyboardInterrupt:
         self.abort = True
      except Exception as exc:
         print "ERROR: '%s' !!" % (file_,)
         print exc


def get_dest_orphans( dest_dir, base_dir, sources ):
   """
   Return a list of destination files that have no matching source file.  Only
   consider files that match paths from source list (if any).

   :param dest_dir:  Desintation root directory path, to find orpahned files.
   :type  dest_dir:  str

   :param base_dir:  Base directory (of FLAC files) for comparing with
                     :data:`dest_dir`.
   :type  base_dir:  str

   :param sources:   List of 0 or more path strings, relative to
                     :data:`base_dir` for bulding a subset of all source files.
   :type  sources:   list

   :returns: List of orphan destination files.
   """
   orphans = []
   # walk all destination sub-directories
   for root, dirs, files in os.walk( dest_dir, followlinks=True ):
      orphans.extend( os.path.abspath(os.path.join(root,f)) for f in files )

   # remove files from destination not found under one (or more) paths from the
   # source list
   if sources:
      # if absolute path, convert src filters to reference dest dir
      dests = (f.replace( base_dir, dest_dir, 1) for f in sources)
      orphans = (f for f in orphans for p in dests if f.startswith(p))

   # remove all files with valid sources
   orphans = (f for f in orphans if not
         os.path.exists(
            util.fname(f, base=dest_dir, new_base=base_dir, new_ext='.flac')) )
   return orphans


def del_dest_orphans( dest_dir, base_dir, sources ):
   """
   Interactively prompt the user to remove all orphaned files located in the
   destination file path(s).

   :param dest_dir:  Desintation root directory path, to find orpahned files.
   :type  dest_dir:  str

   :param base_dir:  Base directory (of FLAC files) for comparing with
                     :data:`dest_dir`.
   :type  base_dir:  str

   :param sources:   List of 0 or more path strings, relative to
                     :data:`base_dir` for bulding a subset of all source files.
   :type  sources:   list
   """
   # create list of orphans
   orphans = get_dest_orphans( dest_dir, base_dir, sources )
   yes_to_all = False
   for o in orphans:
      rm = True
      if not yes_to_all:
         while True:
            val = raw_input( "remove orphan `%s'? [YES,no,all,none]: " % (o,))
            val = val.lower()
            if val == 'none': return
            elif val in ['a','all']:
               yes_to_all = True
               break
            elif val in ['y','yes','']: break
            elif val in ['n','no']:
               rm = False
               break
      if rm:
         os.remove(o)

   # remove empty directories from 'dest_dir'
   for root,dirs,files in os.walk(dest_dir, topdown=False):
      if root != dest_dir:
         try:
            os.rmdir(root)   # remove dir
         except OSError: pass


def get_src_files( base_dir, sources ):
   """
   Return a list of source files for transcoding.

   :param base_dir:  Base directory of FLAC files.
   :type  base_dir:  str

   :param sources:   List of 0 or more path strings, relative to
                     :data:`base_dir` for bulding a subset of all source files.
   :type  sources:   list

   :returns: List of source files.
   """
   input_files = []
   # walk all sub-directories
   for root, dirs, files in os.walk( base_dir, followlinks=True ):
      # filter flac files
      flacs = (f for f in files if os.path.splitext(f)[1] == '.flac')
      input_files.extend( os.path.abspath(os.path.join(root,f)) for f in flacs )

   # remove files not found under one (or more) paths from the source list
   if sources:
      input_files = (f for f in input_files for p in sources if f.startswith(p))
   return input_files


def normalize_sources( base_dir, sources ):
   """
   Convert all source paths to absolute path, and remove non-existent paths.

   :param base_dir:  Base directory of FLAC files.
   :type  base_dir:  str

   :param sources:   List of 0 or more path strings, relative to
                     :data:`base_dir` for bulding a subset of all source files.
   :type  sources:   list

   :returns: List of source files with absolute path names.
   """
   # try to extend sources list using 'base_dir' as root
   alt_sources = [os.path.join(base_dir,f) for f in sources]
   sources = zip( sources, alt_sources )
   # apply 'os.path.exists' to tuples of dirs
   is_valid_path = [ map(os.path.exists,x) for x in sources ]
   # find any False 'is_valid' tuples
   invalid = [x for x in zip(sources,is_valid_path) if not any(x[1])]
   if invalid:
      raise ValueError( "', or '".join(invalid[0][0]))
   # apply abspath to all items, remove duplicates
   sources = [inner for outer in sources for inner in outer]
   return list(set(map(os.path.abspath,sources)))


def store_once( option, opt_str, value, parser, *args, **kw):
   """
   :mod:`optparse` handler for one-time storage of single option.

   .. seealso::

      :ref:`optparse-option-callbacks` reference.

   :param option: The Option instance that's calling the callback.
   :type  option: :ref:`Option <optparse-option-attributes>`

   :param opt_str: Option selector value (i.e. ``-a```).
   :type  opt_str: str

   :param value:  Argument to the option from the command-line.
   :type  value:  str

   :param parser: The current parser instance.
   :type  parser: :class:`~optparse.OptionParser`

   :raises: :exc:`OptionValueError` if option is already defined.
   """
   old_val = getattr(parser.values, option.dest)
   if not (old_val is None or old_val == value):
      raise op.OptionValueError(
         "option '%s' can not redefine '%s' to '%s'" % (opt_str,old_val,value))
   else:
      setattr(parser.values, option.dest, value)


def store_enc_opt( option, opt_str, value, parser, *args, **kw):
   """
   :mod:`optparse` handler for storing an encoder option.

   .. seealso::

      :ref:`optparse-option-callbacks` reference.

   :param option: The Option instance that's calling the callback.
   :type  option: :ref:`Option <optparse-option-attributes>`

   :param opt_str: Option selector value (i.e. ``-a```).
   :type  opt_str: str

   :param value:  Argument to the option from the command-line.
   :type  value:  str

   :param parser: The current parser instance.
   :type  parser: :class:`~optparse.OptionParser`

   :raises: :exc:`OptionValueError` if encoder does not support the option.
   """
   # set the default encoder if it has not be defined
   if not parser.values.enc_type:
      parser.values.enc_type = DEFAULT_ENCODER

   # check that encoder type matches the encoder option type
   enc = parser.values.enc_type
   if not enc or enc == args[0]:
      setattr(parser.values, option.dest, value)
   else:
      raise op.OptionValueError(
         "option '%s' is not allowed with '%s' encoder" % (opt_str,enc))


def get_opts( argv ):
   """
   Initializes option parser and reads command-line options.

   :param argv: The command-line argument list
   :type  argv: list

   :returns: :class:`optparse.OptionValue` instance of the parsed options.
   """
   usage = """%prog [options] BASE_DIR [SOURCE ...]

   BASE_DIR    Define the root path of a directory hierarchy containing desired
               input files (FLAC).  A mirrored output directory will be created
               in the deepest path, parallel to BASE_DIR, and named after the
               selected output file extension. For example, if BASE_DIR is
               "/data/flac", the output dir will be "/data/aac".

   SOURCE ...  Optional dir/file argument list to select source files for
               transcoding. If not defined, all files in BASE_DIR will be
               transcoded.  The SOURCE file/dir list must be relative from
               BASE_DIR or the current working directory.
   """
   parser = op.OptionParser(usage=usage, version="%prog "+__version__)
   parser.add_option( '-c', '--threads', dest='thread_count', default=CORES,
         type='int',
         help="set max number of encoding threads [default:%default]" )

   helpstr = """
      force re-encode of all files from the source dir; by default source files
      will be skipped if it is determined that an up-to-date copy exists in the
      destination path"""
   parser.add_option( '-f', '--force', dest='force', default=False,
         action="store_true", help=_help_str(helpstr) )

   helpstr = """
      select the output transcode format; supported values are 'aac','ogg'
      [default:%s]""" % (DEFAULT_ENCODER,)
   # note: the default encoder is enforced manually
   parser.add_option( '-t', '--type', choices=ENCODERS.keys(),
         action='callback', callback=store_once,
         type='choice', dest='enc_type', help=_help_str(helpstr))

   helpstr = """
      prevent the removal of files and directories in the dest dir that have no
      corresponding source file"""
   parser.add_option( '-o', '--ignore-orphans', dest='del_orphans',
         default=True, action="store_false", help=_help_str(helpstr) )

   helpstr = """
      define alternate destination output directory to override the default.
      The standard default destination directory will be created in the same
      parent directory of BASE_DIR. See BASE_DIR above."""
   parser.add_option( '-d', '--destination', dest='dest_dir',
         help=_help_str(helpstr) )

   # AAC only options
   aac_group = op.OptionGroup( parser, "AAC Encoder Options" )
   helpstr = """
      set the AAC encoder quality value, must be a float range of 0..1
      [default:%default]"""
   aac_group.add_option( '-q', '--aac-quality', dest='aac_q', default='0.35',
         action='callback', callback=store_enc_opt, callback_args=('aac',),
         type='string', help=_help_str(helpstr) )
   parser.add_option_group( aac_group )

   # OGG only options
   ogg_group = op.OptionGroup( parser, "OGG Encoder Options" )
   helpstr = """
      set the Ogg Vorbis encoder quality value, must be a float range of -1..10
      [default:%default]"""
   ogg_group.add_option( '-g', '--ogg-quality', dest='ogg_q', default='5',
         action='callback', callback=store_enc_opt, callback_args=('ogg',),
         type='string', help=_help_str(helpstr) )
   parser.add_option_group( ogg_group )

   # MP3 only options
   mp3_group = op.OptionGroup( parser, "MP3 Encoder Options" )
   helpstr = """
      set the Lame MP3 encoder quality value, must be a initeger range of 9..0
      [default:%default]"""
   mp3_group.add_option( '-m', '--mp3-quality', dest='mp3_q', default='3',
         action='callback', callback=store_enc_opt, callback_args=('mp3',),
         type='string', help=_help_str(helpstr) )
   parser.add_option_group( mp3_group )

   # examine input args
   (opts, args) = parser.parse_args( argv )
   if not args:
      print "ERROR: BASE_DIR not defined !!"
      sys.exit(-1)

   # check/set encoder
   if not opts.enc_type:
      opts.enc_type = DEFAULT_ENCODER
   opts.EncClass = ENCODERS[opts.enc_type]

   # handle positional arguments
   opts.base_dir = os.path.abspath(args[0])
   try:
      opts.sources = normalize_sources( opts.base_dir, args[1:] )
   except ValueError as exc:
      print "ERROR: '%s' is not a valid path !!" % (exc,)
      sys.exit(-1)

   # set default destination directory, if not already defined
   if not opts.dest_dir:
      opts.dest_dir = os.path.join(os.path.dirname(opts.base_dir),opts.enc_type)
   opts.dest_dir = os.path.abspath(opts.dest_dir)
   return opts


def _help_str( text ):
   return textwrap.dedent(text).strip()


def main( argv=None ):
   """
   Primary entry function.

   :param argv: The command-line argument list
   :type  argv: list
   """
   opts = get_opts( argv )
   # use base dir and input filter to locate all input files
   flacs = get_src_files( opts.base_dir, opts.sources )

   # convert files to encoder objects
   enc_opts = dict((k,v) for k,v in vars(opts).iteritems()
                  if k.startswith(opts.enc_type))
   encoders = (opts.EncClass( src=f, base_dir=opts.base_dir,
                  dest_dir=opts.dest_dir, **enc_opts) for f in flacs)
   # filter out encoders that are unnecessary
   if not opts.force:
      encoders = (e for e in encoders if not e.skip_encode())
   encoders = list(encoders)

   # remove orphans, if defined
   if opts.del_orphans:
      del_dest_orphans( opts.dest_dir, opts.base_dir, opts.sources)

   # exit if no work
   if not encoders: return

   # create work pool, and add jobs
   queue = mp.Pool( processes=opts.thread_count )
   work_obj = WorkUnit( opts, len(encoders) )
   for e in encoders:
      queue.apply_async( work_obj.do_work, (e,) )
   try:
      queue.close()
      queue.join()
   except KeyboardInterrupt:
      work_obj.abort = True

