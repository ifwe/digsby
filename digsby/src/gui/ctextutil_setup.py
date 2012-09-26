import distutils
from distutils.core import setup
from distutils.core import Extension

WXPYTHON_BIN_DIR = 'C:\\src\\wxPython-2.8.4.0'

files = '''
ctextutil.cpp
ctextutil.i
'''.split()

ctextutilExt = Extension('_ctextutil', files,
    swig_opts = ['-c++', '-I%s\\include\\wx\\wxPython\\i_files' % WXPYTHON_BIN_DIR],
    include_dirs = ['C:\\src\\wxPython-2.8.1.1\\lib\\vc_dll\\mswuh',
                    "%s/include" % WXPYTHON_BIN_DIR,
                    '%s/include/wx/msw' % WXPYTHON_BIN_DIR,
                    'C:\\program files\\Microsoft Visual C++ Toolkit 2003\\include',
                    'C:\\program files\\Microsoft Platform SDK for Windows Server 2003 R2\\Include',
    ],
    library_dirs = ['C:\\program files\\Microsoft Platform SDK for Windows Server 2003 R2\\Lib',
                    'C:\\program files\\Microsoft Visual Studio .NET 2003\\Vc7\\lib',
                    'C:\\src\\wxPython-2.8.1.1\\lib\\vc_dll',
                    ],
    libraries = 'wxmsw28uh_core wxmsw28uh_adv wxbase28uh'.split(),
    define_macros = [('WXUSINGDLL','1'),
                     ('_UNICODE',1)]
)

if __name__ == '__main__':

    setup(name='ctextutil', version='1.0',
          ext_modules=[ ctextutilExt ]
    )