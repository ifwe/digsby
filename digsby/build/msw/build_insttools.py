#__LICENSE_GOES_HERE__
'''

- nsis
- py2exe

'''
from __future__ import with_statement

import sys
if not '..' in sys.path:
    sys.path.append('..')

from buildutil import run, fatal, tardep, cd, dpy
from os import environ
from os.path import isdir, abspath

# overridable from environment
NSIS_PATH = environ.get('NSIS_PATH', r'c:\Program Files\NSIS')
DOTSYNTAX_SVN = environ.get('DOTSYNTAX_SVN', 'http://mini')

DIGSBY_INSTALLER_SVN = DOTSYNTAX_SVN + '/svn/dotSyntax/DigsbyInstaller/trunk'
PY2EXE_DIR = '/py2exe'
PY2EXE = DIGSBY_INSTALLER_SVN + PY2EXE_DIR

def patch_nsis():
    if not isdir(NSIS_PATH):
        fatal('Cannot find NSIS installation at %s')

    print '\nPlease copy the contents of\n%s into %s' % (abspath('NSIS'), NSIS_PATH)

def build_py2exe():
    from buildutil import DEPS_DIR
    assert isdir(DEPS_DIR)

    with cd('DigsbyInstaller' + PY2EXE_DIR):
        # -i means the PYD will sit next to the files in py2exe/py2exe
        dpy(['setup.py', 'build', 'install', '--install-lib', str(DEPS_DIR)])
        print
        print 'py2exe source and PYDs are in:'
        print abspath('.')
        print

def main():
    run('svn co %s' % DIGSBY_INSTALLER_SVN)

    patch_nsis()
    build_py2exe()

if __name__ == '__main__':
    main()
