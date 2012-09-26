'''
A thin wrapper over wxHyperlinkCtrl allowing for transparency on
windows, and for passing callables to be invoked when the links
are clicked.
'''

import wx
from wx import HyperlinkCtrl, TRANSPARENT_WINDOW, HL_DEFAULT_STYLE
from config import platformName

def clearlink_url(url):
    if callable(url):
        callback = url
        url = '^_^' # a nonsense value--EVT_HYPERLINK will trigger a callable
    else:
        assert isinstance(url, basestring)
        callback = None

    return callback, url

class ClearLink(HyperlinkCtrl):
    callback = None

    def __init__(self, parent, id, label, url, style = HL_DEFAULT_STYLE, pos = wx.DefaultPosition):
        # clearlink allows the caller to pass a callable
        # as the "url" argument--which will be invoked
        # when the link is clicked.
        callback, url = clearlink_url(url)
        if callback is not None:
            self.callback = callback

        if platformName == 'win':
            style = style | TRANSPARENT_WINDOW

        HyperlinkCtrl.__init__(self, parent, id, label, url, pos = pos, style = style)
        Bind = self.Bind

        if platformName == 'win':
            # on windows we need to hack transparency
            self.dopaint = True
            self.min = False

            self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
            Bind(wx.EVT_PAINT, self.OnPaint)
            Bind(wx.EVT_MOTION, self.OnMouseMotion)
            Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)

        Bind(wx.EVT_HYPERLINK, self.OnHyperlink)

    def OnHyperlink(self, e):
        if self.callback is not None:
            self.callback()
        else:
            e.Skip()

    if platformName == 'win':
        # win-specific methods

        def OnMouseMotion(self,event):
            if not self.min:
                self.min = True
                event.Skip()

        def OnMouseLeave(self,event):
            self.min = False
            event.Skip()

        def OnPaint(self,event):
            if self.dopaint:
                self.dopaint = False
                event.Skip()
            else:
                self.dopaint = True
                self.Parent.RefreshRect(self.Rect)
