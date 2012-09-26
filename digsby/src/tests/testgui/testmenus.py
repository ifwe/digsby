import wx

if __name__ == '__main__':
    from tests.testapp import testapp
    from gui.uberwidgets.umenu import UMenuBar, UMenu
    from gui import skin

    app = a = testapp(skinname = 'jeffrey')
    wx.InitAllImageHandlers()
    wx.UpdateUIEvent.SetMode(wx.UPDATE_UI_PROCESS_SPECIFIED)

    f = wx.Frame(None, -1, 'menu test')

    f.Bind(wx.EVT_MENU,  lambda e: msg('%s %s %s' % (e, e.EventType, e.Id)))

    f.Bind(wx.EVT_CLOSE, lambda e: app.ExitMainLoop())
    p = wx.Panel(f)
    f.CenterOnScreen()

    p.Sizer = wx.BoxSizer(wx.VERTICAL)

    bar  = UMenuBar(p, p.Sizer)
    bmps = [wx.Bitmap('..\\..\\..\\res\\%s.png' % aa) for aa in ('online', 'away', 'offline')]

    m = UMenu(f)
    m.AddItem('&Preferences\tCtrl+P', callback = lambda: msg('prefs'), bitmap = skin.get('serviceicons.aim'))
    accounts_item = m.AddItem('&Accounts\tCtrl+A', callback = lambda: msg('show accounts!'))

    m.AddSep()

    sub = UMenu(f)
    g = sub.AddItem('one',       callback = lambda: msg('one!'))
    sub.AddItem('two\tCtrl+T',   bitmap   = bmps[1])
    three = sub.AddItem('three', bitmap   = bmps[2])

    sub4 = UMenu(f)
    sub4.AddItem('foo1')
    sub4.AddItem('&foo')
    sub4.AddItem('&foo2')
    sub4.AddItem('bar')
    sub4.AddItem('another &foo')
    sub4.AddItem('meep')
    sub4.AddItem('fooness')
    sub.AddSubMenu(sub4, 'foobarmeep')

    g.SetBitmap(bmps[0])

    sub2 = UMenu(f); add = sub2.AddCheckItem
    add('four')
    add('five\tCtrl+F')
    add('six')

    sub3 = UMenu(f); add = sub3.AddRadioItem
    add('seven')
    add('eight\tCtrl+F')
    add('nine')

    def msg(msg):
        print msg

    m.AddSubMenu(sub, 'Submenu', onshow = lambda: g.SetText('one shown!'))
    m.AddSubMenu(sub2, 'Checks', onshow = lambda: msg('submenu 2 onshow'))
    m.AddSubMenu(sub3, 'Radios')

    m.AddItem('&Close\tCtrl+W',  callback = lambda: f.Close())

    m2 = UMenu(f, onshow = lambda menu: msg('wut')); add = m2.AddItem
    add('&Undo\tCtrl+Z')
    add('&Redo\tCtrl+Y')
    m2.AddSep()
    add('Cu&t\tCtrl+X')
    add('&Copy\tCtrl+C')
    add('&Paste\tCtrl+V')

    bar.Append(m, '&File')
    bar.Append(m2, '&Edit')

    def menu_open(e):
        print vars(e)

    def popup(e):
        m.PopupMenu()


    p.Bind(wx.EVT_RIGHT_UP, popup)
    #p.Bind(wx.EVT_PAINT, lambda e: wx.PaintDC(p).DrawBitmap(bmps[0], 10, 10, True))

    button  = wx.Button(p, -1, 'toggle skin')
    button2 = wx.Button(p, -1, 'events')

    def showevents(e):
        from gui.uberwidgets.umenu import menuEventHandler
        from pprint import pprint
        from util import funcinfo

        for id, cb in menuEventHandler(f).cbs.iteritems():
            print id, funcinfo(cb)


    button2.Bind(wx.EVT_BUTTON, showevents)

    wut = False
    def toggle(e):
        global wut
        wut = not wut

        mb = wx.GetApp().skin.tree['menubar']
        mb.mode = 'skin' if mb.get('mode', 'skin').lower() == 'native' else 'native'

        from gui.skin.skintree import refresh_wx_tree
        refresh_wx_tree()
        p.Sizer.Layout()

    button.Bind(wx.EVT_BUTTON, toggle)

    p.Sizer.Add(bar.SizableWindow)
    p.Sizer.Add((30, 140), 0)
    p.Sizer.Add(button)
    p.Sizer.Add(button2)

    f.Show()

    def wutcapture():
        win =wx.Window.GetCapture()
        if win:
            print 'capture', wx.Window.GetCapture(),'with',wx.Window.GetCapture().menu[0]
        print 'focus  ', wx.Window.FindFocus()
        print

    a.timer = wx.PyTimer(wutcapture)
    a.timer.Start(3000, False)

    a.MainLoop()
    #from util import profile; profile(a.MainLoop)
    #a.MainLoop()