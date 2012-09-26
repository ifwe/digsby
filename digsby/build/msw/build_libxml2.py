#__LICENSE_GOES_HERE__
from __future__ import with_statement

import os
import os.path
import shutil
import sys

sys.path.append('..') if '..' not in sys.path else None
from buildutil import run, fatal, inform, cd, wget_cached, untar, unzip, mkdirs, \
    filerepl, dpy, copy_different, DEBUG, DEBUG_POSTFIX, get_patch_cmd
from os.path import isdir, abspath, join as pathjoin

from compiledeps import libxml2_dirname, download_libxml2, libxslt

iconv_zipfile, iconv_zipfile_size = 'libiconv-1.9.2-1-lib.zip', 731496
iconv_url = 'http://downloads.sourceforge.net/project/gnuwin32/libiconv/1.9.2-1/' + iconv_zipfile
iconv_dirname = iconv_zipfile.replace('.zip', '')

patch_cmd = get_patch_cmd()
lxml_patch = r'..\patches\lxml.patch'
libxml2_patch = r'..\patches\libxml2.patch'

from buildutil import DEPS_DIR

CLEAN = 'clean' in sys.argv

def patch_libxml2_h(*path):
    # msvc 2008 defines _vsnprintf as an intrinsic (or something like that)
    # but libxml2 wants to #define it as something else, and things go
    # boom

    with cd(*path):
        with open('win32config.h') as f:
            lines = [l for l in f if not l.startswith('#define vsnprintf')]

        with open('win32config.h', 'w') as f:
            f.write(''.join(lines))

def build_libxslt():
    'needed by webkit and lxml'

    from compiledeps import libxml2_dirname

    libxmlabs = abspath(libxml2_dirname)
    libxmlinc = pathjoin(libxmlabs, 'include')
    libxmllib = pathjoin(libxmlabs, 'win32', 'bin.msvc')
    iconvinc = pathjoin(abspath(iconv_dirname), 'include')

    libxslt_dir = libxslt.get()
    with cd(libxslt_dir):
        with cd('libxslt'):
            ensure_processonenode_is_public()

        with cd('win32'):
            patch_libxml2_h('..', 'libxslt')
            debug_flag = ['debug=yes'] if DEBUG else []
            run(['cscript', 'configure.js', '//E:JavaScript', 'vcmanifest=yes']
                + debug_flag +
                 ['include=%s' % os.pathsep.join([libxmlinc, iconvinc]),
                 'lib=%s' % libxmllib])

            filerepl('Makefile.msvc', '/O2', '/Os /GL /GS- /Zi')
            filerepl('Makefile.msvc', 'LDFLAGS = /nologo', 'LDFLAGS = /OPT:REF /OPT:ICF /nologo /DEBUG')

            run(['nmake', '-f', 'Makefile.msvc'] + (['clean'] if CLEAN else []))

    return libxslt_dir

def ensure_processonenode_is_public():
    '''
    libxslt doesn't export xsltProcessOneNode but lxml expects it.

    rewrites libxslt/transform.h to export the function.
    '''

    with open('transform.h', 'r') as f:
        transform_h = f.read()

    if not 'xsltProcessOneNode' in transform_h:
        to_repl = 'XSLTPUBFUN xsltTransformContextPtr XSLTCALL'
        assert to_repl in transform_h
        transform_h = transform_h.replace(
                            to_repl,
                            'XSLTPUBFUN void XSLTCALL xsltProcessOneNode(xsltTransformContextPtr ctxt, xmlNodePtr node, xsltStackElemPtr params);\n\n'
                            'XSLTPUBFUN xsltTransformContextPtr XSLTCALL')
        assert 'xsltProcessOneNode' in transform_h
        with open('transform.h', 'w') as f:
            f.write(transform_h)

def build_lxml():
    from compiledeps import libxml2_dirname

    libxml2_dir = abspath(libxml2_dirname)
    iconv_dir = abspath(iconv_dirname)

    lxml2_libs = pathjoin(libxml2_dir, 'win32', 'bin.msvc')
    if not isdir(lxml2_libs):
        fatal('could not find libxml2.lib in %s' % lxml2_libs)

    lxml2_inc = pathjoin(libxml2_dir, 'include')
    if not isdir(lxml2_inc):
        fatal('could not find libxml2 includes directory at %s' % lxml2_inc)

    if not isdir(iconv_dir):
        fatal('could not find iconv at %s' % iconv_dir)

    libxslt_dir = abspath(libxslt.dirname)
    if not isdir(libxslt_dir):
        fatal('could not find libxslt at %s' % libxslt_dir)
    libxslt_lib = pathjoin(libxslt_dir, 'win32', 'bin.msvc')

    zlib_dir = abspath('zlib-1.2.3')

    from compiledeps import lxml
    new = not os.path.exists(lxml.dirname)
    with cd(lxml.get()):
        if os.name == 'nt' and new:
            # after pulling a fresh tarball, apply the patch pointed to by lxml_patch.
            run([patch_cmd, '--ignore-whitespace', '-p0', '-i', '../%s' % lxml_patch])
        dpy(['setup.py', 'build_ext',
            '-I' + os.pathsep.join((lxml2_inc, libxslt_dir, pathjoin(iconv_dir, 'include'))),
            '-L' + os.pathsep.join((libxslt_lib, lxml2_libs, pathjoin(iconv_dir, 'lib'), zlib_dir))] +
            (['--debug'] if DEBUG else []) +
            ['install', '--install-lib', DEPS_DIR])
        build_libxml2

def build_libxml2():
    from compiledeps import libxml2_dirname
    new = not os.path.exists(libxml2_dirname)
    libxml2_dir = download_libxml2()

    with cd(libxml2_dir):
        if os.name == 'nt' and new:
            # after pulling a fresh tarball, apply the patch pointed to by lxml_patch.
            print os.getcwd()
            run([patch_cmd, '--ignore-whitespace', '-p0', '-i', os.path.abspath(os.path.join('..', libxml2_patch))])

    inform(banner = 'libiconv')
    if not isdir(iconv_dirname):
        # has a .lib compiled statically to msvcrt.dll
        wget_cached(iconv_zipfile, iconv_zipfile_size, iconv_url)
        unzip(iconv_zipfile)
    else:
        inform('libiconv directory already exists')

    patch_libxml2_h(libxml2_dir, 'include')

    iconv = abspath(iconv_dirname)

    inform(banner = 'libxml2')

    print 'passing libiconv path to configure.js as %r' % iconv

    # copy the fixed setup.py.in
    print 'copying libxml2.setup.py.msvc2008', pathjoin(libxml2_dir, 'python')
    patched_setup = 'libxml2.setup.py.msvc2008'
    assert os.path.exists(patched_setup)
    copy_different(patched_setup, pathjoin(libxml2_dir, 'python', 'setup.py.in'))

    with cd(libxml2_dir, 'win32'):
        debug_flag = ['debug=yes'] if DEBUG else []
        run(['cscript', 'configure.js', '//E:JavaScript', 'vcmanifest=yes', 'python=yes'] + debug_flag + [
             'include=%s' % pathjoin(iconv, 'include'),
             'lib=%s' % pathjoin(iconv, 'lib')])

        makefile = 'Makefile.msvc'

        # customize the Makefile...
        with open(makefile) as f:
            lines = []
            for line in f:
                # 1) optimize a bit more than just /O2
                line = line.replace('/O2', '/Os /GS- /GL /Zi')
                line = line.replace('/nologo /VERSION', '/nologo /OPT:REF /OPT:ICF /DEBUG /VERSION')

                lines.append(line)

        with open(makefile, 'w') as f:
            f.write(''.join(lines))


    with cd(libxml2_dir, 'win32'):
        run(['nmake', '-f', makefile] + (['clean'] if CLEAN else []))

    # All finished files go to DEPS_DIR:
    mkdirs(DEPS_DIR)
    deps = os.path.abspath(DEPS_DIR)

    inform(banner='libxml2 python bindings')
    with cd(libxml2_dir, 'python'):
        # installs libxml2 python files to deps directory'
        #post commit hook test line, git failed to catch the last one.
        dpy(['setup.py', 'build_ext'] + (['--debug'] if DEBUG else []) +
            ['install', '--install-lib', deps])

    # but we still need libxml2.dll
    libxml2_bindir = pathjoin(libxml2_dir, 'win32', 'bin.msvc')
    copy_different(pathjoin(libxml2_bindir, 'libxml2.dll'), deps)
    copy_different(pathjoin(libxml2_bindir, 'libxml2.pdb'), deps)

    # and iconv.dll
    copy_different(os.path.join(iconv, 'iconv.dll'), deps)

    # show which Python was used to build the PYD
    dpy(['-c', "import sys; print 'libxml2 python bindings built with %s' % sys.executable"])

    with cd(DEPS_DIR):
        dpy(['-c', "import libxml2"])

    # build and install libxslt
    libxslt_dir = build_libxslt()
    copy_different(os.path.join(libxslt_dir, 'win32', 'bin.msvc', 'libxslt.dll'), deps)
    copy_different(os.path.join(libxslt_dir, 'win32', 'bin.msvc', 'libexslt.dll'), deps)

if __name__ == '__main__':
    if 'libxml2' in sys.argv or '--libxml2' in sys.argv:
        build_libxml2()
    if 'lxml' in sys.argv or '--lxml' in sys.argv:
        build_lxml()
