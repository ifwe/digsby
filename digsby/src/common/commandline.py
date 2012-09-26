app = None

import wx
import threading
from pprint import pprint, pformat as pf
pp = pprint

from gui.input import input_manager as inp
from util.net import wget

try:
    from di import di
except ImportError:
    di = lambda i: None

def fire(topic, *args, **kwargs):
    from common.notifications import fire
    fire(topic, *args, **kwargs)

def im():
    from gui.imwin.imwin_gui import ImWinPanel
    for win in ImWinPanel.all():
        return win

def ad():
    for win in wx.GetTopLevelWindows():
        try:
            return win._ad_rotater
        except AttributeError:
            pass

def addebug():
    '''a debugging info frame for ad rotaters'''

    f=wx.Frame(None, size=(870, 200), title='Ad Info', name='Ad Info')
    from gui.toolbox import persist_window_pos
    persist_window_pos(f)

    f.BackgroundStyle=wx.BG_STYLE_CUSTOM
    def paint(e):
        dc = wx.AutoBufferedPaintDC(f)
        dc.Brush = wx.WHITE_BRUSH
        dc.Pen = wx.TRANSPARENT_PEN
        dc.DrawRectangleRect(f.ClientRect)
        font = f.Font
        font.PointSize = 12
        dc.Font = font

        x = y = 10
        found_rotater = False

        for win in wx.GetTopLevelWindows():
            try:
                rotater = win._ad_rotater
            except AttributeError:
                pass
            else:
                found_rotater = True
                dc.DrawText('%s: %r' % (win.Title, rotater), x, y)
                y += 20

        if not found_rotater:
            import gui.imwin.imwin_ads as imwin_ads
            secs = imwin_ads.secs_since_last_close()
            msg = 'seconds since last close: %s' % secs
            if imwin_ads.should_clear_cookies():
                msg += ' (will clear cookies on next imwin open)'
            dc.DrawText(msg, x, y)
            y += 20

    f.Bind(wx.EVT_PAINT, paint)
    f.Show()
    f.OnTop = True
    f.timer = wx.PyTimer(lambda: f.Refresh() if not wx.IsDestroyed(f) else None)
    f.timer.StartRepeating(307)

def where_string(duplicates = False):
    import sys
    from traceback import format_stack

    # thread pool threads keep a dictionary of info about their last work request,
    # so printing them here lets us see what they were up to last, even if they're
    # waiting on the next one.
    request_infos = dict((t.ident, getattr(t, 'request_info', {}))
                          for t in threading.enumerate())

    seen = set()
    s = ''
    for threadId, frame in sys._current_frames().iteritems():
        key = (frame.f_code.co_filename, frame.f_code.co_firstlineno)
        if not duplicates and key in seen:
            continue
        seen.add(key)

        s += '\n%s\n\n%s\n\n%s\n\n\n' % (threadId, ''.join(format_stack(frame)), pf(request_infos.get(threadId, None)))

    return s

def where(duplicates = False, stream = None):
    if stream is None:
        stream = sys.stdout

    stream.write(where_string(duplicates))


def bl():
    'Returns the currently visible buddylist.'
    return blist().new_sorter.view

def blist():
    return top(1).Children[0].blist.Children[0]

def bls():
    """Returns the buddylist sorter's buddylist dictionary of the form

    { protocol : root groups, ... }
    """
    return blist().new_sorter.buddylists


def crust_show( item ):
    'Show an object in the "Display" tab of the Digsby crust.'

    wx.GetApp().crust.crust.display.setItem(item)

def info():

    crust_show(dict(p.blist.info))

def killdigsby():
    'Kills the connection to the digsby server, causing a reconnect.'

    from common import profile

    profile.connection.stream.socket.close()

    def writeidle():
        if profile.connection:
            profile.connection.stream.write_raw( ' ' )

    wx.CallLater( 1000, writeidle )

def sorter():
    return blist().new_sorter

if 'wxMSW' in wx.PlatformInfo:
    def ramhack():
        'omG Digsby took my RAMs'

        from gui.native.win.process import page_out_ram; page_out_ram()

from common import profile as p

def mcs():
    'Returns active metacontacts.'
    from pprint import pprint
    pprint( p().blist.meta_contacts )

def get_connection( name=None ):
    '''
    Command line utility function to get a connection.

    Uses string.find functionality to locate a connection with the requested name.
    Should return a Protocol instance (e.g. OscarProtocol)

    Default argument returns the first found connection. (may throw an error)
    '''
    from . import profile
    if name is True:
        return profile.connection

    if not name:
        if len( profile.account_manager.connected_accounts ):
            return profile.account_manager.connected_accounts[0].connection
        else:
            #raise AssertionError('No accounts are connected. (digsbyprofile.connected_accounts = [])')
            return None

    for prof in profile.account_manager.connected_accounts:
        if str( prof ).find( name ) != -1:
            return prof.connection

    return profile.connection

def D():
    return gc( True )

def list_connections():
    'Lists all connected protocols.'
    from . import profile
    return [str( p ) for p in profile.account_manager.connected_accounts]

class reloader( object ):
    def __call__( self, obj ):
        '''Reload an object from its original Python source. The object's __class__
        will point to the newly reloaded class.

        If obj is not specified, the first connected account.

        >>> r    # reloads the current protocol

        >>> r(mybuddy)
        '''
        import util
        return util.reload_( obj )

r = reloader()

class b( object ):
    def __getattr__( self, val, default = sentinel ):
        if default is sentinel:
            return getattr( s(), val )
        else:
            return getattr( s(), val, default )

b = b()

def toggle_connection( n=0 ):
    from . import profile
    profile.account_manager.accounts[n]()

def emailtimers():
    'Prints timer values for each enabled email account.'

    return '\n'.join( ( '%r %s\n' % ( a.timer, a.email_address ) )
                     for a in p.emailaccounts if a.enabled )

def top( n=0 ):
    'Grab a reference to the nth top level window. Defaults to 0.'

    import wx
    return wx.GetTopLevelWindows()[n]

def alert( *a, **k ):
    wx.MessageBox( *a, **k )

def hit():
    return wx.FindWindowAtPoint( wx.GetMousePosition() )

def ie():
    return imwin.message_area



import sys

mbox = alert


def s():
    'Returns the currently selected item on the buddylist, or None.'
    import wx
    blist = wx.FindWindowByName('Buddy List').Children[0].blist
    i = blist.GetSelection()
    if i != -1: return blist.model[i]

def a(n=0):
    'Returns the nth account'
    from . import profile
    return profile.account_manager.accounts[n]

def ea(n=0):
    'Returns the nth email account'
    from . import profile
    return profile.account_manager.emailaccounts[n]

def eea(n=0):
    'Returns the nth enabled email account'
    from . import profile
    return [e for e in profile.account_manager.emailaccounts if e.enabled][n]

def sa(n=0):
    'Returns the nth social account'
    from . import profile
    return profile.account_manager.socialaccounts[n]

def esa(n=0):
    'Returns the nth enabled social account'
    from . import profile
    return [s for s in profile.account_manager.socialaccounts if s.enabled][n]


def rr():
    from gui import skin; skin.reload()

def save_workspace(name, lines):
    from . import pref, setpref
    if isinstance(lines, int):
        history = pref('debug.shell.history.lines', [])[:lines]
    elif isinstance(lines, list):
        assert all(isinstance(line, basestring) for line in lines)
        history = list( reversed( lines ) )
    workspaces = pref('debug.shell.workspaces', {})
    workspaces[name] = history
    setpref('debug.shell.workspaces', workspaces)

sw = save_workspace

def get_workspace( name ):
    from . import pref
    workspaces = pref( 'debug.shell.workspaces', {} )
    if name not in workspaces:
        print 'Workspace does not exist'
    return list( reversed( workspaces[name] ) )

gw = get_workspace

def load_workspace(name, verbose = True):
    'runs a workspace'
    f_globals = sys._getframe(1).f_globals
    f_locals = sys._getframe(1).f_locals
    for line in get_workspace(name):
        if verbose:
            print '>>>', line
        exec line in f_globals, f_locals
    return 'Workspace %s loaded succesfully' % name

lw = load_workspace

def print_workspace( name ):
    'prints a workspace'
    for line in get_workspace(name):
        print line

pw = print_workspace

def workspaces():
    from . import pref
    return pref( 'debug.shell.workspaces', {} ).keys()

from util import leakfinder

def profilereport():
    import util.introspect
    return util.introspect.profilereport()

if getattr(sys, 'DEV', False):
    from util.gcutil import byaddress, byclassname, byclass, count, newest

def gctree(obj, string=False):
    '''
    Shows an expandable tree of references to the given object.
    '''
    import util.gcutil

    if not string and isinstance(obj, basestring):
        # if given a string, find the newest object of that type
        obj = list(util.gcutil.byclassname(obj))[-1]

    return util.gcutil.gctree(obj)

def jsconsole():
    'Show the Javascript console.'

    from gui.browser.jsconsole import show_console
    show_console()

def xmlconsole(jabber = None):
    '''
    Shows an XML console for the latest Jabber connection, or for the connection
    given as the first argument.
    '''
    from jabber import protocol as JabberProtocol
    import common
    if jabber is None:
        jabber = get_connection()

        if not isinstance(jabber, JabberProtocol):
            for conn in common.profile.account_manager.connected_accounts:
                if isinstance(conn.connection, JabberProtocol):
                    jabber = conn.connection
                    break
            else:
                if not isinstance(jabber, JabberProtocol):
                    raise AssertionError('no jabber')

    from gui.protocols.jabbergui import show_xml_console
    show_xml_console(jabber)

"""
U{http://lists.osafoundation.org/pipermail/commits/2004-July/001779.html}
  Install a custom displayhook to keep Python from setting the global
_ (underscore) to the value of the last evaluated expression.  If
we don't do this, our mapping of _ to gettext can get overwritten.
This is useful in interactive debugging with PyCrust.
"""
def _displayHook(obj):
    sys.stdout.write(repr(obj))

sys.displayhook = _displayHook

lc = list_connections
gc = get_connection
tc = toggle_connection

try:
    import sip
except ImportError:
    pass

from gui.toolbox import show_sizers

def w(s):
    import util
    print util.wireshark_format(s)

def bugreport(simulate_flags=False):
    from util.diagnostic import send_bug_report
    send_bug_report(simulate_flags=simulate_flags)

def spin():
    'Makes and returns a spinning thread. Set thread.busydone = True to stop.'

    def busyloop():
        while not threading.currentThread().busydone:
            pass

    t = threading.Thread(target = busyloop)
    t.busydone = False
    t.start()
    return t

def set_ramhack(enabled):
    from gui.native import memfootprint
    memfootprint.set_enabled(enabled)

def prettyxml(xml):
    'Returns your XML string with nice whitespace.'

    import lxml.etree as ET
    if isinstance(xml, basestring):
        xml = ET.fromstring(xml)
    return ET.tostring(xml, pretty_print = True)

if hasattr(wx, "Crash"):
    crash = wx.Crash

def ssidump(oscar = None):
    '''Returns SSI bytes for an OscarProtocol'''

    if oscar is None:
        oscar = gc()

    return [ssi.to_bytes() for ssi in oscar.ssimanager.ssis.values()]

def ssis(oscar=None):
    if oscar is None:
        oscar = gc()

    from oscar.ssi import viewer
    viewer(oscar, None).Show()

def quit():
    'Quits Digsby normally.'

    wx.GetApp().DigsbyCleanupAndQuit()

exit = quit

def rcon():
    from common import profile
    profile.account_manager.reconnect_timers.values()[0].done_at = 0

def dcon():
    from common import profile
    profile.connection.stream.socket.send('<>')

def dump_elem_tree(e, indent = 0, maxwidth=sys.maxint):
    from contacts.buddyliststore import dump_elem_tree
    print dump_elem_tree(e, indent, maxwidth)

def bltxt():
    '''returns a textual representation of the new sorter's buddylist tree'''

    dump_elem_tree(p.blist.new_sorter.gather())

def clearorder():
    '''Resets all custom ordering.'''
    p.blist._init_order()  # clear
    p.blist.update_order() # tell sorter

# override help() to show help for this module
try:
    help
except NameError:
    help = lambda *a, **k: "Help only exists in __debug__ mode."

_help = help
help = lambda obj=None: _help(sys.modules[__name__]) if obj is None else _help(obj)
help.__doc__ = _help.__doc__

def infobox():
    return wx.GetApp().buddy_frame.buddyListPanel.infobox

def infohtml(openfolder=False, pretty=False, returnstring=False, original=True):
    'prettifies the HTML in the infobox and dumps it to a temporary file'

    webview = infobox().profilebox
    return webview_in_browser(webview,
            openfolder=openfolder, pretty=pretty, returnstring=returnstring, original=original)

def webview_in_browser(webview, openfolder=False, pretty=False, returnstring=False, original=True):
    html = webview._page if original and hasattr(webview, '_page') else webview.HTML
    if isinstance(html, bytes):
        html = html.decode('utf8')

    if pretty:
        import lxml
        doc = lxml.html.document_fromstring(html)
        html = lxml.etree.tostring(doc, pretty_print = True)

    if returnstring:
        return html
    else:
        import stdpaths
        pth = stdpaths.temp / 'infobox.html'
        pth.write_bytes(html.encode('utf-8'))
        if openfolder:
            pth.openfolder()

        return pth

def launch_html(webview):
    p = webview_in_browser(webview)
    wx.LaunchDefaultBrowser(p)

def browse(url):
    import wx.webview
    f = wx.Frame(None, -1, url)
    w = wx.webview.WebView(f)
    w.LoadURL(url)
    f.Show()
    return f

def templatebenchmark():
    import fb20.fbbenchmark as bench
    import fb20.fbacct as fbacct
    from common import profile

    fb = [a for a in profile.socialaccounts if isinstance(a, fbacct.FacebookAccount)][0]

    c = fb.connection
    data = dict(alerts=c.last_alerts,
                status=c.last_status,
                stream=c.last_stream)

    bench.benchmark(data)

def logfile():
    '''opens an explorer window showing this process's log file'''
    from path import path
    path(sys.LOGFILE_NAME).abspath().openfolder()

def tenjin(acct, filename):
    from gui.infobox.interfaces import IInfoboxHTMLProvider as IP
    try:
        i = IP(acct)
    except Exception:
        i = IP(esa(acct))
    try: i.get_html()
    except Exception: pass
    e = i.get_template().e
    for key, temp in e.cache.items.iteritems():
        if key.find(filename) != -1:
            return temp.script

def wkstats():
    '''Returns a dictionary of WebKit memory statistics.'''

    from cStringIO import StringIO
    import wx.webview
    import syck

    return syck.load(StringIO(wx.webview.WebView.GetStatistics().encode('utf-8')))

def tofrom_clear():
    from common import profile
    profile.blist.reset_tofrom()

def shallowdir(o, depth=1):
    '''returns only methods and attributes up to depth levels deep in an
    object's class's mro'''

    original = dir(o)
    indices = dict((b, i) for i, b in enumerate(original))
    return sorted(list(set(original)-set(dir(o.__class__.__mro__[depth]))),
            key=lambda a: indices[a])

def ads():
    'show ads debug window'

    import feed_trends.feed_trends as f
    f.show_debug_window()

try:
    if sys.opts.heapy:
        try:
            import guppy
        except ImportError:
            pass
        else:
            hpy = guppy.hpy()
except AttributeError:
    pass

try:
    import digsby_updater.xmpp
except ImportError:
    pass
else:
    def send_update(name):
        digsby_updater.xmpp.send_update(p.connection, name)

def xml(s):
    import lxml.etree as etree
    return etree.tostring(etree.fromstring(s), pretty_print = True)

