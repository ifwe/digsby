#__LICENSE_GOES_HERE__
'''
Use -I to point to include directories for libxml2 and iconv, and -L to point
to the  libxml2 library.

example:

C:\dev\digsby\ext>python build_xmlextra.py build_ext -L c:\dev\digsby\build\msw\
libxml2-2.6.31\win32\bin.msvc -I c:\dev\digsby\build\msw\libxml2-2.6.31\i
nclude -I c:\dev\digsby\build\msw\libiconv install --install-lib=win
'''

sources   = ['src/xmlextra/xmlextra.c']
libraries = ['libxml2']

from distutils.core import setup, Extension
import os

if os.name == 'nt':
    # include debugging information
    cflags = ['/GL', '/Zi', '/GS-']
    ldflags = ['/DEBUG', '/OPT:REF', '/OPT:ICF']
else:
    cflags = []
    ldflags = []

setup(name = '_xmlextra', ext_modules = [
    Extension('_xmlextra',
              sources,
              libraries = libraries,
              extra_compile_args = cflags,
              extra_link_args = ldflags)

])
