#__LICENSE_GOES_HERE__
from __future__ import with_statement
import sys
sys.path.append('..')
from buildutil import dpy, fatal, cd, DEPS_DIR, DEBUG
from os.path import join as pathjoin, abspath, isdir, dirname

EXTDIR = pathjoin(dirname(__file__), '../../ext')

from compiledeps import libxml2_dirname
from build_libxml2 import iconv_dirname

distutils_debug = '--debug' if DEBUG else ''

def build_xmlextra():
    '''Builds _xmlextra.pyd, a speedups module for pyxmpp.'''

    libxml2_dir = abspath(libxml2_dirname)
    iconv_dir = abspath(iconv_dirname)

    lxml2_libs = pathjoin(libxml2_dir, 'win32', 'bin.msvc')
    lxml2_inc = pathjoin(libxml2_dir, 'include')

    with cd(EXTDIR):
        import os
        dpy(['build_xmlextra.py', 'clean'])
        dpy(['build_xmlextra.py', 'build_ext'] + ([distutils_debug] if distutils_debug else []) + [
            '-L' + os.pathsep.join(filter(None, [lxml2_libs] + os.environ.get('LIB', '').split(os.pathsep))),
            '-I' + os.pathsep.join(filter(None, [iconv_dir, lxml2_inc] + os.environ.get('INCLUDE', '').split(os.pathsep))),
            'install', '--install-lib', DEPS_DIR])

def main():
    build_xmlextra()

if __name__ == '__main__':
    main()
