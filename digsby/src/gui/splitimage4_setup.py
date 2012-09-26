#!/usr/bin/env python
import sys, string

sys.setup_is_main =  __name__ == "__main__"  #HAX: an icky hack!
from wx.build.config import *

if not os.path.exists(PKGDIR):
    os.mkdir(PKGDIR)

EXTRA_PATH = getExtraPath(addOpts = True) if INSTALL_MULTIVERSION else None

WXPY_SRC = 'C:/src/wxPython-2.8.4.2'

if True:
    location = './'
    swig_files = ['splitimage4.i', ]

    swig_sources = run_swig(swig_files,
                            location,
                            GENDIR,
                            PKGDIR,
                            True or USE_SWIG,
                            True or swig_force,
                            ['-I%s\\include\\wx\\wxPython\\i_files' % WXPY_SRC] + swig_args,
                            swig_deps)

    includes.append('.')

    if os.name == "nt":
        includes.append(WXPY_SRC + "/include")
        if UNICODE:
            includes.append(WXPY_SRC + "/lib/vc_dll/mswuh")
            defines.append(('_UNICODE',1))
        else:
            includes.append(WXPY_SRC + "/lib/vc_dll/mswh")

        libdirs.append(WXPY_SRC + "/lib/vc_dll")

    if debug:
        defines = defines + [('DEBUG', 1), ('_DEBUG',1), ('TRACING',1)]

    foosources = ['SplitImage4.cpp']

    ext = Extension('_splitimage4',  foosources + swig_sources,
                    include_dirs =  includes,
                    define_macros = defines,

                    library_dirs = libdirs,
                    libraries = libs,

                    extra_compile_args = cflags,
                    extra_link_args = lflags,
                    )
    wxpExtensions.append(ext)


if __name__ == "__main__":
    if not PREP_ONLY:
        setup(name             = PKGDIR,
          version          = VERSION,
          description      = DESCRIPTION,
          long_description = LONG_DESCRIPTION,
          author           = AUTHOR,
          author_email     = AUTHOR_EMAIL,
          url              = URL,
          license          = LICENSE,
          packages = ['wx', 'wxPython'],

          extra_path = EXTRA_PATH,
          ext_package = PKGDIR,
          ext_modules = wxpExtensions,

          options = { 'build' : { 'build_base' : BUILD_BASE }},
          )


#----------------------------------------------------------------------
#----------------------------------------------------------------------
