#__LICENSE_GOES_HERE__
'''
builds Digsby's CGUI extension
'''
from __future__ import with_statement

import sys
sys.path.append('..') if not '..' in sys.path else None
from buildutil import cd, dpy
from os.path import isdir, abspath
import os

def build():
    # find WX directory
    from build_wx import WXDIR
    wxdir = abspath(WXDIR)

    # find WXPY directory, and SIP directory
    from build_wxpy import wxpy_path, sip_path
    sipdir, wxpydir = abspath(sip_path), abspath(wxpy_path)

    assert isdir(wxdir)
    assert isdir(sipdir)
    assert isdir(wxpydir)

    from buildutil import tardep
    boost = tardep('http://iweb.dl.sourceforge.net/project/boost/boost/1.42.0/', 'boost_1_42_0', '.tar.gz', 40932853)
    boost.get()

    # place these directories on the PYTHONPATH
    os.environ['PYTHONPATH'] = os.pathsep.join([wxpydir, sipdir])

    with cd('../../ext'):
        dpy(['buildbkl.py', '--wx=%s' % wxdir] +  sys.argv[1:])

def main():
    build()

if __name__ == '__main__':
    main()
