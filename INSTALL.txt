Installation Steps
==================

1. Any one of the following command will install *flacsync*. Make sure to run as
   ``root`` user:

   a. Use ``easy_install`` from the `setuptools package
      <http://peak.telecommunity.com/DevCenter/EasyInstall]>`_::

         sudo easy_install flacsync

   b. Download the source distribution file and install from the
      command line::

         tar xzf flacsync-*.tar.gz
         cd flacsync-*
         sudo make install

2. Install necessary dependencies:

  a. Common Linux distribution packages:

  * The following common distro packages are necessary:
    - Python Imaging Library
    - Flac tools
    - Ogg tools

  * To install in Debian/Ubuntu:
    $ apt-get install python-imaging flac vorbis-tools

  b. ACC Utils

  * AAC encoding archive is located at the `Nero AAC Codec Download Page`_
  * Extract the archive files **neroAacEnc** and **neroAacTag** to any
    directory defined in your PATH statement. A recommended location would be
    either ``/usr/bin`` or ``/usr/local/bin``.

3. Review the usage instruction by running::

      flacsysnc -h

.. _Nero AAC Codec Download Page: http://www.nero.com/eng/downloads-nerodigital-nero-aac-codec.php
