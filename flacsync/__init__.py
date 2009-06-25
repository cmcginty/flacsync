#!/usr/bin/env python
"""
   Recursively mirrors FLAC audio fles to AAC. The source FLAC files sourced
   can be filtered by sub-directory in order to limit the files converted. The
   script will also attempt to retain all meta-data fields in the output files.

   At A Glance
   ===========

   * Mirror directory tree of FLAC files to AAC (using NeroAacEnc).
   * Filter source file selection using one or more sub-directory paths.
   * By default, will only re-encode missing or out-of-date AAC files.
   * Optionally deletes orphaned output files.
   * Multi-threaded encoding ensures full CPU utilization.
   * Supports transfer of FLAC meta-data including *title*, *artist*, *album*.
   * Converts FLAC replaygain field to Apple iTunes Sound Check.
   * Resizes and embeds album cover art JPEG files to destination files.
"""

import sys
import os
import optparse as op
import subprocess as sp
import multiprocessing
import Image
import tempfile

__version__ = '0.1'
__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'

NULL = file('/dev/null')
# list of album covers, in preferential order
COVERS = ['cover.jpg', 'folder.jpg', 'frong.jpg', 'album.jpg']


#############################################################################
class Encoder(object):
   # dimensions of cover thumbnails in pixels
   THUMBSIZE = 250,250
   def __init__( self, src, ext, base_dir, dest_dir, **kwargs ):
      super( Encoder, self).__init__()
      self.src = src
      self.dst = fname(src,base_dir,dest_dir,ext)
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
      sc = 1000 * pow(10,(-0.1*rg_f))
      return "%08X" % (sc,)

   def _cover_thumbnail(self):
      if not self.cover: return None
      im = Image.open(self.cover)
      im.thumbnail(self.THUMBSIZE)
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
      cmd = ['-meta-user:ITUNNORM="%s"' % (sc_val,)]
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


#############################################################################
class FlacDecoder( object ):

   FLAC_TAGS = {
      'artist':'artist',
      'title':'title',
      'album':'album',
      'year':'date',
      'track':'tracknumber',
      'genre':'genre',
      'replay_gain':'REPLAYGAIN_TRACK_GAIN',
      }

   def __init__(self, name):
      self.name = name

   @property
   def tags(self):
      return dict((k,self._read_tag(v)) for k,v in self.FLAC_TAGS.items())

   def _read_tag(self,field):
      val = sp.Popen( 'metaflac --show-tag=%s "%s"' % (field,self.name),
            shell=True, stdout=sp.PIPE).communicate()[0]
      return val.split('=')[1].strip()


#############################################################################
ENCODERS = {'aac':AacEncoder }

def process_flac( opts, f ):
   """Perform all process steps to convert every FLAC file to the defined
   output format."""
   try:
      # print input file
      print '\t',
      print os.path.basename(f)
      EncClass = ENCODERS[opts.enc_type]
      e = EncClass( src=f, q=opts.aac_q, base_dir=opts.base_dir,
            dest_dir=opts.dest_dir ) # instantiate the encoder
      encoded = e.encode( opts.force )
      if encoded:
         e.tag( **FlacDecoder(f).tags )
      e.set_cover( encoded )
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
            fname(f, base=dest_dir, new_base=base_dir, new_ext='.flac')) )
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

   # remove empty directories fraom 'dest_dir'
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


def fname( file_, base=None, new_base=None, new_ext=None ):
   """Convert a file name to a new base + extensions."""
   if base and new_base:
      file_ = file_.replace(base, new_base, 1)
   if new_ext:
      file_ = os.path.splitext(file_)[0] + new_ext
   return file_


def normalize_sources( base_dir, sources ):
   """Convert all source paths to absolute path, and remove non-existant
   paths."""
   # try to extend sources list using 'base_dir' as root
   sources.extend( [os.path.join(base_dir,f) for f in sources] )
   # apply abspath to all items, remove invalid paths
   sources = filter( os.path.exists, map(os.path.abspath,sources) )
   sources = list(set(sources)) # remove duplicates
   return sources


def get_opts( argv ):
   usage = """%prog [options] BASE_DIR [SOURCE ...]

   BASE_DIR    Define the 'root' of the source FLAC directory heirarcy. All
               output files will be generated in directory parallel to the
               BASE_DIR.  The generated file paths in destination directory
               will be created to duplicate the source path, starting from
               BASE_DIR.

   SOURCE ...  Optional dir/file argument list to select source files for
               transcoding. If not defined, all files in BASE_DIR will be
               transcoded.  The SOURCE file/dir list must be relative from
               BASE_DIR or the current working directory.
   """
   parser = op.OptionParser(usage=usage, version="%prog "+__version__)
   parser.add_option( '-c', '--threads', dest='thread_count',
         default=multiprocessing.cpu_count(),
         help="define max number of encoding threads (default %default)" )
   parser.add_option( '-f', '--force', dest='force',
         default=False, action="store_true",
         help="set to force re-enocde of files that exists in the output dir" )
   parser.add_option( '-t', '--type', dest='enc_type', default="aac",
         help="set the output transcode format [%default (default)]")
   parser.add_option( '-o', '--ignore-orphans', dest='del_orphans',
         default=True, action="store_false",
         help="set to prevent the removal of files and directories in the "
              "dest dir that have no corresponding source file" )
   # ACC only options
   aac_group = op.OptionGroup( parser, "AAC Encoder Options" )
   aac_group.add_option( '-q', '--quality', dest='aac_q', default='0.35',
         help="set the AAC encoder quality value, must be a float range "
              "of 0..1 [%default (default)]")
   parser.add_option_group( aac_group )

   # examine input args
   (opts, args) = parser.parse_args( argv )
   if not args:
      print( "ERROR: BASE_DIR not defined !!" )
      sys.exit(-1)
   if opts.enc_type not in ENCODERS.keys():
      print( "ERROR: '%s' is not a valid encoder !!" % (opts.enc_type,) )
      sys.exit(-1)

   # handle positional arguments
   opts.base_dir = os.path.abspath(args[0])
   opts.sources = normalize_sources( opts.base_dir, args[1:] )

   # set default destination directory
   opts.dest_dir = os.path.join( os.path.dirname(opts.base_dir), opts.enc_type)
   return opts


def main( argv=None ):
   opts = get_opts( argv )
   # use base dir and input filter to locate all input files
   flacs = get_src_files( opts.base_dir, opts.sources )

   # remove orphans, if defined
   if opts.del_orphans:
      del_dest_orphans( opts.dest_dir, opts.base_dir, opts.sources)

   # create mp Pool
   try:
      p = multiprocessing.Pool( opts.thread_count )
      for f in flacs:
         p.apply_async( process_flac, args=(opts, f))
         # process_flac( opts, f)
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

