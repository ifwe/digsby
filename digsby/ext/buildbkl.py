#__LICENSE_GOES_HERE__
import os.path
import shutil
import sys
import time

mydir = os.path.dirname(os.path.abspath(__file__))
print 'thisdir is', mydir
sys.path.append(os.path.abspath(os.path.join(mydir, '..', 'build')))

from buildutil import *
from buildutil.common import *

# FIXME: We need to not hardcode these!
if os.name != 'nt':
    wx_version = "2.9"
    py_version = sys.version[:3]

    depsDir = os.path.join(homeDir, "digsby-deps", "py" + py_version + "-wx" + wx_version[:3])
    buildDirs.initBuildDirs(depsDir)

def build():
    from wxpybuild.wxpyext import build_extension
    import cguisetup

    cgui_modules = [
        ('cgui', [os.path.abspath(os.path.join(mydir,'src', 'cgui.sip'))] + cguisetup.sources),
    ]

    libs = []
    if os.name == 'nt':
        libs.extend(['comsuppw', 'shlwapi']) # COM support library for _com_ptr_t in WinJumpList.cpp
    print 'buildDirs.boostDir', buildDirs.boostDir
    build_extension('cgui%s' % DEBUG_POSTFIX,
                    cgui_modules,
                    includes = cguisetup.include_dirs + [buildDirs.boostDir],
                    libs = libs,
                    libdirs = os.environ.get('LIB', '').split(os.pathsep))

    if sys.platform.startswith('win'):
        return

    buddylist_sources = '''\
sip/blist.sip
Account.cpp
Buddy.cpp
BuddyListSorter.cpp
Contact.cpp
ContactData.cpp
FileUtils.cpp
Group.cpp
Node.cpp
PythonInterface.cpp
Sorters.cpp
Status.cpp
StringUtils.cpp
'''.split()

    blist_modules = [
            ('blist', ['%s/src/BuddyList/%s' % (mydir, f) for f in buddylist_sources]),
        ]
    #return
    build_extension('blist',
                    blist_modules,
                    defines=['BUILDING_BUDDYLIST_DLL=1'],
                    includes = cguisetup.include_dirs + [buildDirs.boostDir]
                    )

def install():
    pth = os.path.abspath('.').replace('\\', '/')
    assert pth.lower().endswith('/ext'), pth

    # todo: get these paths from wxpybuild
    format = 'msvs2008prj'
    ext = 'pyd'
    if not sys.platform.startswith('win'):
        format = 'gnu'
        ext = 'so'

    builddir = 'build/obj-%s%s' % (format, DEBUG_POSTFIX)

    # FIXME: On Mac, I'm getting obj-gnu_d, even though
    # DEBUG_POSTFIX is empty.
    if not sys.platform.startswith('win'):
        builddir = builddir + '_d'

    src, dest = '%s/cgui%s.%s' % (builddir, DEBUG_POSTFIX, ext), DEPS_DIR

    shutil.copy(src, dest)
    try:
        shutil.copy('%s/blist.%s' % (builddir, ext), DEPS_DIR)
    except:
        pass

    if sys.platform.startswith('win'):
        shutil.copy(r'%s/cgui%s.pdb' % (builddir, DEBUG_POSTFIX), DEPS_DIR)

def run(cmd):
    print cmd
    os.system(cmd)

def main():
    build()
    install()

if __name__ == '__main__':
    main()
