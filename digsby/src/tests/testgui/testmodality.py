import wx

def main():
    a = wx.PySimpleApp()
    f = wx.Frame(None)
    b = wx.Button(f, -1, 'showmodal')
    f2 = wx.Dialog(f)

    b2 = wx.Button(f2, -1, 'wut')

    def onsubbutton(e):
        print 'IsModal ', f2.IsModal()
        print 'IsShown ', f2.IsShown()


    b2.Bind(wx.EVT_BUTTON, onsubbutton)

    def onbutton(e):
        print 'onbutton'
        print 'showing modal'
        print 'result:', f2.ShowModal()
        print 'done!'

    b.Bind(wx.EVT_BUTTON, onbutton)
    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    main()