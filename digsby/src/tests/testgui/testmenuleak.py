import wx, gc, weakref

class MenuCleanup(object):
    def add(self, menu):
        weakref.ref(menu, callback)
        self.refs[ref] = menu


def main():
    a = wx.PySimpleApp()

    f = wx.Frame(None)


    def update():
        menus = [a for a in gc.get_objects() if isinstance(a, wx.Menu)]


    def onmenu(e):
        m = wx.Menu()
        m.Append(-1, 'test')
        f.PopupMenu(m, f.ScreenToClient(wx.GetMousePosition()))

        update()


    f.Bind(wx.EVT_CONTEXT_MENU, onmenu)
    f.Show()

    a.MainLoop()

if __name__ == '__main__':
    main()
