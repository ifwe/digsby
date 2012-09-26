from gui.filetransfer.filetransferlist import FileTransferPanel
from common.filetransfer import FileTransfer
import wx
from util import autoassign
from path import path

class MockFileTransfer(FileTransfer):
    def __init__(self, **attrs):
        FileTransfer.__init__(self)
        autoassign(self, attrs)

    @property
    def name(self):
        return self.filepath.name

    def accept(self, fobj):
        self.state = self.states.CONNECTING
        self._accept(fobj)

    def decline(self):
        self.state = self.states.CANCELLED_BY_YOU

    def cancel(self):
        self.state = self.states.CANCELLED_BY_YOU

if __name__ == '__main__':
    from util.observe import ObservableList
    from tests.mock.mockbuddy import MockBuddy
    from tests.testapp import testapp

    a = testapp(plugins=False)
    f = wx.Frame(None, title = 'File Transfers')
    f.Bind(wx.EVT_CLOSE, lambda e: a.ExitMainLoop())

    filexfers = ObservableList([
        MockFileTransfer(buddy     = MockBuddy('digsby03'),
                         filepath  = path('c:\\YyyyYgq-v3.1.exe'),
                         size      = 120.6 * 1024 * 1024,
                         completed = 0,
                         direction = 'incoming',
                         ),

        MockFileTransfer(buddy     = MockBuddy('dotsyntax1'),
                         filepath  = path('c:\\DL Manager(2).jpg'),
                         size      = 253 * 1024,
                         completed = 253 * 1024,
                         direction = 'outgoing')
    ])

    ft = filexfers[0]
    ft.state = ft.states.WAITING_FOR_YOU
    filexfers[1].state = ft.states.WAITING_FOR_BUDDY


    def tick(self):
        newval = ft.completed + 320 * 1024
        ft._setcompleted(min(ft.size, newval))

        if ft.size < newval:
            ft.state = ft.states.FINISHED
            f.Unbind(wx.EVT_TIMER)



    f.Bind(wx.EVT_TIMER, tick)

    t = wx.Timer()
    t.SetOwner(f)


    ft._accept = lambda *a, **k: wx.CallLater(2000, lambda: (setattr(ft, 'state', ft.states.TRANSFERRING),
                                                            t.Start(200)))


    ftl = FileTransferPanel(f, filexfers)

    f.Show()

    a.MainLoop()


