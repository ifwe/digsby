#__LICENSE_GOES_HERE__
'''

builds wxWidgets with our customizations

'''

from __future__ import with_statement

from os.path import abspath

import sys; sys.path.append('..')

WX_GIT_REPO = 'https://github.com/kevinw/wx.git'
WX_GIT_BRANCH = 'cairo'

WXWIDGETS_28_SVN_DIR = "http://svn.wxwidgets.org/svn/wx/wxWidgets/branches/wxWebKitBranch-2.8"

WXDIR = 'wxWidgets'

WXPYTHON_28_SVN_DIR = "http://svn.wxwidgets.org/svn/wx/wxPython/branches/WX_2_8_BRANCH"
WXPYDIR = 'wxPython'

WXWEBKIT_SVN_DIR = "http://svn.webkit.org/repository/webkit/trunk"

from buildutil import DEBUG, git, timed
from constants import wxconfig, setup_h_use_flags


CONTRIB = dict(
    STC = True
)


WX_MAKEFILE_ARGS = dict(
    BUILD          = 'debug' if wxconfig.debug_runtime else 'release',
    OFFICIAL_BUILD = 1, # don't append _custom to DLLs
    SHARED         = 1, # make DLLs
    MONOLITHIC     = 0, # split build into several DLLs

    USE_RTTI       = 1,
    USE_HTML       = 1 if wxconfig.html else 0,

    USE_EXCEPTIONS = int(wxconfig.exceptions),

    USE_GDIPLUS    = 1, # wxGraphicsContext support
    USE_OPENGL     = 0, # OpenGL canvas support
    USE_MEDIA      = 0,
    USE_XRC        = 0,
    USE_QA         = 0,
    USE_AUI        = 0,
    USE_RICHTEXT   = 0,
    #USE_CAIRO      = 1,

    UNICODE        = 1,
    MSLU           = 0,

    DEBUG_FLAG     = 1 if wxconfig.debug_assertions else 0,
    WXDEBUGFLAG    = 'd' if wxconfig.debug_runtime else 'h',
    CXXFLAGS       = ['/D__NO_VC_CRTDBG__'] if wxconfig.debug_assertions and not wxconfig.debug_runtime else [],
    LDFLAGS        = ['/OPT:REF', '/OPT:ICF'],
)

wxargs = WX_MAKEFILE_ARGS

wxargs['CXXFLAGS'].extend(['/GS-'])

if wxconfig.debug_symbols:
    wxargs['CXXFLAGS'].append('/Zi')
    wxargs['LDFLAGS'].extend(['/DEBUG'])

if wxconfig.whole_program_optimization:
    wxargs['CXXFLAGS'].append('/GL')
    wxargs['LDFLAGS'].append('/LTCG')

if wxconfig.exceptions:
    wxargs['CXXFLAGS'].append('/EHa')

if wxconfig.disable_all_optimization:
    wxargs['CXXFLAGS'].append('/Od')

CYGWIN_DIR = 'c:\\cygwin'

SWIG_MSG = 'Wrong or missing SWIG on PATH: please install from http://wxpython.wxcommunity.com/tools/'

import os
import sys
if not '..' in sys.path:
    sys.path.append('..') # for buildutil
from buildutil import run, cd, inform, fatal
from os.path import exists, isdir, isfile, join as pathjoin

def checkout():
    if exists(WXDIR):
        inform('already exists: %s' % WXDIR)
    else:
        #inform('checking out wxWebKitBranch-2.8...')
        #run(['svn', 'checkout', WXWIDGETS_28_SVN_DIR, WXDIR])

        inform('cloning wxWebKitBranch-2.8')
        git.run(['clone', WX_GIT_REPO, abspath(WXDIR).replace('\\', '/'), '--depth=1'])
        with cd(WXDIR):
            # don't change newlines
            git.run(['config', 'core.autocrlf', 'false'])

            if WX_GIT_BRANCH != 'master':
                git.run(['fetch', 'origin'])
                # checkout our branch.
                git.run(['checkout', '-b', WX_GIT_BRANCH, 'origin/%s' % WX_GIT_BRANCH])
        assert exists(WXDIR)

def update():
    with cd(WXDIR):
        inform('updating wxWidgets...')
        #run(['svn', 'up'])
        git.run(['checkout', WX_GIT_BRANCH])
        git.run(['pull', 'origin', WX_GIT_BRANCH])

def copy_setup_h():
    inform('copying include/wx/msw/setup0.h to include/wx/msw/setup.h with modifications')

    with cd(WXDIR, 'include', 'wx', 'msw'):

        # setup0.h is the "template" for setup.h. we use the setup_h_use_flags
        # dictionary above to set certain values in it for things we want to
        # customize (results in smaller binaries, since about 50% of wx we don't
        # use or need)
        f   = open('setup0.h', 'rU')
        out = open('setup.h', 'w')

        flags = dict(setup_h_use_flags)
        define_use = '#define wxUSE_'
        for line in f:
            i = line.find(define_use)
            if i != -1:
                use_name = line[i+len(define_use):].split()[0]
                if use_name in flags:
                    line = '%s%s %s\n' % (define_use, use_name, flags.pop(use_name))

            out.write(line)

        # make sure there are no leftover flags
        if flags:
            leftover = '\n'.join('  wxUSE_%s' % key for key in flags.iterkeys())
            raise AssertionError('invalid wxUSE_XXX flags (were not found in setup0.h):\n%s' % leftover)

        out.close()
        f.close()

def bakefile():
    with cd(WXDIR, 'build', 'bakefiles'):
        run(['bakefile_gen', '-f', 'msvc'])

def build(force_bakefile = False):
    abs_wxdir = abspath(WXDIR)

    os.environ.update(
        WXWIN = abspath(WXDIR),
        WXDIR = abspath(WXDIR),
        #CAIRO_ROOT = abspath(pathjoin(WXDIR, 'external', 'cairo-dev')),
    )

    copy_setup_h()
    check_bakefile()

    msw_makefile = pathjoin(WXDIR, 'build', 'msw', 'makefile.vc')

    do_bakefile = False
    if force_bakefile:
        inform('forcing bakefile_gen')
        do_bakefile = True
    elif not isfile(msw_makefile):
        inform('makefile.vc missing, running bakefile')
        do_bakefile = True

    if do_bakefile:
        bakefile()
        assert isfile(msw_makefile), "running bakefile_gen did not create %s" % msw_makefile

    make_cmd = ['nmake', '-f', 'makefile.vc'] + stropts(WX_MAKEFILE_ARGS)

    # build WX main libraries
    with cd(WXDIR, 'build', 'msw'):
        run(make_cmd)

    # build contribs
    if CONTRIB['STC']:
        with cd(WXDIR, 'contrib', 'build', 'stc'):
            run(make_cmd)

    inform('wxWidgets built successfully in %s' % abspath(WXDIR))

    # install
    from buildutil import copy_different, DEPS_DIR

    bindir = pathjoin(abspath(WXDIR), 'lib', 'vc_dll')

    for dll in ('base28%s_net_vc base28%s_vc msw28%s_adv_vc '
                'msw28%s_core_vc msw28%s_stc_vc').split():

        dll = dll % ('u' + WX_MAKEFILE_ARGS['WXDEBUGFLAG'])
        for ext in ('.dll', '.pdb'):
            src, dest = pathjoin(bindir, 'wx' + dll + ext), DEPS_DIR
            copy_different(src, dest)

def check_swig():
    'Checks for the correct version of SWIG.'

    try:
        run(['swig', '-version'], checkret = False)
    except Exception:
        fatal(SWIG_MSG)

    if not 'SWIG_LIB' in os.environ:
        fatal("ERROR: no SWIG_LIB\n"
              "please set SWIG_LIB in your environment to the Lib folder "
              "underneath Swig's installation folder")

def check_bakefile():
    'Checks for bakefile on PATH.'

    try:
        run(['bakefile', '--version'])
    except Exception:
        fatal('bakefile is not on PATH: please fix, or download and install from http://www.bakefile.org/download.html')

def fix_newlines(filename):
    "Makes a file's newlines UNIX style."

    with open(filename, 'rb') as f:
        s = f.read()

    s = s.replace('\r\n', '\n').replace('\r', '\n')

    with open(filename, 'wb') as f:
        f.write(s)

def stropts(opts):
    elems = []
    for k, v in opts.iteritems():
        if isinstance(v, (list, tuple)):
            v = '%s' % (' '.join('%s' % e for e in v))

        elems.append('%s=%s' % (k, v))

    return elems

def clean():
    if os.name == 'nt':
        def rmdir(p):
            p = os.path.abspath(p)
            if os.path.isdir(p):
                run(['cmd', '/c', 'rmdir', '/s', '/q', p], checkret=False)

        with cd(WXDIR, 'lib'):
            rmdir('vc_dll')

        # TODO: don't hardcode this debug flag
        dir = 'vc_mswu%sdll' % WX_MAKEFILE_ARGS['WXDEBUGFLAG']

        with cd(WXDIR, 'build', 'msw'):
            rmdir(dir)

        with cd(WXDIR, 'contrib', 'build', 'stc'):
            rmdir(dir)
    else:
        raise AssertionError('clean not implemented for %s' % os.name)

def all(force_bakefile = False):
    if not isdir(WXDIR):
        checkout()

    update()
    build(force_bakefile)

def main():
    force_bakefile = False
    if '--force-bakefile' in sys.argv:
        sys.argv.remove('--force-bakefile')
        force_bakefile = True

    funcs = dict(clean = clean,
                 rebuild = lambda: (clean(), build(force_bakefile)),
                 checkout = checkout,
                 update = update,
                 build = build,
                 all = lambda: all(force_bakefile))


    if not len(sys.argv) == 2 or sys.argv[1] not in funcs:
        print >> sys.stderr, 'python build_wx.py [--DEBUG] [--force-bakefile] [checkout|update|build|rebuild|all|clean]'
        return 1

    funcname = sys.argv[1]

    with timed(funcname):
        funcs[funcname]()

if __name__ == '__main__':
    from traceback import print_exc
    try: sys.exit(main())
    except SystemExit: raise
    except: print_exc(); sys.exit(1)
