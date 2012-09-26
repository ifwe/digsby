#__LICENSE_GOES_HERE__
'''
Create a set of binaries needed by the rest of the build process
'''

assert False, "use webkit's cygwin installer"
from __future__ import with_statement
import sys
sys.path.append('..')
from buildutil import wget, cd, unzip

prefix = 'http://gnuwin32.sourceforge.net/downlinks/'
zip_php = 'zip.php'
types   = {'b' : 'bin',
           'd' : 'dep'}
needed = {
          'autoconf'  : 'b',
          'automake'  : 'b',
          'bison'     : 'bd',
          'flex'      : 'b',
          'gperf'     : 'b',
          'make'      : 'bd',
          'wget'      : 'bd',
          'grep'      : 'bd',
          'unzip'     : 'b',
          'which'     : 'b',
          'tar'       : 'bd',
          'unrar'     : 'b',
          'zip'       : 'bd',
          'coreutils' : 'bd',
          }
#          'http://downloads.sourceforge.net/mingw/binutils-2.19.1-mingw32-bin.tar.gz' : None,
#http://subversion.tigris.org/files/documents/15/45222/svn-win32-1.5.6.zip
with cd('downloads'):
    for package, zips in needed.iteritems():
        for letter in zips:
            kind = types[letter]
            name = package + '-' + kind + '-' + zip_php
            wget(prefix + name)
            unzip(name)
