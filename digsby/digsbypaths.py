import os.path
import sys

platformName = dict(darwin = 'mac',
                    linux2 = 'gtk',
                    win32  = 'win')[sys.platform]

def get_platlib_dir(debug=None):
    import distutils.sysconfig as sysconfig
    return sysconfig.get_python_lib()
