#__LICENSE_GOES_HERE__
from __future__ import with_statement

import os.path
import shutil
import sys
sys.path.append('..') if '..' not in sys.path else None

from buildutil import run, fatal, inform, cd, git, dpy, copytree_filter, DEBUG_POSTFIX
from buildutil.common import *
from constants import *

from os.path import isdir, abspath, isfile, join as pathjoin

py_ext = "so"
if sys.platform.startswith("win"):
    py_ext = "pyd"

# local SIP info
sip_path = 'sip'
sip_exe = pathjoin(sip_path, 'sipgen', 'sip')
if sys.platform.startswith("win"):
    sip_exe += ".exe"
sip_pyd = pathjoin(sip_path, 'siplib', 'sip%s.%s' % (DEBUG_POSTFIX, py_ext))
sip_pdb = pathjoin(sip_path, 'siplib', 'sip%s.pdb' % DEBUG_POSTFIX)

# local WXPY info
WXPYDIR = wxpy_path = 'wxpy'

comtypes_url = 'https://comtypes.svn.sourceforge.net/svnroot/comtypes/tags/comtypes-0.6.0/'

# see below for notes on this patch
comtypes_patch = 'comtypes.0.6.0.patch'

def sip():
    sip_path_parent, sip_dir = os.path.split(os.path.abspath(sip_path))

    # Get SIP
    needs_build = True
    with cd(sip_path_parent):
        if not isdir(sip_dir):
            inform('Could not find SIP directory at %r, downloading...' % sip_path)
            git.run(['clone', SIP_GIT_REPO, sip_dir])

            if SIP_GIT_BRANCH != 'master':
                with cd(sip_dir):
                    git.run(['checkout', '-b', SIP_GIT_BRANCH, SIP_GIT_REMOTE + '/' + SIP_GIT_BRANCH])
        else:
            pass
#            inform('SIP found at %r, updating...' % sip_path)
#            with cd(sip_dir):
#                git.run(['pull'])
#                if not git.sha_changed() and isfile(sip_exe) and isfile(sip_pyd):
#                    inform('skipping SIP build')
#                    needs_build = False

    # Build SIP
    if needs_build and 'nosip' not in sys.argv:
        with cd(sip_path):
            if not sys.platform.startswith("win"):
                dpy(['configure.py', '-b', 'sipgen', '-d', 'siplib', '-e', 'siplib', '-v', 'siplib'])
                # sip sets CC and CXX directly to cc and c++ rather than pulling the values
                # from the environment, which we don't want if we're forcing a 32-bit build
                # by using gcc 4.0.
                env = os.environ
                run(['make', 'CC=%s' % env['CC'],
                             'CXX=%s' % env['CXX'],
                             'LINK=%s' % env['CXX']])

            else:
                dpy(['setup.py', 'build'])

    assert isfile(sip_exe), "setup.py did not create %s" % sip_exe

    if sys.platform.startswith("win"):
        from buildutil import copy_different, DEPS_DIR
        copy_different(sip_pyd, DEPS_DIR)
        copy_different(sip_pdb, DEPS_DIR)

def wxpy(rebuild = False, branch="master"):
    wxpy_path_parent, wxpy_dir = os.path.split(os.path.abspath(wxpy_path))

    # must have wx and webkit directories
    wx_dir = buildDirs.wxWidgetsDir
    webkit_dir = buildDirs.wxWebKitDir

    sip_dir = os.path.abspath(sip_path)

    with cd(wxpy_path_parent):
        if not isdir(wxpy_dir):
            inform('Could not find wxpy directory at %r, downloading...' % wxpy_path)
            git.run(['clone', WXPY_GIT_REPO, wxpy_dir])
            if branch != "master":
                with cd(wxpy_dir):
                    git.run(['checkout', '-b', branch, 'origin/%s' % branch])

        # else:
        #     with cd(wxpy_dir):
        #         git.run(['pull'])

        # wipe out the "wxpy/build" directory if we're rebuilding

        if rebuild:
            inform("rebuilding...removing old build directory")
            with cd(wxpy_dir):
                if os.path.isdir('build'):
                    shutil.rmtree('build')

        sip_pyd_loc = pathjoin(sip_dir, 'siplib')

        sip_exe = 'sip%s.%s' % (DEBUG_POSTFIX, py_ext)
        assert os.path.isfile(pathjoin(sip_pyd_loc, sip_exe)), \
            "could not find %s at %r" % (sip_exe, sip_pyd_loc)
        pp = os.pathsep.join([sip_dir, sip_pyd_loc])

        os.environ['PYTHONPATH'] = pp

        print 'PYTHONPATH=' +  pp

        with cd(wxpy_dir):
            dpy(['setup.py',
                 '--wx=%s' % wx_dir,
                 '--webkit=%s' % webkit_dir]
                + sys.argv[1:])


    install_wxpy()

def install_wxpy():
    # install to dependencies dir
    from buildutil import DEPS_DIR
    install_dir = pathjoin(DEPS_DIR, 'wx')
    inform('\n\ninstalling wxpy to %s' % install_dir)

    def ffilter(f):
        return not any(map(f.endswith, ('.exp', '.idb', '.pyc', '.lib')))

    with cd(wxpy_path):
        copytree_filter('wx', install_dir, filefilter = ffilter, only_different = True)


def all():
    sip()
    wxpy(rebuild = 'rebuild' in sys.argv)
    #print 'skipping comtypes'

def main():
    if 'sip' in sys.argv:
        sip()
    elif 'copy' in sys.argv:
        install_wxpy()
    else:
        all()

if __name__ == '__main__':
    main()
