#__LICENSE_GOES_HERE__
'''
builds all windows digsby dependencies
'''

from __future__ import with_statement
import sys; sys.path.append('..')
import os.path

if __name__ == '__main__':
    os.chdir(os.path.abspath(os.path.dirname(__file__)))

from buildutil import run, cd, dpy, DEBUG
from datetime import datetime

def help():
    def i(msg):
        print >> sys.stderr, msg

    i('''
Usage: b [what-to-build], where what-to-build is
  all       all dependencies
  python    DPython
  libxml2   libxml2, libxslt, and lxml
  wx        wxWidgets
  webkit    wxWebKit
  wxpy      wxpy bindings
  cgui      Digsby extensions
  speedups  speedup modules for pyxmpp, simplejson, and protocols
  blist     buddylist module
  package   tools for packaging Digsby

''')

def build_all_deps():
    check_windows_sdk_version()

    #run(['python', 'build_python.py', 'all'] + (['--DEBUG'] if DEBUG else []))

    #with cd('..'):
        #dpy(['compiledeps.py', 'm2crypto'])
        #dpy(['compiledeps.py', 'syck'])

    #dpy(['build_libxml2.py', 'libxml2'])
    dpy(['build_wx.py', 'all'])
    dpy(['build_webkit.py', ('debug' if DEBUG else 'release')]) #requires libxml2, wx

    #with cd('..'):
        #dpy(['compiledeps.py', 'pil']) # uses JPEG lib from wx/webkit

    #dpy(['build_libxml2.py', 'lxml']) #depends on zlib from PIL

    dpy(['../build_wxpy.py']) #depends on webkit.
    dpy(['build_speedups.py'])
    dpy(['build_cgui.py']) #cgui depends on wx, wxpy
    dpy(['build_blist.py'])

def show_time(func):
    before = datetime.now()
    res = func()
    print '\nbuild_all took %s' % format_td(datetime.now() - before)
    return res

def format_td(td):
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    seconds = td.seconds % 60
    return '%sh:%sm:%ss' % (hours, minutes, seconds)

def check_windows_sdk_version():
    import _winreg
    for hive in (_winreg.HKEY_LOCAL_MACHINE, _winreg.HKEY_CURRENT_USER):
        # not checking 64bit mode.
        key = _winreg.OpenKey(hive, r'SOFTWARE\Microsoft\Microsoft SDKs\Windows', 0, _winreg.KEY_READ)
        ver, _tp = _winreg.QueryValueEx(key, 'CurrentVersion')
        assert int(ver[1]) >= 7, 'Microsoft Windows SDK v7.0 or higher is required, found: %s' % ver

if __name__ == '__main__':
    if '--help' in sys.argv:
        help()
    else:
        show_time(build_all_deps)
