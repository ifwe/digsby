#__LICENSE_GOES_HERE__
'''

builds webkit (and dependencies)

'''

from __future__ import with_statement

import sys
if __name__ == '__main__':
    try:
        cfg = sys.argv.pop(1)
    except IndexError:
        cfg = 'release'

    if cfg not in ('release', 'debug', 'curl'):
        print >> sys.stderr, 'Usage: python build_webkit.py release|debug [OPTS]'
        sys.exit(1)

    if cfg == 'debug':
        sys._build_debug = True



import shutil
import os
sys.path.append('..') if '..' not in sys.path else None
from buildutil import run, cd, tardep, unzip, filerepl, git, inform, timed, DEBUG, copy_different, DEPS_DIR, get_patch_cmd
from os import makedirs, environ
from os.path import isdir, abspath, exists, join as pathjoin, isfile
from constants import TARBALL_URL, WXWEBKIT_GIT_REPO
from shutil import move

thisdir = abspath(os.path.dirname(__file__))

zlib = tardep('http://symbolsystem.com/build/msvc2008/', 'zlib-1.2.3', '.zip', 629830)

patch_cmd = get_patch_cmd()

icu = tardep('http://download.icu-project.org/files/icu4c/49.1.2/', 'icu4c-49_1_2-Win32-msvc10', '.zip', 9327628, dirname='icu')

# WARNING: if the cURL version changes, make sure that the accompanying patch file (curl_patch) is updated
curl = tardep('http://curl.haxx.se/download/', 'curl-7.18.1', '.tar.bz2', 1700966)

# this patch hacks cURL to assume all URLS are UTF-8 encoded (which is true when they are coming from webkit,
# our only user of cURL. this fixes problems when accessing file:/// paths on the hard disk under non-english
# locales). applied only for windows.
curl_patch = 'curl_utf8_urls.diff'

jpeg = tardep('http://www.ijg.org/files/', 'jpegsrc.v7', '.tar.gz', 960379, dirname = 'jpeg-7')

WEBKITDIR = 'WebKit'
WEBKIT_GIT_REMOTE = 'mini'
WEBKIT_GIT_REPO = WXWEBKIT_GIT_REPO
WEBKIT_GIT_BRANCH = 'master'

WEBKIT_USE_GC = False # whether or not to use the wxGraphicsContext path

def get_wxdir():
    "WebKit's build scripts need a WXWIN environment variable to find wxWidgets."

    from build_wx import WXDIR
    WXDIR = abspath(WXDIR)
    return WXDIR

    if 'WXWIN' in environ:
        # already set in the enviornment
        inform('WXWIN is %s' % environ['WXWIN'])
        return environ
    else:
        # wasn't already set--use the path set in build_wx.py
        from build_wx import WXDIR
        WXDIR = abspath(WXDIR)
        inform('setting environment variable WXWIN=%s' % WXDIR)
        environ['WXWIN'] = WXDIR

def checkout():
    if isdir(WEBKITDIR):
        inform('skipping checkout, %s already exists' % WEBKITDIR)
    else:
        inform('cloning WebKit')

        makedirs(WEBKITDIR)
        with cd(WEBKITDIR):
            git.run(['init'])

            # turn off auto CRLF conversion, so that cygwin bash
            # doesn't complain about line endings
            git.run(['config', 'core.autocrlf', 'false'])

            # Add our remote source
            git.run(['remote', 'add', WEBKIT_GIT_REMOTE, WEBKIT_GIT_REPO])
            git.run(['fetch', WEBKIT_GIT_REMOTE, '--depth', '1'])

            # checkout a local tracking branch of the remote branch we're interested in
            with timed():
                git.run(['checkout', '-b', WEBKIT_GIT_BRANCH, WEBKIT_GIT_REMOTE + '/' + WEBKIT_GIT_BRANCH])

def update():
    print 'skipping webkit update'
    return

    with cd(WEBKITDIR):
        git.run(['pull', WEBKIT_GIT_REMOTE, WEBKIT_GIT_BRANCH])


def build_zlib():
    copy_different('../../../builddeps/msvc2008/' + zlib.filename, '.')
    unzip(zlib.filename)

    with cd('zlib-1.2.3'):
        lib_dest_path = os.getcwd()
        with cd('projects/visualc9-x86'):
            configname = 'DLL ASM %s' % ('Debug' if DEBUG else 'Release')
            run(['vcbuild', 'zlib.vcproj', configname])

            # install the ZLIB dll and pdb
            print 'DEPS_DIR here', DEPS_DIR
            with cd('Win32/' + configname):
                debug_flag = 'd' if DEBUG else ''

                for dest in (DEPS_DIR, lib_dest_path):
                    copy_different('zlib1%s.dll' % debug_flag, dest)
                    copy_different('zlib1%s.pdb' % debug_flag, dest)
                    copy_different('zlib1%s.lib' % debug_flag, dest)

def build_png():
    pass

def build_jpeg():
    with cd(jpeg.get()):
        # setup for nmake build
        shutil.copy2('jconfig.vc', 'jconfig.h')

        # make sure libjpeg is built against the multithreaded C runtime
        # library.
        run(['nmake', '-f', 'makefile.vc', 'NODEBUG=' + ('0' if DEBUG else '1')])

        lib = abspath('libjpeg.lib')
        assert exists(lib)
        return lib

curl_pfix = 'd' if DEBUG else ''

def build_curl():
    # relies on openssl-0.9.8g being in msw/ (should be there from
    # building Python)

    new = not os.path.exists(curl.dirname)

    with cd(curl.get()):
        if os.name == 'nt' and new:
            # after pulling a fresh tarball, apply the patch pointed to by curl_patch.
            # see the note above for an explanation.
            run([patch_cmd, '-p0', '-i', '../' + curl_patch])

        filerepl('lib/Makefile.vc6',
                 '/O2 /DNDEBUG',
                 '/Zi /Ox /GL /GS- /GR- /DNDEBUG')

        filerepl('lib/Makefile.vc6',
                 'LFLAGS     = /nologo /machine:$(MACHINE)',
                 'LFLAGS     = /DEBUG /nologo /machine:$(MACHINE)')

        openssl_includes = "../../../../../digsby-venv"

        # point at includes
        filerepl('lib/Makefile.vc6',
                 '/DUSE_SSLEAY /I "$(OPENSSL_PATH)/inc32"',
                 '/DUSE_SSLEAY /I "%s/PC" /I "%s/PC/openssl" /I "$(OPENSSL_PATH)/inc32"' % (openssl_includes, openssl_includes))

        # point at .libs
        filerepl('lib/Makefile.vc6',
            'LFLAGSSSL = "/LIBPATH:$(OPENSSL_PATH)\out32dll"',
            'LFLAGSSSL = "/LIBPATH:%s/libs"' % openssl_includes)

        with cd('lib'):
            run(['nmake', '/nologo', '/E', '/f', 'Makefile.vc6', 'cfg=%s-dll-ssl-dll-zlib-dll' % ('debug' if DEBUG else 'release'),
                 'ZLIBLIBSDLL=zlib1%s.lib'  % ('d' if DEBUG else ''),
                 'IMPLIB_NAME=libcurl',
                 'IMPLIB_NAME_DEBUG=libcurld']
            )

            # copy libcurl.dll to digsby/build/msw/dependencies
            from buildutil import copy_different, DEPS_DIR

            copy_different('libcurl%s.dll' % curl_pfix, DEPS_DIR)
            copy_different('libcurl%s.pdb' % curl_pfix, DEPS_DIR)

CYGWIN_PATH = 'c:\\cygwin'

def cygwin(cmd, env=None):
    run([CYGWIN_PATH + '\\bin\\bash', '--login', '-c', cmd], env=env)

def cygfix(path):
    return r'"`cygpath -d \"' + path + r'\"`"'

from contextlib import contextmanager

@contextmanager
def _cygwin_env():
    # cygwin's link.exe and python.exe can get in the way of webkit's build
    # process so move them out of the way temporarily.

    bad_files = [
        '\\bin\\link.exe'
    ]

    badfiles = []
    for f in bad_files:
        badfile = CYGWIN_PATH + f
        if isfile(badfile):
            badfile_moved = badfile + '.webkitbuilding'
            move(badfile, badfile_moved)
            badfiles.append(badfile)

    try:
        yield
    finally:
        for badfile in badfiles:
            move(badfile + '.webkitbuilding', badfile)

def _setup_icu():
    # ICU
    icudir = icu.get()

    # copy icu binaries into DEPS_DIR
    icu_bindir = os.path.join(icudir, 'bin')
    for f in os.listdir(icu_bindir):
        copy_different(os.path.join(icu_bindir, f), DEPS_DIR)

    return icudir

def build_webkit(cfg):
    wxdir = get_wxdir()
    assert isdir(wxdir)
    assert cfg in ('debug', 'release', 'curl')

    webkit_scripts = abspath(WEBKITDIR + '/WebKitTools/Scripts')
    assert isdir(webkit_scripts), "not a directory: " + webkit_scripts

    # passing things through to cygwin will mangle backslashes, so fix them
    # here.
    webkit_scripts = cygfix(webkit_scripts)
    wxdir = cygfix(wxdir)

    libdir = os.path.join(abspath(WEBKITDIR), 'WebKitLibraries/msvc2008/win/lib')
    incdir = os.path.join(abspath(WEBKITDIR), 'WebKitLibraries/msvc2008/win/include')

    icudir = _setup_icu()

    os.environ['WEBKIT_ICU_REPLACEMENT'] = os.path.join(thisdir, icudir)
    os.environ['WEBKIT_CURL_REPLACEMENT'] = abspath(os.path.join(curl.dirname, 'lib', 'libcurl%s.lib' % curl_pfix))
    os.environ['WEBKIT_JPEG_REPLACEMENT'] = abspath(os.path.join(jpeg.dirname))

    with _cygwin_env():
        cygwin('cd %s && ./set-webkit-configuration --%s' % (webkit_scripts, cfg))

        cygprefix = 'cd %s && PATH="%s:$PATH" WXWIN=%s' % (webkit_scripts, '/cygdrive/c/python26', wxdir)

        wkopts = 'wxgc' if WEBKIT_USE_GC else ''

        with timed('building webkit'):
            build_scripts_py = os.path.join(abspath(WEBKITDIR), 'WebKitTools/wx/build')
            assert os.path.isdir(build_scripts_py), build_scripts_py
            env=dict(os.environ)
            env.update(PYTHONPATH=cygfix(build_scripts_py), PATH=';'.join([r'c:\python26',os.environ['PATH']]))

            def run_cygwin(s):
                cygwin(cygprefix + ' ' + s + (' --wx %s' % wkopts), env=env)

            if '--test' in sys.argv:
                run_cygwin('./run-webkit-tests --wx')
            elif '--clean' in sys.argv:
                run_cygwin('./build-webkit --wx --clean')
            else:
                run_cygwin('./build-webkit --wx wxpython')


def install(cfg):
    'Installs all necessary binaries.'

    if False:
        copy_different('openssl-0.9.8g/out32dll/libeay32.dll', DEPS_DIR)
        copy_different('openssl-0.9.8g/out32dll/ssleay32.dll', DEPS_DIR)

    bindir = pathjoin(WEBKITDIR, 'WebKitBuild', 'Release' if cfg == 'release' else 'Debug')

    for dll in 'wxwebkit'.split():
        for ext in ('.pdb', '.dll'):
            src, dest = pathjoin(bindir, dll + ext), DEPS_DIR
            if ext == '.pdb' and not isfile(src):
                continue
            copy_different(src, dest)

    copy_different(pathjoin(WEBKITDIR, 'WebKitLibraries/win/lib', 'pthreadVC2.dll'), DEPS_DIR)

    print 'wxwebkit.dll is %.2fMB' % (os.path.getsize(pathjoin(bindir, 'wxwebkit.dll')) / 1024.0 / 1024.0)


def build(cfg):
    if not isdir(WEBKITDIR):
        checkout()
    update()

    if cfg == 'curl':
        build_curl()
    else:
        build_zlib()
        build_curl()
        build_jpeg()
        build_webkit(cfg)
        if not '--clean' in sys.argv:
            install(cfg)

def main():
    build(cfg)

if __name__ == '__main__':
    main()
