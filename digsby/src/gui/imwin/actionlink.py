import wx
from gui.imwin.styles import get_theme, BasicMessageStyle
from gui.imwin.messagearea import MessageArea
from util import Storage as S
from datetime import datetime
from logging import getLogger; log = getLogger('actionlink')

class ActionLink(object):
    def __init__(self, html, **callbacks):
        self.html = html
        self.callbacks = callbacks


if __name__ == '__main__':
    message_style = 'GoneDark'


    def msgobj(msg):
        return S(buddy = b,
                 conversation = c,
                 message = msg,
                 timestamp = datetime.now())

    from tests.testapp import testapp
    a = testapp('../../..')

    theme = get_theme(message_style)
    f = wx.Frame(None, size = (600,400))
    p = wx.Panel(f)

    b  = wx.Button(p, -1, 'foo')
    b2 = wx.Button(p, -1, 'bar')
    b3 = wx.Button(p, -1, 'html')

    s = p.Sizer = wx.BoxSizer(wx.VERTICAL)
    msg = MessageArea(p, theme = theme)

    msg.OnURL('21321321:accept', lambda: log.info("SUCCESS"))

    b.Bind(wx.EVT_BUTTON,
           lambda e:  (msg.format_message('incoming', msgobj('foo foo <a href="21321321-accept">foo</a> foo fooo fo foo?'))))

    b2.Bind(wx.EVT_BUTTON,
            lambda e: (msg.format_message('incoming', msgobj('barbar bar!'), next = True)))

    b3.Bind(wx.EVT_BUTTON, lambda e: log.info(msg.HTML))

    s.Add(msg, 1, wx.EXPAND)

    h = wx.BoxSizer(wx.HORIZONTAL)
    s.Add(h, 0, wx.EXPAND)
    h.AddMany([b, b2, b3])

    from tests.mock.mockbuddy import MockBuddy
    from tests.mock.mockconversation import MockConversation

    c = MockConversation()
    b = MockBuddy('Digsby Dragon')


    #msg.format_message('incoming', msgobj('test message'))

    f.Show()
    a.MainLoop()
