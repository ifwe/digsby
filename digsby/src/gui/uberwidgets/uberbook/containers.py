from page import Page
import wx
from wx import BoxSizer, VERTICAL, EXPAND
from cgui import SimplePanel

class PageContainer(SimplePanel):
    'Stores and displays pages.'

    def __init__(self, parent):
        SimplePanel.__init__(self, parent)
        self.SetSizer(BoxSizer(VERTICAL))
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self._active = None

    def OnSize(self,event):
        event.Skip()
        if self._active:
            wx.CallAfter(lambda: wx.CallAfter(self._active.SetSize, self.Size))

    def Append(self, panel_or_page):
        '''
        Note: should only be called by UberBook and TabManager

        Creates a page from the panel provided if not already a page
        Adds that page to the container
        Returns that page to the parent notebook for tab generation
        '''

        if isinstance(panel_or_page, Page):
            page = panel_or_page
            page.Reparent(self)
        else:
            page = Page(self, panel_or_page)

        page.Size = self.Size
        return page

    def GetActive(self):
        'Returns the active page.'

        return self._active

    def SetActive(self, source):
        "A way for a page to set itself active."

        if self._active!=source:
            if self._active:
                self._active.Hide()

            self._active = source
            self._active.Size = self.Size
            print 'calling show on', self._active
            self._active.Show()
            self.Layout()

    active = property(GetActive, SetActive)