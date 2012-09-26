import wx
import wx.lib.sized_controls as sc

ID_BUG_REPORT = wx.NewId()

class ErrorDialog(sc.SizedFrame):
    def __init__(self):
        sc.SizedFrame.__init__(self, None, -1, "Traceback Viewer", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        pane = self.GetContentsPane()

        self.exc_ctrl = wx.TextCtrl(pane, -1, "", size=(300, 300), style=wx.TE_MULTILINE)
        self.exc_ctrl.SetSizerProps(expand=True, proportion=1)

        self.bug_report = wx.Button(pane, ID_BUG_REPORT, _('Send Bug Report'))
        self.bug_report.SetSizerProps(expand=False, proportion=0)
        self.Bind(wx.EVT_BUTTON, self.on_bug_report, id=ID_BUG_REPORT)

        self.Fit()
        self.MinSize = self.Size

    def on_bug_report(self, e):
        from util.diagnostic import do_diagnostic
        do_diagnostic()

    def AppendText(self, txt):
        return self.exc_ctrl.AppendText(txt)


