#__LICENSE_GOES_HERE__
'''

build Digsby's cgui native extension (SIP version)

'''

import os
import cguisetup
import wxpysetup

from distutils.core import setup

def build():
    if os.name == 'nt':
        libs = ['User32.lib', 'Gdi32.lib', 'shell32.lib']
    else:
        libs = []

    extensions = [wxpysetup.make_sip_ext('cgui',
                     ['src/cgui.sip'] + cguisetup.sources,
                     include = './src',
                     libs = libs)]

    setup(name = 'cgui',
          version = '1.0',
          ext_modules = extensions,
          cmdclass = {'build_ext': wxpysetup.wxpy_build_ext})

if __name__ == '__main__':
    build()

