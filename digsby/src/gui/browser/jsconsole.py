from __future__ import with_statement
from util import traceguard
from weakref import ref
import wx

ID_CLEAR = wx.NewId()

try: _
except: _ = lambda s:s

console = None

class JSConsoleFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, title = _('Javascript Console'), name = 'JavaScript Console')

        with traceguard:
            from gui.toolbox import persist_window_pos, snap_pref
            persist_window_pos(self,
                               defaultPos  = wx.Point(50, 50),
                               defaultSize = wx.Size(400, 300),
                               nostack     = True)
            snap_pref(self)

            from gui import skin
            self.SetFrameIcon(skin.get('AppDefaults.TaskbarIcon').Inverted)

        # don't allow menu events, etc, to go up to the IM window which
        # is our parent.
        self.SetExtraStyle(wx.WS_EX_BLOCK_EVENTS)

        self.construct()
        self.Bind(wx.EVT_TOOL, self.on_clear, id = ID_CLEAR)
        self.Bind(wx.EVT_CLOSE, self.close)

    def on_message(self, message, line_number, source_id):
        self.console.AppendText('(line %d) %s (source: %s)\n' % (line_number, message, source_id))

    def on_clear(self, e):
        self.console.Clear()

    def construct(self):
        self.console = wx.TextCtrl(self, -1, '', style = wx.TE_MULTILINE | wx.TE_READONLY)

        from gui import skin
        toolbar = self.CreateToolBar(wx.NO_BORDER | wx.TB_HORIZONTAL | wx.TB_FLAT)
        toolbar.AddTool(ID_CLEAR, _('Clear'), skin.get('AppDefaults.RemoveIcon'), wx.NullBitmap,
                        wx.ITEM_NORMAL, _('Clear'))
        toolbar.Realize()

    def close(self, e):
        global console
        console = None
        e.Skip()


def on_message(message, line_number, source_id):
    global console
    if console is None: return
    console.on_message(message, line_number, source_id)

def show_console():
    global console

    if console is not None:
        if console.Visible:
            wc = ref(console)
            console.Close()
        else:
            console.Show()
            console.Raise()
    else:
        console = JSConsoleFrame(None)
        wx.CallAfter(console.Show)

def main():
    a = wx.PySimpleApp()
    JSConsoleFrame(None).Show()
    a.MainLoop()

if __name__ == '__main__':
    main()