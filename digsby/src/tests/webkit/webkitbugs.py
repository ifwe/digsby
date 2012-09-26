'''
Tests editor functionality of WebKit through the execCommand Javascript API.
'''
import wx, wx.webview
from functools import partial


class WebKitEditor(wx.webview.WebView):
    def __init__(self, parent):
        wx.webview.WebView.__init__(self, parent)

    def _execCommand(self, *a):
        args = ', '.join(jsrepr(arg) for arg in a)
        js = 'document.execCommand(%s);' % args

        print js

        return self.RunScript(js)

    def __getattr__(self, attr):
        try:
            return wx.webview.WebView.__getattr__(self, attr)
        except AttributeError:
            if attr.startswith('__'):
                raise
            return partial(self._execCommand, attr)

def jsrepr(o):
    'Python object -> Javascript equivalent'

    if isinstance(o, bool):
        return str(o).lower() # True -> true
    elif isinstance(o, unicode):
        return repr(o)[1:]    # u'string' -> 'string'
    else:
        return repr(o)


def Button(parent, text, callback, **kwargs):
    button = wx.Button(parent, -1, text, **kwargs)
    button.Bind(wx.EVT_BUTTON, lambda *e: callback())
    return button


if __name__ == '__main__':

    # construct gui
    app = wx.PySimpleApp()
    f  = wx.Frame(None, title = 'WebKit Editor Test')
    f.Sizer = fs = wx.BoxSizer(wx.VERTICAL)

    editor = WebKitEditor(f)
    editor.SetPageSource('<html><body></body></html>')
    editor.MakeEditable(True)

    but = lambda label, callback: Button(f, label, callback, style = wx.BU_EXACTFIT)

    editbuttons = [
        ('B',  editor.Bold),
        ('I',  editor.Italic),
        ('U',  editor.Underline),
        ('A+', lambda: editor.FontSizeDelta(True, 1)),
        ('A-', lambda: editor.FontSizeDelta(True, -1)),
        ('bg', lambda: editor.BackColor(True, wx.GetColourFromUser().GetAsString(wx.C2S_HTML_SYNTAX))),
        ('fg', lambda: editor.ForeColor(True, wx.GetColourFromUser().GetAsString(wx.C2S_HTML_SYNTAX))),
    ]

    # layout gui
    bsizer = wx.BoxSizer(wx.HORIZONTAL)
    for label, callback in editbuttons:
        bsizer.Add(but(label, callback))

    fs.Add(bsizer, 0, wx.EXPAND)
    fs.Add(editor, 1, wx.EXPAND)

    # run
    f.Show()
    app.MainLoop()