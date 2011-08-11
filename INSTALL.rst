1. Any one of the following command will install **Flacsync**.

   a. Use ``pip`` from the `pip package <http://pypi.python.org/pypi/pip>`_::

         pip install flacsync --upgrade --use

   b. Download the source distribution file and install from the
      command line::

         tar xzf flacsync-*.tar.gz
         cd flacsync-*
         python setup.py install --user

2. Install necessary dependencies:

   a. Common Linux distribution packages:

      The following common distro packages are necessary:

      - Python Imaging Library
      - Flac tools
      - Ogg tools (optional)
      - Lame (optional)

      To install in Debian/Ubuntu::

         apt-get install python-imaging flac vorbis-tools lame

   b. ACC Utils

      * AAC encoding archive is located at the `Nero AAC Codec Download Page`_
      * Extract the archive files **neroAacEnc** and **neroAacTag** to any
        directory defined in your PATH statement. A recommended location would
        be either :file:`/usr/bin` or :file:`/usr/local/bin`.

3. Review the usage instruction by running::

      flacsysnc -h

.. _Nero AAC Codec Download Page: http://www.nero.com/eng/downloads-nerodigital-nero-aac-codec.php
