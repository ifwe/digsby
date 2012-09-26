#__LICENSE_GOES_HERE__
'''

python jsonspeedups.py build_ext install --install-lib=platform_dir

where platform_dir is win/mac/linux

'''

from distutils.core import setup, Extension

setup(name = '_jsonspeedups',
      ext_modules = [Extension('_jsonspeedups', ['../lib/simplejson/_speedups.c'])])


