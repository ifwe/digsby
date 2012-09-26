import wx
import cgui
import gettext; gettext.install('Digsby')
import gui.toolbox.imagefx

class MyTabController(cgui.TabController):
    def __init__(self):
        cgui.TabController.__init__(self)
        self.thumb = None

    def GetIconicBitmap(self, tab, width, height):
        print tab, width, height

        if self.thumb is None:
            self.thumb = wx.Bitmap(r'c:\users\kevin\src\digsby\res\digsbybig.png', wx.BITMAP_TYPE_ANY).Resized((width, height))

        return self.thumb

    def GetLivePreview(self, tab, rect):
        bitmap = wx.EmptyBitmap(rect.width, rect.height)
        dc = wx.MemoryDC(bitmap)
        dc.Brush = wx.Brush(tab.Window.BackgroundColour)
        dc.DrawRectangle(0, 0, rect.width, rect.height)
        return bitmap

def main2():
    #app = wx.PySimpleApp()
    from tests.testapp import testapp
    app = testapp()
    from gui import skin

    f = wx.Frame(None)

    f.Sizer = sizer = wx.BoxSizer(wx.VERTICAL)

    tabs = cgui.TabNotebook(f)

    def maketab(color, name):
        p = wx.Panel(f, name=name)
        def leftdown(e):
            def later():
                from gui.native.toplevel import FlashOnce
                win = p if not wx.GetKeyState(wx.WXK_SHIFT) else p.Top
                print 'flashing', win
                FlashOnce(win)


            wx.CallLater(2000, later)
            e.Skip()

        def rightdown(e):
            e.Skip()
            print tabs.SetTabActive(p)

        p.Bind(wx.EVT_LEFT_DOWN, leftdown)
        p.Bind(wx.EVT_RIGHT_DOWN, rightdown)
        p.SetBackgroundColour(color)
        sizer.Add(p, 1, wx.EXPAND)

        p.tab = tabs.CreateTab(f, MyTabController())

    maketab(wx.RED, 'foo')
    maketab(wx.BLUE, 'bar')
    maketab(wx.GREEN, 'meep')

    icon = skin.get('AppDefaults.UnreadMessageIcon')
    success = tabs.SetOverlayIcon(icon)

    print
    print '###'*30
    print success

    #print cgui.TaskbarTab()

    f.Show()
    app.MainLoop()

def main():
    from tests.testapp import testapp
    app = testapp()
    from gui import skin

    icon = skin.get('AppDefaults.UnreadMessageIcon')

    #f = wx.Frame(None)
    #f.Show()

    #f.SetFrameIcon(skin.get('appdefaults.taskbaricon'))
    #w = wx.Panel(f)
    #n = cgui.TabNotebook(f)
    #n.CreateTab(w, MyTabController())
    #print '\n\n'
    icon = icon.PIL.ResizeCanvas(16, 16).WXB
    #print n.SetOverlayIcon(icon)

    import gui.native.win.taskbar as tb
    print '*'*80
    print tb.set_overlay_icon(icon)

    app.MainLoop()

if __name__ == '__main__':
    main2()

