#__LICENSE_GOES_HERE__
'''
builds buddylist.dll and blist.pyd and installs them to DEPS_DIR
'''

import sys
import os.path
import distutils.sysconfig

from subprocess import call
blist_dir = os.path.dirname(__file__)
if '..' not in sys.path: sys.path.append(os.path.join(blist_dir, '..'))
from buildutil import dpy, DEBUG, DEPS_DIR, copy_different

buddylist_root = os.path.join(blist_dir, '../..', r'ext/src/BuddyList')

def build():
    project_dir = os.path.join(buddylist_root, 'msvc2008')
    solution_file = os.path.normpath(os.path.abspath(os.path.join(project_dir, 'BuddyListSort.sln')))

    config_name = 'Debug' if DEBUG else 'Release'
    configuration = '%s|Win32' % config_name

    # the MSVC project files use the DIGSBY_PYTHON environment variable to find
    # Python.h and python2x.lib
    env = dict(os.environ)

    SIP_INCLUDE = os.path.normpath(os.path.abspath('../../build/msw/sip/siplib'))
    SIP_BIN = os.path.normpath(os.path.abspath('../../build/msw/sip/sipgen/sip.exe'))

    assert os.path.isdir(SIP_INCLUDE), 'expected a siplib directory at ' + SIP_BIN
    assert os.path.isfile(SIP_BIN), 'expected a sip binary at ' + SIP_BIN

    env.update(
        SIP_INCLUDE=SIP_INCLUDE,
        SIP_BIN=SIP_BIN,
        DIGSBY_PYTHON=os.path.dirname(distutils.sysconfig.get_python_inc()))

    # Invoke vcbuild
    ret = call(['vcbuild', '/nologo', solution_file, configuration], env=env)
    if ret: sys.exit(ret)

    # Install to DEPS_DIR
    binaries = 'blist{d}.pyd blist{d}.pdb buddylist{d}.dll buddylist{d}.pdb'
    for f in binaries.format(d='_d' if DEBUG else '').split():
        binary = os.path.join(project_dir, config_name, f)
        copy_different(binary, DEPS_DIR)

def test():
    sorter_test_file = os.path.join(buddylist_root, 'test/sorter_test.py')
    dpy([sorter_test_file], platlib = True)

def main():
    if 'test' in sys.argv:
        test()
    else:
        build()

if __name__ == '__main__':
    main()
