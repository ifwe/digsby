#__LICENSE_GOES_HERE__
#
# builds "cgui", Digsby's native code extension
#
# use "python buildexts.py build_ext" from the command line
# to build cgui.pyd or cgui.so
#

from wx.build.config import *
import wx

import cguisetup
import sys, os
from os import environ as env
from os.path import join as pj
from pprint import pprint

def build():
    global swig_args, includes, defines, cflags, lflags

    if os.name == "nt":
        WXDIR    = env['WXDIR']
        WXPY_SRC = env['WXPYDIR']

    def die(msg):
        print msg
        sys.exit(-1)

    def sanity_checks():
        from path import path
        if not path(WXPY_SRC).files('_core.py'):
            die(WXPY_SRC + ' does not have _core.py -- is it a valid wxPython?')

    swig_args += ['-v']

    print 'swig_args:'
    pprint(swig_args)
    
    includes += cguisetup.include_dirs

    if os.name == 'nt':
        includes += [
            '%s\\include' % WXPY_SRC,
            '%s\\..\\include' % WXPY_SRC,
            pj(WXPY_SRC, 'lib', 'vc_dll', 'mswuh'),
        ]

    sources = cguisetup.sources

    # WIN32
    if os.name == 'nt':
        # Unlike Win, on Unix/Mac the wxPy developer package is not separate, so we do 
        # not need this sanity check there; import wx above should fail on Unix/Mac
        # if we've got an invalid wxPython.svn diff
        sanity_checks()
        
        sources.append('src/debugapp.cpp')
        
        # add some include dirs for SWIG
        swig_args += ['-I' + pj(*([WXPY_SRC] + paths)) for paths in (
            ['src'],
            #  ['..', 'include'],
            #  ['..', 'include', 'wx', 'msw'],
            #  ['include', 'wx', 'wxPython', 'i_files'],
            )]
            
        cflags  += ['/Zi',            # generates PDBs (debugging symbols files)
                    '/D_UNICODE']     # use unicode Win32 functions

        lflags = lflags or []
        lflags  += ['/DEBUG',
                   '/LTCG']

    for include in cguisetup.include_dirs:
        swig_args += ['-I' + include]

    exts = [('cgui', sources + ["src/cgui_wrap.cpp"])]

    # common args to distuils.Extension
    extopts = dict(include_dirs       = includes,
                   define_macros      = defines,
                   library_dirs       = libdirs,
                   libraries          = libs,

                   extra_compile_args = cflags,
                   extra_link_args    = lflags,

                   swig_opts = swig_args,
                   language = 'c++',)

    ext_modules = []

    for extension_name, sources in exts:
        swig_sources = run_swig(files = ['./src/%s.i' % extension_name],
                                dir = '',
                                gendir = '.',
                                package = '.',
                                USE_SWIG  = True,
                                force     = True,
                                swig_args = swig_args,
                                swig_deps = swig_deps)

        print
        print 'building extension %r' % extension_name
        print
        print 'sources:'
        pprint(sources)
        print

        ext = Extension('_' + extension_name, sources, **extopts)
        ext_modules.append(ext)

    setup(ext_modules = ext_modules, scripts=['src/cgui.py'])

if __name__ == '__main__':
    build()
