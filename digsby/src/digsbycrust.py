from util.primitives import Storage
import wx
from gui.shell import PyCrustFrame

class FakeApp(wx.PySimpleApp):

    def OnInit(self, *a, **k):
        PyCrustFrame(standalone=True).Show()
        return True

def main():
    FakeApp().MainLoop()

if __name__ == '__main__':
    import gettext
    gettext.install("digsby")
    import main as main_mod
    main_mod.setup_log_system()
    main_mod.init_threadpool()
    from common.commandline import *
    import digsbyprofile; digsbyprofile.profile = Storage(username = 'TEST')
    main()