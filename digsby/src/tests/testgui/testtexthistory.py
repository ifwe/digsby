if __name__ == '__main__':
    import gettext; gettext.install('Digsby')
import wx
from util import to_hex

from gui.toolbox.texthistory import TextHistory
from gui.toolbox import prnt

txtFlags = wx.TE_RICH2 | wx.TE_MULTILINE | wx.TE_CHARWRAP | wx.NO_BORDER | wx.WANTS_CHARS | wx.TE_NOHIDESEL

class TestTextHistory(TextHistory):
    def next(self):
        TextHistory.next(self)
        prnt('index:\t\t',self.index,'\nclip:\t\t',self.clip,'\nhistory:\t',self.history)

    def prev(self):
        TextHistory.prev(self)
        prnt('index:\t\t',self.index,'\nclip:\t\t',self.clip,'\nhistory:\t',self.history)

def main():
    from tests.testapp import testapp
    a = testapp()

    f = wx.Frame(None, -1, 'history test')
    t = wx.TextCtrl(f, -1, style = txtFlags)
    t.history = TestTextHistory(t)
    st = wx.StaticText(f, -1, '')

    def onenter(e = None):
        t.history.commit(t.Value)
        t.Clear()
        prnt('index:\t\t',t.history.index,'\nclip:\t\t',t.history.clip,'\nhistory:\t',len(t.history.history),t.history.history)

    def onkey(e):
        wx.CallAfter(lambda: st.SetLabel(to_hex(t.Value)))
        if e.ControlDown() and e.AltDown() and e.KeyCode == wx.WXK_SPACE:
            from random import choice, randrange
            import string

            for i in xrange(200):
                rstr = ''.join(choice(string.letters) for x in xrange(randrange(5,300)))
                t.AppendText(rstr)
                onenter()

            return
        e.Skip()

    t.Bind(wx.EVT_TEXT_ENTER, onenter)
    t.Bind(wx.EVT_KEY_DOWN, onkey)

    s = f.Sizer = wx.BoxSizer(wx.VERTICAL)
    s.Add(t, 1, wx.EXPAND)
    s.Add(st, 1, wx.EXPAND)




    f.Show()
    a.MainLoop()
    pass

if __name__ == '__main__':
    print 'hello'
    main()
