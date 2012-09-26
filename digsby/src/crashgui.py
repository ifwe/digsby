import wx

# TODO: remove this hack
if not hasattr(wx, 'WindowClass'):
    wx.WindowClass = getattr(wx, '_Window', wx.Window)
if __name__ == '__main__':
    import gettext; gettext.install('Digsby')
import wx.lib.sized_controls as sc


CRASH_TITLE =  _('Digsby Crash Report')
CRASH_MSG_HDR = _('Digsby appears to have crashed.')
CRASH_MSG_SUB = _('If you can, please describe what you were doing before it crashed.')
CRASH_MSG = u'%s\n\n%s' % (CRASH_MSG_HDR, CRASH_MSG_SUB)
CRASH_SEND_BUTTON = _("&Send Crash Report")

class CrashDialog(sc.SizedDialog):
    '''Shown after crashes.'''

    def __init__(self, parent = None):
        sc.SizedDialog.__init__(self, parent, -1, CRASH_TITLE,
                                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.panel = CrashPanel(self)
        s = self.Sizer = wx.BoxSizer(wx.VERTICAL)
        s.Add(self.panel, 1, wx.EXPAND | wx.ALL, 8)

        self.SetButtonSizer(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL))
        self.FindWindowById(wx.ID_OK, self).SetLabel(CRASH_SEND_BUTTON)

        self.Fit()
        self.SetMinSize((self.Size.width, 150))

    @property
    def Description(self):
        return self.panel.input.Value

class CrashPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.construct()
        self.layout()

    def construct(self):
        self.msg = wx.StaticText(self, -1, CRASH_MSG)
        self.input = wx.TextCtrl(self, -1, size = (350, 200), style = wx.TE_MULTILINE)

        wx.CallAfter(self.input.SetFocus)

    def layout(self):
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.AddMany([(self.msg, 0, wx.EXPAND),
                            ((10, 10)),
                            (self.input, 1, wx.EXPAND)])

if __name__ == '__main__':
    a=wx.PySimpleApp()
    CrashDialog().ShowModal()
