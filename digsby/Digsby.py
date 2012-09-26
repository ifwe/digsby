import time; time.clock() #startup time.

import sys
import os.path

from digsbypaths import get_platlib_dir, platformName

if __debug__:
    os.chdir(os.path.abspath(os.path.dirname(__file__)))

    extra_paths = [
        './src',
        './lib',
        './platlib/' + platformName,
    ]

    platlib_dir = get_platlib_dir()
    if platlib_dir not in sys.path:
        sys.path.insert(0, platlib_dir)

    sys.path[0:0] = map(os.path.abspath, extra_paths)

    if os.name == 'nt':
        os.environ['PATH'] = os.pathsep.join([os.environ['PATH'], get_platlib_dir()])

else:
    launcher_name = 'digsby.exe'
    __libdir, __myname = os.path.split(sys.executable)
    __mydir, __ = os.path.split(__libdir)
    os.chdir(__mydir)

    # Vista doesn't find ssleay32.dll without this PATH modification (ssleay32.dll
    # is one of the binaries that is depended on by PYDs in more than one directory
    # location).
    os.environ['PATH'] = os.path.pathsep.join((__libdir, os.environ.get('PATH', '')))

    sys.prefix = __libdir
    sys._real_exe, sys.executable = sys.executable, os.path.join(__mydir, launcher_name)

# need this really early
if __name__ == '__main__':
    import options
    sys.opts, _args = options.parser.parse_args()

# Monkeypatches that used to be in DPython
import netextensions

# imported for its side effects
import digsbysite
import logextensions
del digsbysite

import socks
sys.modules['socket'] = socks
if platformName == 'win' and hasattr(socks._socket, '_GLOBAL_DEFAULT_TIMEOUT'):
    # for python 2.6 compatability
    socks._GLOBAL_DEFAULT_TIMEOUT = socks._socket._GLOBAL_DEFAULT_TIMEOUT

def main():
    # guard against util being imported too early
    assert not getattr(sys, '_util_loaded', False)
    sys.util_allowed = False

    import main
    main.main()


    print >>sys.stderr, "Digsby.py main is done."

if __name__ == '__main__':
    main()

