import wx

import config
import gui.pref.prefcontrols as PC
from gui.uberwidgets.PrefPanel import PrefPanel, PrefCollection

from common import setpref, pref
from util import traceguard
from gui.browser.webkit import WebKitDisplay

WALL_OF_TEXT = _(
u'''\
Help Digsby stay free for all users. Allow Digsby to use part of your computer's idle processing power to contribute to commercial grid computing projects by enabling the Research Module.
<p>
This module turns on after your computer has been completely idle (no mouse or keyboard movement) for a period of time. It turns off the instant you move your mouse or press a key, so it has no effect on your PC's performance when you're using it. The research module also runs as a low priority, sandboxed Java process, so that other tasks your computer is doing will get done first, and so that it is completely secure.
<p>
For more details, see the <a href="http://wiki.digsby.com/doku.php?id=cpuusage">Research Module FAQ</a>.
'''
)

# TODO move all this into the WebKitDisplay class
if config.platform == 'win':
    import gui.native.win.winutil as winutil

    if winutil.is_vista():
        font = 'Segoe UI, Tahoma, MS Sans Serif; font-size: 9pt;'
    else:
        font = 'Tahoma, MS Sans Serif; font-size: 11px;'
else:
    font = 'Arial 12px' # TODO: other platforms.


css = u'''\
body {
margin: 0;
overflow: hidden;
cursor: default;
background-color: white;
font-family: %s;
-webkit-text-size-adjust: none;
-webkit-user-select: none;
}''' % font

description_html = u'''<!doctype html><html><head><style>{css}</style></head>
<body><div id="container">{body}</container></body></html>'''.format(
    css=css,
    body=WALL_OF_TEXT)

def build_description_webview(parent, prefix):
    webview = WebKitDisplay(parent)

    # TODO: this entire figure-out-the-size-of-the-webview is also repeated in
    # infobox.py. We need to add a method to wxWebView that says: layout your
    # content at this width, and return your height.

    webview._loaded = False
    def on_load(e):
        e.Skip()
        if e.GetState() == wx.webview.WEBVIEW_LOAD_ONLOAD_HANDLED:
            webview._loaded = True

    def on_timer():
        if not webview._loaded:
            return

        webview._timer.Stop()
        with traceguard:
            height = webview.RunScript('document.getElementById("container").clientHeight')
            height = int(height)
            webview.SetMinSize((-1, height))
            webview.GrandParent.Layout()
        parent.Thaw()

    webview.SetMinSize((-1, 160))
    webview._timer = wx.PyTimer(on_timer)
    webview._timer.StartRepeating(50)
    webview.Bind(wx.webview.EVT_WEBVIEW_LOAD, on_load)

    webview.SetPageSource(description_html)
    parent.Freeze()
    return webview


def panel(panel, sizer, addgroup, exithooks):

    try:
        import researchdriver.driver
    except ImportError:
        default_cpu_num = 75
        default_bandwidth_num = 90
    else:
        default_cpu_num = int(researchdriver.driver.get_cpu_percent())
        default_bandwidth_num = int(researchdriver.driver.get_bandwidth_percent())

    description = PrefPanel(
        panel,
        build_description_webview,
        _('Research Module'),
        prefix = '',
    )
    options = PrefPanel(panel,
            PrefCollection(
                           PrefCollection(
                                          PC.Check('local.research.enabled',
                                                   _('Allow Digsby to use CPU time to conduct research after %2(research.idle_time_min)d minutes of idle time')),
                                          layout = PC.VSizer(),
                                          itemoptions = (0, wx.ALL, 3),
                                          ),
                           PrefCollection(
                                          lambda parent, prefix: PC.Slider(PC.pname(prefix, 'local.research.cpu_percent'),
                                                                           _('Maximum CPU Usage:'),
                                                                           start = 1, stop = 101, step = 1,
                                                                           value   = int(PC.get_pref('local.research.cpu_percent', default=default_cpu_num)),
                                                                           default = int(PC.get_pref('local.research.cpu_percent', default=default_cpu_num)),
                                                                           fireonslide = True,
                                                                           unit = _('{val}%'))(parent)[0], # Slider returns the sizer and the control, we just want the sizer
                                          lambda parent, prefix: PC.Slider(PC.pname(prefix, 'local.research.bandwidth_percent'),
                                                                           _('Maximum Bandwidth Usage:'),
                                                                           start = 1, stop = 101, step = 1,
                                                                           value   = int(PC.get_pref('local.research.bandwidth_percent', default=default_bandwidth_num)),
                                                                           default = int(PC.get_pref('local.research.bandwidth_percent', default=default_bandwidth_num)),
                                                                           fireonslide = True,
                                                                           unit = _('{val}%'))(parent)[0], # Slider returns the sizer and the control, we just want the sizer
                                          layout = PC.HSizer(),
                                          itemoptions = (0, wx.ALL, 3),
                                          ),
                           layout = PC.VSizer(),
                           itemoptions = (0, wx.BOTTOM | wx.TOP, 3)),
            _('Options'),
            prefix = '',
    )

    sizer.Add(description, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 3)
    sizer.Add(options, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 3)

    return panel
