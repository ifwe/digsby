#!/usr/bin/env python
#__LICENSE_GOES_HERE__

'''

builds the following external dependencies for Digsby:
 - libxml2 (with Python bindings
 - PySyck
 - PIL (http://www.pythonware.com/products/pil/)
   - TODO: lacking JPEG and TrueType support
 - M2Crypto

all binaries go into DEPS_DIR, defined below

'''

from __future__ import with_statement

import os
import sys
from distutils.sysconfig import get_python_lib

compiledeps_dir = os.path.dirname(os.path.abspath(__file__))

deps = 'libxml2 m2crypto syck pil'.split()

usage = '''\
compile_deps.py

Downloads, builds, and installs dependencies for Digsby.

 $ python compile_deps.py all      builds all libraries
 $ python compile_deps.py libxml2  builds just libxml2

Available libraries are:
%s
''' % '\n'.join('  ' + dep for dep in deps)

from os.path import exists, join as pathjoin, abspath, isdir, split as pathsplit
from buildutil import *
from constants import MINI_LOCAL, MINI_HTTP
MINI_LOCAL = None
MINI_HTTP = None

def inform(text):
    print text

patch_cmd = get_patch_cmd()

if not os.path.exists(DEPS_DIR):
    os.makedirs(DEPS_DIR)

# Point PYTHONPATH here so that we can test libraries after
# building/installing them here.
sys.path.insert(0, DEPS_DIR)

#
# LIBXML2
#
libxml2_tarball, libxml2_tarball_size = 'libxml2-2.7.7.tar.gz', 4868502
libxml2_url = 'http://xmlsoft.org/sources/' + libxml2_tarball
libxml2_dirname = libxml2_tarball.replace('.tar.gz', '')
libxml2_setup_py_patch = abspath('./libxml2.setup.py.patch')

libxslt = tardep('http://xmlsoft.org/sources/', 'libxslt-1.1.24', '.tar.gz', 3363961)


#
# LXML
#
lxml = tardep('http://pypi.python.org/packages/source/l/lxml/', 'lxml-2.2', '.tar.gz', 2931993,
              md5 = 'b3f12344291aa0d393915e7d8358b480')

#
# PyObjC
#
pyobjc = tardep('http://pypi.python.org/packages/source/p/pyobjc/', 'pyobjc-2.2b2', '.tar.gz', 6231,
              md5 = '9613a79b3d883e26f92b310604568e1f')

#
# SYCK
#
syck_tarball, syck_tarball_size = 'syck-0.61+svn231+patches.tar.gz', 311647
syck_url = 'http://pyyaml.org/download/pysyck/' + syck_tarball
syck_dirname = syck_tarball.replace('.tar.gz', '')

pysyck_tarball, pysyck_tarball_size = 'PySyck-0.61.2.tar.gz', 44949
pysyck_url = 'http://pyyaml.org/download/pysyck/' + pysyck_tarball
pysyck_dirname = pysyck_tarball.replace('.tar.gz', '')
pysyck_cfg = '''\
[build_ext]
include_dirs=%s/include
library_dirs=%s/lib
''' % (DEPS_DIR, DEPS_DIR)

#
# PIL
#
pil_tarball, pil_tarball_size = 'Imaging-1.1.6.tar.gz', 435854
pil_url = 'http://effbot.org/media/downloads/' + pil_tarball
pil_dirname = pil_tarball.replace('.tar.gz', '')

freetype_tar = tardep('http://voxel.dl.sourceforge.net/sourceforge/freetype/',
                     'freetype-2.3.7', '.tar.gz', 1781554)
freetype_win_lib = 'freetype237MT.lib' if not DEBUG else 'freetype237MT_D.lib'

#
# M2CRYPTO
#
if MINI_LOCAL:
    m2crypto_svn_base = '%s/svn/m2crypto-mirror/' % MINI_HTTP
else:
    m2crypto_svn_base = 'http://svn.osafoundation.org/m2crypto/'
m2crypto_svn_url = m2crypto_svn_base + 'tags/0.19.1/'
m2crypto_dir = 'm2crypto'

#
# LIBJPEG
#

libjpeg_tarball, libjpeg_size= 'jpegsrc.v6b.tar.gz', 613261
libjpeg_url= 'http://wxwebkit.wxcommunity.com/downloads/deps/' + libjpeg_tarball
libjpeg_dirname = 'jpeg-6b'


#
# Mac OS X SDK flags support
#

sdk = '/Developer/SDKs/MacOSX10.5.sdk'
sdkflags = "-isysroot %s -arch i386 -arch ppc" % sdk
sdkcflags = sdkflags + " -I" + sdk + "/usr/include" # for Python since it overrides its own sdk setting...
sdkldflags = sdkflags + " -L" + sdk + "/usr/lib -Wl,-search_paths_first" # ditto
makeflags = []
configureflags = []

if sys.platform.startswith('darwin'):
    configureflags= ['--disable-dependency-tracking']
    makeflags = ["CFLAGS=%s" % sdkflags, "LDFLAGS=%s" % sdkflags]

def download_libxml2():
    if not isdir(libxml2_dirname):
        wget_cached(libxml2_tarball, libxml2_tarball_size, libxml2_url)
        untar(libxml2_tarball)
    return libxml2_dirname

def build_libxml2_mac():
    banner('libxml2')

    #
    # NOTE: mac only--this links against the system libxml2
    #
    if not os.path.exists('libxml2-2.6.16'):
        run('curl -O ftp://ftp.gnome.org/pub/GNOME/sources/libxml2/2.6/libxml2-2.6.16.tar.gz'.split())
        run('tar xvfz libxml2-2.6.16.tar.gz'.split())

    with cd('libxml2-2.6.16/python'):
        dpy('setup.py build'.split())
        dpy(['setup.py', 'install', '--install-lib', DEPS_DIR])

    if not os.path.exists(lxml.dirname):
        lxml.get()
    if not os.path.exists(libxslt.dirname):
        libxslt.get()
    # LXML needs newer versions than what are provided by the OS, but since we have some low-level
    # components that rely on the OS version, we need to statically link libxml2 here so as not
    # to have conflicts loading two different versions of libxml which are not compatible.
    with cd(lxml.dirname):
        dpy(['setup.py', 'install',
             '--install-lib', DEPS_DIR,
             'build', '--static-deps', '--libxml2-version=2.7.3', '--libxslt-version=1.1.24'],
             platlib=True)


def build_libxml2():
    download_libxml2()

    with cd(libxml2_dirname):
        # build libxml2

        # TODO: disable unneeded libxml2 features--right now disabling
        # things appears to confuse the Python bindings.
        #disabled_features = 'ftp http docbook valid'.split()
        #config_args = ' '.join('--without-%s' % feature for feature in disabled_features)

        if os.name == 'nt':
            return
        else:
            run(['./configure',
                 '--prefix=%s' % DEPS_DIR,
                 '--exec-prefix=%s' % DEPS_DIR,
                 ] +
                 configureflags)
            run(['make'] + makeflags)
            run(['make', 'install'])
            #run('rm -rf %s/share %s/bin %/include' % (3*(DEPS_DIR,)))

        with cd('python'):
            # make sure libxml2's setup.py finds the headers for the libxml2
            # we just downloaded and built.

            # t is for "batch" and means don't return an error if the patch
            # has already been applied

            os.system(r'%s -p0 -N -i %s/../libxml2-rootfirst.patch' % (patch_cmd, DEPS_DIR))

            # run('bash -c "patch -t -p0 setup.py < %s"' % libxml2_setup_py_patch)

            dpy(['setup.py', 'install', '--install-lib', DEPS_DIR])
    if not os.path.exists(libxslt.dirname):
        libxslt.get()
    with cd(libxslt.dirname):

        run(['./configure',
             '--prefix=%s' % DEPS_DIR,
             '--exec-prefix=%s' % DEPS_DIR,
             '--with-libxml-prefix=%s' % DEPS_DIR] + configureflags)
        run(['make'] + makeflags)
        run(['make', 'install'])
    with cd(lxml.dirname):
        dpy(['setup.py'
             'install', '--install-lib', DEPS_DIR,
             '--with-xml2-config=%s/bin/xml2-config' % DEPS_DIR,
             '--with-xslt-config=%s/bin/xslt-config' % DEPS_DIR,
             ])

def fix_symlinks(openssl_dir):
    with cd(openssl_dir, 'include', 'openssl'):
        for header in locate('*.h'):
            with open(header, 'r') as f:
                text = f.read()

            if text.startswith('link '):
                target = text[5:]

                print 'fixing symlink in %s to %s' % (header, target)
                with open(target, 'r') as target_file:
                    with open(header, 'w') as f:
                        f.write(target_file.read())

def build_m2crypto():
    banner('M2Crypto')

    if not exists(m2crypto_dir):
        run(['svn', 'co', m2crypto_svn_url, m2crypto_dir])

        with cd(m2crypto_dir):
            from buildutil import common
            run([patch_cmd, '-p0', '-i', os.path.join(compiledeps_dir, 'm2crypto-ssl-wanterrors-zero-return.diff')])

    if os.name == 'nt':
        openssl = abspath(r'C:\OpenSSL-Win32')
        assert exists(openssl), 'cannot find openssl'

        # svn puts "link PATH" for symlinks...
        fix_symlinks(openssl)

        # copy a fixed setup.py
        from buildutil import copy_different
        dbg_ext = '.debug' if DEBUG else ''
        copy_different(pathjoin('msw', 'm2crypto.setup.py.msvc2008' + dbg_ext), pathjoin(m2crypto_dir, 'setup.py'))

    with cd(m2crypto_dir):
        # Fix M2Crypto so that it doesn't monkeypatch urllib.
        # do it before running setup.py because that creates an egg now
        # so it's a lot easier to patch before it's eggified
        f = os.path.join('M2Crypto', 'm2urllib.py')
        assert os.path.isfile(f), f

        lines = []
        with open(f) as infile:
            for line in infile.readlines():
                if line == 'URLopener.open_https = open_https\n':
                    line = '# ' + line
                lines.append(line)

        with open(f, 'w') as out:
            out.writelines(lines)

        if os.name == 'nt':
            libdirs  = pathjoin(openssl, 'lib')
            debug_build_flag = ['--debug'] if DEBUG else []
            dpy(['setup.py', 'build_ext', '-o', openssl, '-L' + libdirs] + debug_build_flag)

            dpy(['setup.py', 'install', '--install-lib', get_python_lib()])
        else:
            if sys.platform.startswith('darwin'):
                os.environ['CFLAGS'] = sdkcflags
                os.environ['LDFLAGS'] = sdkldflags
            dpy(['setup.py', '--verbose', 'build_ext', 'install',
                '-O2', '--install-lib', DEPS_DIR], platlib=True)

            if sys.platform.startswith('darwin'):
                os.environ['CFLAGS'] = ''
                os.environ['LDFLAGS'] = ''

if False and os.name == 'nt':
    # prebuilt PySyck for MSVC2008
    def build_syck():
        from buildutil import wget_cached, unzip
        with cd(DEPS_DIR):
            dbgpostfix = '_d' if DEBUG else ''
            zip = 'pysyck_msvc2008_%s%s.zip' % (sys.version[:3].replace('.', ''), dbgpostfix)

            wget_cached(zip, 42443, 'http://symbolsystem.nfshost.com/build/msvc2008/' + zip)
            unzip(zip)
#            os.remove(zip)
else:
    def build_syck():
        banner('syck')

        if not isdir(syck_dirname):
            wget_cached(syck_tarball, syck_tarball_size, syck_url)
            untar(syck_tarball)

        with cd(syck_dirname):
            global sdkflags
            sdkflags_syck = ""
            if sys.platform.startswith('darwin'):
                sdkflags_syck = sdkflags
            makeflags = ["CFLAGS=%s" % sdkflags_syck,
                         "LDFLAGS=%s -L%s/lib" % (sdkflags_syck, os.path.abspath('.'))]

            run(['./configure',
                 '--prefix=%s' % DEPS_DIR,
                 '--exec-prefix=%s' % DEPS_DIR] +
                 configureflags)
            run(['make'] + makeflags)
            run(['make', 'install'])

        banner('pysyck')

        if not isdir(pysyck_dirname):
            wget_cached(pysyck_tarball, pysyck_tarball_size, pysyck_url)
            untar(pysyck_tarball)

        with cd(pysyck_dirname):
            # write out a small .cfg file to tell PySyck's setup.py where to
            # find syck includes and libraries
            with open('setup.cfg', 'w') as setup_cfg:
                setup_cfg.write(pysyck_cfg)
            dpy(['setup.py', 'install', '--install-lib', DEPS_DIR])

def build_pil():
    banner('PIL')

    if not isdir(pil_dirname):
        wget_cached(pil_tarball, pil_tarball_size, pil_url)
        untar(pil_tarball)

    jpeg = libjpeg_dirname
    zlib = '/usr/lib'
    freetype = None

    if sys.platform == 'darwin':
        freetype = '/Developer/SDKs/MacOSX10.5.sdk/usr/X11R6'
        if not isdir(libjpeg_dirname):
            wget_cached(libjpeg_tarball, libjpeg_size, libjpeg_url)
            untar(libjpeg_tarball)

            with cd(libjpeg_dirname):
                bindir = os.path.join(DEPS_DIR, "bin")
                if not os.path.exists(bindir):
                    os.makedirs(bindir)
                mandir = os.path.join(DEPS_DIR, "man", "man1")
                if not os.path.exists(mandir):
                    os.makedirs(mandir)
                run(['./configure',
                     '--prefix=%s' % DEPS_DIR,
                     '--exec-prefix=%s' % DEPS_DIR,
                     ] +
                     configureflags)
                run(['make'] + makeflags)
                run(['make', 'install'])

            jpeg = abspath(libjpeg_dirname)
        assert jpeg and isdir(jpeg)
    elif sys.platform == 'win32':
        jpeg = abspath(pathjoin('msw', 'jpeg-7'))
        zlib = abspath(pathjoin('msw', 'zlib-1.2.3'))
        freetype = build_freetype_msw()

        assert isdir(jpeg), jpeg
        assert isdir(zlib), zlib
        assert all(isdir(d) for d in freetype), freetype
    else:
        jpeg = None

    with cd(pil_dirname):
        if jpeg is not None:
            filerepl('setup.py', 'JPEG_ROOT = None', 'JPEG_ROOT = %r' % jpeg)
        if zlib is not None:
            filerepl('setup.py',
                     'elif sys.platform == "win32" and find_library_file(self, "zlib"):',
                     'elif sys.platform == "win32" and find_library_file(self, "zlib1"):')
            filerepl('setup.py',
                     '    feature.zlib = "zlib" # alternative name',
                     '    feature.zlib = "zlib1" # alternative name')
            filerepl('setup.py', 'ZLIB_ROOT = None', 'ZLIB_ROOT = %r' % zlib)
        if freetype is not None:
            if isinstance(freetype, type(())):
                filerepl('setup.py', 'FREETYPE_ROOT = None', 'FREETYPE_ROOT = %r' % (freetype,))
            else:
                filerepl('setup.py', 'FREETYPE_ROOT = None', 'FREETYPE_ROOT = libinclude(%r)' % (freetype,))

        dpy(['setup.py', 'clean'])

        debug_flag = ' --debug' if DEBUG else ''

        # TODO: is there a way to pass --debug to "build" other than through setup.cfg
        # and still have install work correctly?
        with open('setup.cfg', 'w') as f: f.write('[build]\ndebug=%d' % DEBUG)

        dpy(['setup.py', 'install', '--install-lib', DEPS_DIR, '--install-scripts', '.'])

def build_freetype_msw():
    # get/build freetype
    with cd('msw'):
        ftype_dir = freetype_tar.get()
        with cd(ftype_dir, 'builds', 'win32', 'visualc'):

            # use /upgrade to upgrade old VC6 build scripts
            with open('freetype.dsw') as f:
                needs_upgrade = 'Format Version 6.00' in f.read()

            run(['vcbuild',
                 '/nologo', '/time'] +
                 (['/upgrade'] if needs_upgrade else []) +
                 ['freetype.sln', '%s Multithreaded|Win32' % ('Debug' if DEBUG else 'Release')]
                 )

        with cd(ftype_dir, 'objs'):
            # copy the lib to a name PIL is looking for
            from buildutil import copy_different
            copy_different(freetype_win_lib, 'freetype.lib')

        freetype = (abspath(pathjoin(ftype_dir, 'objs')),
                    abspath(pathjoin(ftype_dir, 'include')))

    return freetype

def build_pyobjc():
    banner('PyObjC')

    try:
        import objc
    except:
        pyobjc.get()

        with cd(pyobjc.dirname):
            run(['python', 'setup.py', 'install'])

def install_deps():
    # strip off the script name
    argv = sys.argv
    if argv[0] == globals()['__file__']:
        argv = argv[1:]

    startdir = os.getcwd()
    if not sys.platform.startswith('win'):
        depsDir = os.path.join(homeDir, "digsby-deps", "py" + sys.version[:3])
        if not os.path.exists(depsDir):
            os.makedirs(depsDir)
        os.chdir(depsDir)

    if not argv:
        print usage
        return 0

    if 'all' in argv:
        argv = deps

    invalid = set(argv) - set(deps)
    if invalid:
        print >> sys.stderr, 'invalid arguments:', ', '.join(a for a in argv if a in invalid)
        return 1

    for dep in argv: globals()['build_' + dep]()

    os.chdir(startdir)

def banner(txt):
    print '\n' + '\n'.join(['*' * 80, ' ' + txt, '*' * 80])

if __name__ == '__main__':
    original_working_dir = os.getcwd()
    try:
        sys.exit(install_deps())
    finally:
        os.chdir(original_working_dir)
