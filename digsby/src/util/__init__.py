import os
import sys
#assert getattr(sys, 'util_allowed', True)
sys._util_loaded = True

import digsbysite
import time
from peak.util.imports import lazyModule

if sys.platform == "win32":
    # On Windows, the best timer is time.clock()
    default_timer = time.clock
else:
    # On most other platforms the best timer is time.time()
    default_timer = time.time
del time,sys


def program_dir():
    import path
    import sys, os.path, locale

    frozen = hasattr(sys, 'frozen')
    if frozen and sys.frozen == 'windows_exe':
        return path.path(sys.executable.decode(locale.getpreferredencoding())).abspath().dirname()
    elif frozen and sys.platform.startswith('darwin'):
        exedir = path.path(sys.executable.decode(locale.getpreferredencoding())).dirname()
        return (exedir / ".." / "Resources").abspath()
    else:
        import digsbypaths
        return path.path(digsbypaths.__file__).parent

#r17477 auxencodings has no dependencies
import auxencodings
auxencodings.install()
#del auxencodings #OscarUtil need it for now.

#as of r18996, primitives has no dependencies
from primitives import *

#introspect requires primitives and path
from introspect import *

from threads import *
from net import *
from callbacks import callsback, DefaultCallback, CallLater
from fileutil import *

def soupify(*a, **k): #this method exists so that BeautifulSoup isn't imported until needed.
    import BeautifulSoup
    return BeautifulSoup.BeautifulSoup(*a, **k)

import urllib2_file #side effects
import proxy_settings #side effects

#from ie import IEEvents, IEBrowser, JavaScript, GetIE

observe = lazyModule('util.observe')

### SOME MONKEYPATCHING

import rfc822

__old_init = rfc822.Message.__init__
__old_str  = rfc822.Message.__str__

def __init__(self, fp, *a, **k):
    if isinstance(fp, basestring):
        from cStringIO import StringIO
        return __old_init(self, StringIO(fp), *a, **k)
    else:
        return __old_init(self, fp, *a, **k)

def body(self):
    return self.fp.getvalue()[self.startofbody:]

def __str__(self):
    try:
        return self.fp.getvalue()
    except:
        return __old_str(self)

rfc822.Message.__init__ = __init__
rfc822.Message.__str__  = __str__
rfc822.Message.body     = body

del rfc822
