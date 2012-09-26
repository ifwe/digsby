import wx
from util.primitives.funcs import do
from cgui import SimplePanel

from logging import getLogger
log = getLogger('uberbook.page')

class Page(SimplePanel):
    """
        This holds the contents associated with a tab.
        Handles all commands related to itself and acts as a hub between the panel,
        the PageContainer, and the associated Tab
    """
    def __init__(self, parent, panel, size = wx.DefaultSize):
#        wx.Panel.__init__(self, parent, size=size)
        SimplePanel.__init__(self, parent)
        self.Show(False)

        do(self.Bind(event, method) for (event,method) in (
            (wx.EVT_CLOSE, self.OnClose),
        ))

        panel.Reparent(self)
        self.Sizer=wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(panel, 1, wx.EXPAND)
        #panel.Show(True)

        self.panel=panel

        self.name  = getattr(panel, 'name', getattr(panel, 'Title', u''))

        from gui import skin
        self.icon  = skin.get('BuddiesPanel.BuddyIcons.NoIcon').WXB

        self.nicon = None
        self.notified = False

        self.tab = None

        panel.update_icon()
        panel.update_title()

    def Reparent(self,newparent):
        SimplePanel.Reparent(self,newparent)
        #self.panel.OnTopChanged()

    @property
    def Content(self):
        return self.Children[0]

    @property
    def Notebook(self):
        return self.GrandParent

    def SetIcon(self, icon):
        self.icon = icon

        #print '*'*80
        #print 'did_seticon(%r, %r)' % (self.panel, icon)
        #print self.tab

        self.Notebook.did_seticon(self.Content, icon)

        tab = self.tab
        if tab:
            if tab.IsShownOnScreen():
                tab.Refresh()

            if tab.active and self.icon is not None:
                self.Top.SetFrameIcon(self.icon)


    def SetTitle(self, title, window_title = None):
        '''
        Sets this page's title (shown in its tab).

        If window_title is not None, that string is used in the TopLevelWindow's title instead.
        '''

        self.title        = title
        self.window_title = window_title

        log.info('%r.SetTitle(%r, %r)', self, title, window_title)

        self.Notebook.did_settitle(self.Content, window_title or title)

        tab = self.tab
        if tab:
            log.info('setting title for tab to %r', title)
            tab.SetLabel(title)

    def GetIcon(self):
        return self.icon

    Icon = property(GetIcon)

    def Display(self):
        """
            Called to move the page front and center
        """
        self.Parent.active = self
        self.panel.SetFocus()

    def Hide(self):
        'This will hide the page and deactivate the tab.'

        self.tab.active = False
        self.Show(False)

    def OnClose(self, event):
        """
            Internal use only
            Closes the page ONLY!
            use tab.Close() instead
        """
        #HAX:: uberbook needs to throw tab closing events
        if hasattr(self.Children[0], 'on_close'):
            self.Children[0].on_close()

        self.Destroy()

    def __repr__(self): return '<Page with %r>' % self.GetChildren()
