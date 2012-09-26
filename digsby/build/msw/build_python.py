#__LICENSE_GOES_HERE__
'''
downloads, builds, and tests Python
'''
from __future__ import with_statement

USAGE_MSG = 'usage: python build_python.py [all] [build] [rebuild] [test] [copylib] [checkout]'

USE_PYTHON_26 = True

import os
from os.path import exists, join as pathjoin, abspath, normpath, split as pathsplit

# if True, try to build _ssl.pyd against OpenSSL dynamically instead
# of statically, so that we don't have duplicate code (webkit uses openssl too)
USE_OPENSSL_DLL = True

def is_vsexpress():
    try:
        vsinstalldir = os.environ['vsinstalldir']
    except KeyError:
        raise AssertionError('You must run build scripts from the Visual Studio command prompt.')

    # If we have devenv.exe, then it is VS pro
    devenv = os.path.join(vsinstalldir, 'common7', 'ide', 'devenv.exe')
    return not os.path.isfile(devenv)

VS_EXPRESS = is_vsexpress()

import sys
if not '..' in sys.path: sys.path.append('..') # for buildutil
from traceback import print_exc

# where to place Python sources
PYTHON_DIR     = 'python'

# where to get Python sources:

from buildutil import DEBUG, get_patch_cmd
from constants import PYTHON_PROJECTS_SVN

DEBUG_POSTFIX = '_d' if DEBUG else ''

USE_DEVENV = not VS_EXPRESS # devenv.exe does not come with the free compiler



makepath = lambda *p: normpath(pathjoin(abspath(p[0]), *p[1:]))

if USE_PYTHON_26:
    #
    # Python 2.6 Trunk
    #
    PYTHON_SVN_REVISION = '72606'
    PYTHON_SVN_URL = '%s/python/branches/release26-maint@%s' % (PYTHON_PROJECTS_SVN, PYTHON_SVN_REVISION)
    PCBUILD_DIR = 'PCBuild'
    PYTHON_LIBDIR  =  normpath(pathjoin(abspath(pathsplit(__file__)[0]), PYTHON_DIR, PCBUILD_DIR))
    PYTHON_PGO_DIR = 'Win32-pgo'
    PYTHON_PGI_LIBDIR  =  normpath(pathjoin(abspath(pathsplit(__file__)[0]), PYTHON_DIR, PCBUILD_DIR, 'Win32-pgi'))
    PYTHON_PGO_LIBDIR  =  normpath(pathjoin(abspath(pathsplit(__file__)[0]), PYTHON_DIR, PCBUILD_DIR, PYTHON_PGO_DIR))
    PYTHON_EXE     =  normpath(pathjoin(PYTHON_LIBDIR, r'python%s.exe' % DEBUG_POSTFIX))
    PYTHON_EXE_PGI =  normpath(pathjoin(PYTHON_PGI_LIBDIR, r'python.exe'))
    PYTHON_EXE_PGO =  normpath(pathjoin(PYTHON_PGO_LIBDIR, r'python.exe'))
    PYTHON_VER = '26'
    PYTHON_BZIP = ('bzip2-1.0.5', '%s/external/bzip2-1.0.5' % PYTHON_PROJECTS_SVN)
    PYTHON_SQLITE = ('sqlite-3.5.9', '%s/external/sqlite-3.5.9/' % PYTHON_PROJECTS_SVN)
else:
    #
    # Python 2.5 Maintenance Branch
    #
    PYTHON_SVN_REVISION = 'HEAD'
    PYTHON_SVN_URL = '%s/python/branches/release25-maint@%s' % (PYTHON_PROJECTS_SVN, PYTHON_SVN_REVISION)
    PCBUILD_DIR    = 'PCBuild'
    PYTHON_LIBDIR  =  normpath(pathjoin(abspath(pathsplit(__file__)[0]), PYTHON_DIR, PCBUILD_DIR))
    PYTHON_EXE     =  normpath(pathjoin(PYTHON_LIBDIR, r'python%s.exe' % DEBUG_POSTFIX))
    PYTHON_VER = '25'
    PYTHON_BZIP = ('bzip2-1.0.3', '%s/external/bzip2-1.0.3' % PYTHON_PROJECTS_SVN)

print
print 'PYTHON_EXE', PYTHON_EXE
print 'DEBUG     ', DEBUG
print

from buildutil import run, cd, inform, fatal, filerepl, which

def svn_version(path = '.'):
    'Returns the current revision for a given working copy directory.'

    v = run(['svnversion', '.'], capture_stdout = True)
    if v.endswith('M'): v = v[:-1]
    return int(v)

def checkout():
    'Checks out Python source.'

    run(['svn', 'co', PYTHON_SVN_URL, PYTHON_DIR])

    patch_cmd = get_patch_cmd()

    def banner_msg(s):
        print
        print s
        print

    def apply_patch(patchfile, strip_prefixes=0):
        assert os.path.isfile(patchfile)
        run([patch_cmd, '-p%d' % strip_prefixes, '-i', patchfile])

    with cd(PYTHON_DIR):
        if sys.opts.use_computed_goto:
            banner_msg('applying computed goto patch')
            apply_patch('../python26-computed-goto.patch')

        banner_msg('applying assert mode patch')
        # this patch restores c assert()s and is made with
        # svn diff http://svn.python.org/projects/python/trunk@69494 http://svn.python.org/projects/python/trunk@69495
        apply_patch('../python26-assert-mode.patch')

        banner_msg('applying file object close bug patch')
        # http://bugs.python.org/issue7079 -- remove once we update to a newer version of 2.6
        apply_patch('../python26-file-object-close-7079.patch')

        if USE_DEVENV and sys.opts.intel:
            banner_msg('applying intel project patch')
            apply_patch('../vs2008+intel.patch', 3)

        banner_msg('applying common controls patch')
        apply_patch('../python-common-controls.patch')


def update():
    'Updates the Python source tree.'

    with cd(PYTHON_DIR):
        if PYTHON_SVN_REVISION == 'HEAD' or svn_version('.') != int(PYTHON_SVN_REVISION):
            inform('updating python')
            run(['svn', 'update', '-r', PYTHON_SVN_REVISION])
            return True
        else:
            return False

def get_deps():
    '''
    Gets external dependencies needed to build Python.

    (From http://svn.python.org/view/python/branches/release25-maint/Tools/buildbot/external.bat?rev=51340&view=markup)

    intentionally missing:
     - tcl/tk
     - Sleepycat db
    '''

    import shutil
    bzip_dir, bzip_checkout = PYTHON_BZIP

    if not exists(bzip_dir):
        run(['svn', 'export', bzip_checkout])
    else:
        inform(bzip_dir + ': already exists')

    sqlite_dir, sqlite_checkout = PYTHON_SQLITE

    if not exists(sqlite_dir):
        run(['svn', 'export', sqlite_checkout])
    else:
        inform(bzip_dir + ': already exists')

    makefile = os.path.join(bzip_dir, 'makefile.msc')
    debug_makefile = os.path.join(bzip_dir, 'makefile.debug.msc')
    release_makefile = os.path.join(bzip_dir, 'makefile.release.msc')

    if not os.path.isfile(debug_makefile):
        shutil.copy2(makefile, release_makefile)

        with open(makefile, 'r') as f: lines = f.readlines()

        with open(debug_makefile, 'w') as f:
            for line in lines:
                if line.strip() == 'CFLAGS= -DWIN32 -MD -Ox -D_FILE_OFFSET_BITS=64 -nologo':
                    line = 'CFLAGS= -DWIN32 -MDd -Od -D_FILE_OFFSET_BITS=64 -nologo -Zi\n'
                f.write(line)

    assert os.path.isfile(release_makefile)
    assert os.path.isfile(debug_makefile)

    src = release_makefile if not DEBUG else debug_makefile
    dest = makefile

    shutil.copy2(src, dest)

    if not exists('openssl-0.9.8g'):
        run(['svn', 'export', 'http://svn.python.org/projects/external/openssl-0.9.8g'])
    else:
        inform('openssl-0.9.8g: already exists')
    os.environ['PATH'] = os.pathsep.join([os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), 'openssl-0.9.8g'))), os.environ['PATH']])

def check_tools():

    # perl - required for _ssl module
    try:
        run(['perl', '--version'])
    except Exception:
        fatal('Missing perl!\nPlease install ActiveState Perl from '
              'http://www.activestate.com/Products/activeperl/')

    # nasm - required for _ssl module
    try:
        run(['nasmw', '-version'])
    except Exception:
        fatal('Missing NASM.\nPlease place binaries from '
              'http://www.nasm.us/ '
              'on your PATH. (copy nasm.exe to nasmw.exe)')


def fix_build_ssl_py():
    # Python's build files aren't quite up to linking against OpenSSL
    # dynamically, but a few string substitutions are enough to do the
    # trick.

    dllbin, staticbin = '$(opensslDir)\\out32dll\\', '$(opensslDir)\\out32\\'

    hashlib = '_hashlib.vcproj'

    build_repl  = lambda *a: filerepl('build_ssl.py', *a)
    vcproj_repl = lambda *a: filerepl('_ssl.vcproj', *a)

    if USE_OPENSSL_DLL:
        build_repl('nt.mak', 'ntdll.mak')
        vcproj_repl(staticbin, dllbin)

        if os.path.isfile(hashlib):
            filerepl(hashlib, staticbin, dllbin)
    else:
        build_repl('ntdll.mak', 'nt.mak')
        vcproj_repl(dllbin, staticbin)
        if os.path.isfile(hashlib): # 2.6
            filerepl(hashlib, dllbin, staticbin)

    conf_flags = ['VC-WIN32']
    # fix idea compilation problems
    conf_flags.append('disable-idea')
    conf_flags.extend(['no-idea', 'no-mdc2', 'no-rc5'])

    build_repl('configure = "VC-WIN32"', 'configure = "%s"' % ' '.join(conf_flags))
    build_repl('if not os.path.isfile(makefile) or os.path.getsize(makefile)==0:', 'if True:')

    if PYTHON_VER == '25':
        from buildutil import copy_different
        copy_different('../../_ssl.mak.25.2008', '_ssl.mak')
    else:
        print >> sys.stderr, 'WARNING: _ssl.pyd will be built without debugging symbols'

def clean():
    with cd(PYTHON_DIR, PCBUILD_DIR):
        config = 'Debug' if DEBUG else 'Release'
        if USE_DEVENV:
            run(['devenv', 'pcbuild.sln', '/clean', "%s|Win32" % config, '/project', '_ssl'], checkret = False)
            run(['devenv', 'pcbuild.sln', '/clean', "%s|Win32" % config], checkret = False)
        else:
            run(['vcbuild', 'pcbuild.sln', '/clean', '%s|Win32' % config], checkret = False)

def build():
    check_tools()
    with cd(PYTHON_DIR, PCBUILD_DIR):

        # fix up files for SSL stuff
        fix_build_ssl_py()

        config = 'Debug' if DEBUG else 'Release'
        if USE_DEVENV:
            run(['devenv', 'pcbuild.sln', '/build', "%s|Win32" % config, '/project', '_ssl'], checkret = False)
            run(['devenv', 'pcbuild.sln', '/build', "%s|Win32" % config], checkret = False)
        else:
            run(['vcbuild', 'pcbuild.sln', '%s|Win32' % config], checkret = False)


def bench(pgo = None):
    if pgo is None:
        pgo = getattr(getattr(sys, 'opts', None), 'pgo', None)
    if not DEBUG and pgo:
        with cd(PYTHON_DIR):
            run([PYTHON_EXE, 'Tools/pybench/pybench.py', '-f', '26.bench.txt'])
            with cd(PCBUILD_DIR):
                run(['devenv', 'pcbuild.sln', '/build', "PGInstrument|Win32", '/project', '_ssl'], checkret = False)
                run(['devenv', 'pcbuild.sln', '/build', "PGInstrument|Win32"], checkret = False)
            run([PYTHON_EXE_PGI, 'Tools/pybench/pybench.py', '-f', '26pgi.bench.txt'])
            with cd(PCBUILD_DIR):
                run(['devenv', 'pcbuild.sln', '/build', "PGUpdate|Win32", '/project', '_ssl'], checkret = False)
                run(['devenv', 'pcbuild.sln', '/build', "PGUpdate|Win32"], checkret = False)
            run([PYTHON_EXE_PGO, 'Tools/pybench/pybench.py', '-f', '26pgo.bench.txt'])


DPYTHON_DIR = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), 'dpython')))

def post_build():
    # copy pyconfig.h from PC/ to /Include and Python26.lib to make scripts
    # using distutils work with our PGO build without modification
    with cd(PYTHON_DIR):
        from buildutil import copy_different
        copy_different('PC/pyconfig.h', 'Include/pyconfig.h')


    install_stdlib()

    with cd(PYTHON_DIR):

        # install python executables
        with cd(PYTHON_LIBDIR):
            pydir = DPYTHON_DIR
            assert os.path.isdir(pydir), pydir

            def copylibs():
                for f in ('''python%(dbg)s.exe python%(dbg)s.pdb
                             pythonw%(dbg)s.exe pythonw%(dbg)s.pdb
                             python%(ver)s%(dbg)s.dll python%(ver)s%(dbg)s.pdb
                             sqlite3%(dbg)s.dll sqlite3%(dbg)s.pdb''' % dict(dbg=DEBUG_POSTFIX,
                                                                                         ver=PYTHON_VER)).split():
                    copy_different(f, pydir)
            if not DEBUG and getattr(getattr(sys, 'opts', None), 'pgo', None):
                with cd(PYTHON_PGO_DIR):
                    copylibs()
            else:
                copylibs()

            dlls_dir = os.path.join(pydir, 'DLLs')
            if not os.path.isdir(dlls_dir):
                os.mkdir(dlls_dir)

            libs = '''_ctypes _elementtree _hashlib _socket _sqlite3
                      _ssl bz2 pyexpat select unicodedata winsound'''.split()

            if int(PYTHON_VER) >= 26:
                libs.append('_multiprocessing')

            for f in libs:
                f += DEBUG_POSTFIX
                copy_different(f + '.pyd', dlls_dir)
                try:
                    copy_different(f + '.pdb', dlls_dir)
                except Exception:
                    print 'WARNING: could not copy %s.pdb' % f

def install_stdlib():
    'Copies all the .py files in python/Lib'

    from buildutil import copy_different

    with cd(PYTHON_DIR):
        exclude = '.xcopy.exclude' # have to specify xcopy excludes in a file

        with open(exclude, 'w') as fout:
            fout.write('\n'.join(['.pyc', '.pyo', '.svn']))

        try:
            run(['xcopy', 'Lib', r'%s\lib' % DPYTHON_DIR, '/EXCLUDE:%s' % exclude, '/I','/E','/D','/Y'])
            run(['xcopy', 'Include', r'%s\Include' % DPYTHON_DIR, '/EXCLUDE:%s' % exclude, '/I','/E','/D','/Y'])
            if not os.path.isdir(r'%s\libs' % DPYTHON_DIR):
                os.makedirs(r'%s\libs' % DPYTHON_DIR)
            for f in os.listdir(r'PCBuild'):
                if f.endswith('.lib'):
                    copy_different(os.path.join('PCBuild', f), os.path.join(r'%s\libs' % DPYTHON_DIR, f))
        finally:
            os.remove(exclude)

def test():
    # check that python is there

    print
    print 'using python', PYTHON_EXE
    print 'current working directory is', os.getcwd()
    print

    try:
        run([PYTHON_EXE, '-c', 'import sys; sys.exit(0)'])
    except Exception:
        print_exc()
        fatal('Error building Python executable')

    # check that we can import ssl
    try:
        run([PYTHON_EXE, '-c', 'import socket; socket.ssl; import sys; sys.exit(0)'])
    except Exception:
        fatal('error building SSL module')

    inform('\nPython built successfully!')

def checkout_or_update():
    if not exists(PYTHON_DIR):
        need_build = True
        checkout()
    else:
        need_build = update()

    return need_build

def main():
    parse_opts()

    usage = True

    if 'all' in sys._args:
        need_build = checkout_or_update()
        get_deps()
        if need_build:
            build()
            bench()

        post_build()
        test()
        return 0

    elif 'build' in sys._args:
        usage = False
        need_build = checkout_or_update()
        get_deps()
        if need_build:
            build()
            bench()
        post_build()

    elif 'rebuild' in sys._args:
        usage = False
        clean()
        checkout_or_update()
        get_deps()
        build()
        bench()
        post_build()

    elif 'test' in sys._args:
        usage = False
        test()
        bench()

    elif 'install' in sys._args:
        usage = False
        post_build()

    elif 'copylib' in sys._args:
        usage = False
        install_stdlib()
    elif 'checkout' in sys._args:
        usage = False
        checkout_or_update()
        get_deps()
    elif 'clean' in sys._args:
        usage = False
        clean()

    if usage:
        print >> sys.stderr, USAGE_MSG
        return 1

    return 0

def parse_opts():
    import optparse
    parser = optparse.OptionParser()

    optimimize_group = optparse.OptionGroup(parser, 'Optimization Options')
    optimimize_group.add_option('--no-computed-goto','--no-computed_goto','--no_computed-goto','--no_computed_goto',
                                help = 'do not apply computed goto',
                                dest = 'use_computed_goto', action='store_false')
    optimimize_group.add_option('--no-intel', '--no_intel', dest = 'intel', action='store_false',
                                help = 'do not attempt use of the intel compiler')
    optimimize_group.add_option('--no-pgo', '--no_pgo', dest = 'pgo', action='store_false',
                                help = 'do not run PGO')

    optimized_build = not VS_EXPRESS
    parser.set_defaults(use_computed_goto = optimized_build,
                        intel = optimized_build,
                        pgo = optimized_build)

    parser.add_option_group(optimimize_group)

    sys.opts, sys._args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main())
