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
Recursively mirror a directory tree of FLAC audio files to AAC. Source files
can be filtered (by sub-directory, or full path) in order to limit the files
converted. The script will also attempt to retain all meta-data fields in the
output files.

At a Glance
===========

* Mirror directory tree of FLAC files audio files to AAC (re-encoded using NeroAacEnc?).
* Filter source tree using one or more sub-directory paths.
* By default, will only re-encode missing or out-of-date AAC files.
* Optionally deletes orphaned output files.
* Multi-threaded encoding ensures full CPU utilization.
* Supports transfer of FLAC meta-data including *title*, *artist*, *album*.
* Converts FLAC replaygain field to Apple iTunes Sound Check.
* Resizes and embeds album cover art JPEG files to destination files.

Usage Model
===========

* Hard disk space is cheap, but flash-based media players are still limited in
  capacity.
* Create an AAC encoded "mirror" of your music files for portability.
* Setup a daily cron job to always keep your FLAC and AAC files syncronized.
* Re-encode your FLAC library to different AAC bit-rates in one command.
"""

import sys
import os
import optparse as op
import multiprocessing
import textwrap

from . import decoder
from . import encoder
from . import util

__version__ = '0.1'
__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'

# define a mapping of enocoder-types to implementation class name.
ENCODERS = {'aac':encoder.AacEncoder }


#############################################################################
def print_status( file_, count, total, dirs ):
   """Output progress of encoding to terminal."""
   dir_ = os.path.dirname(file_)
   if not dir_ in dirs:
      # print current directory
      print '-'*30
      print '%s/...' % (dir_[:74],)
      dirs[dir_] = True
   # print input file
   pos = '[%d of %d]' % (count,total)
   print '%15s %-60s' % (pos, os.path.basename(file_)[:60],)
   sys.stdout.flush()


def process_flac( opts, e, total, count, dirs ):
   """Perform all process steps to convert every FLAC file to the defined
   output format."""
   try:
      # increment counter
      count.value += 1
      print_status( e.src, count.value, total, dirs)
      if e.encode( opts.force ):
         e.tag( **decoder.FlacDecoder(e.src).tags )
         e.set_cover(True)  # force new cover
      else: # update cover if newer
         e.set_cover()
   except KeyboardInterrupt: pass
   except:
      import traceback
      traceback.print_exc()


def get_dest_orphans( dest_dir, base_dir, sources ):
   """Return a list of destination files that have no matching source file.
   Only consider files that match paths from source list (if any)."""
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
   """Prompt the user to remove all orphaned files located in the destination
   file path(s)."""
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
   """Return a list of source files for transcoding."""
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
   """Convert all source paths to absolute path, and remove non-existent
   paths."""
   # try to extend sources list using 'base_dir' as root
   sources.extend( [os.path.join(base_dir,f) for f in sources] )
   # apply abspath to all items, remove invalid paths
   sources = filter( os.path.exists, map(os.path.abspath,sources) )
   sources = list(set(sources)) # remove duplicates
   return sources


def get_opts( argv ):
   usage = """%prog [options] BASE_DIR [SOURCE ...]

   BASE_DIR    Define the 'root' of the source FLAC directory hierarchy. All
               output files will be generated in directory parallel to the
               BASE_DIR.  The generated file paths in the destination directory
               will be mirror each source path, starting from BASE_DIR.

   SOURCE ...  Optional dir/file argument list to select source files for
               transcoding. If not defined, all files in BASE_DIR will be
               transcoded.  The SOURCE file/dir list must be relative from
               BASE_DIR or the current working directory.
   """
   parser = op.OptionParser(usage=usage, version="%prog "+__version__)
   parser.add_option( '-c', '--threads', dest='thread_count',
         default=multiprocessing.cpu_count(),
         help="set max number of encoding threads (default %default)" )

   helpstr = """
      force re-encode of all files from the source dir; by default source files
      will be skipped if it is determined that an up-to-date copy exists in the
      destination path"""
   parser.add_option( '-f', '--force', dest='force', default=False,
         action="store_true", help=_help_str(helpstr) )

   parser.add_option( '-t', '--type', dest='enc_type', default="aac",
         help="select the output transcode format [%default (default)]")

   helpstr = """
      prevent the removal of files and directories in the dest dir that have no
      corresponding source file"""
   parser.add_option( '-o', '--ignore-orphans', dest='del_orphans',
         default=True, action="store_false", help=_help_str(helpstr) )

   # ACC only options
   aac_group = op.OptionGroup( parser, "AAC Encoder Options" )
   helpstr = """
      set the AAC encoder quality value, must be a float range of 0..1
      [%default (default)]"""
   aac_group.add_option( '-q', '--quality', dest='aac_q', default='0.35',
         help=_help_str(helpstr) )
   parser.add_option_group( aac_group )

   # examine input args
   (opts, args) = parser.parse_args( argv )
   if not args:
      print( "ERROR: BASE_DIR not defined !!" )
      sys.exit(-1)
   if opts.enc_type not in ENCODERS.keys():
      print( "ERROR: '%s' is not a valid encoder !!" % (opts.enc_type,) )
      sys.exit(-1)

   # set encoder
   opts.EncClass = ENCODERS[opts.enc_type]

   # handle positional arguments
   opts.base_dir = os.path.abspath(args[0])
   opts.sources = normalize_sources( opts.base_dir, args[1:] )

   # set default destination directory
   opts.dest_dir = os.path.join( os.path.dirname(opts.base_dir), opts.enc_type)
   return opts


def _help_str( text ):
   return textwrap.dedent(text).strip()


def main( argv=None ):
   opts = get_opts( argv )
   # use base dir and input filter to locate all input files
   flacs = get_src_files( opts.base_dir, opts.sources )

   # convert files to encoder objects
   encoders = (opts.EncClass( src=f, base_dir=opts.base_dir,
                  dest_dir=opts.dest_dir) for f in flacs)
   # filter out encoders that are unnecessary
   if not opts.force:
      encoders = (e for e in encoders if not e.skip_encode())
   encoders = list(encoders)

   # remove orphans, if defined
   if opts.del_orphans:
      del_dest_orphans( opts.dest_dir, opts.base_dir, opts.sources)

   # create mp Pool
   p = multiprocessing.Pool( opts.thread_count )
   m = multiprocessing.Manager()
   count = m.Value('i', 0) # shared file counter
   dirs  = m.dict() # shared dir map
   try:
      for e in encoders:
         p.apply_async( process_flac, args=(opts, e, len(encoders), count, dirs))

      p.close()
      p.join()
   except KeyboardInterrupt:
      print 'caught Control-C'
      sys.exit()


if __name__ == '__main__':
   try:
      sys.exit( main(sys.argv[1:]) )
   except KeyboardInterrupt:
      sys.exit(-1)

