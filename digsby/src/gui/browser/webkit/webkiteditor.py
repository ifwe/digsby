'''

WebKit editing

'''

import wx, wx.webview
from functools import partial

class WebKitEditor(wx.webview.WebView):
    '''
    Exposes editor functionality of WebKit through the execCommand Javascript API.
    '''

    def __init__(self, parent):
        wx.webview.WebView.__init__(self, parent)

    def __getattr__(self, attr):
        '''
        wkEditor.BackColor(True, '#ff0000')  # Python becomes...
           ->
        document.execCommand('BackColor', true, '#ff0000'); // Javascript
        '''
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            # any commands from the list below get forwarded to JavaScript
            if attr in jseditor_commands:
                return partial(self._execCommand, attr)
            else:
                raise

    def _execCommand(self, *a):
        args = ', '.join(jsrepr(arg) for arg in a)
        js   = 'document.execCommand(%s);' % args

        print js

        return self.RunScript(js)


def jsrepr(o):
    'Python object -> Javascript equivalent'

    if isinstance(o, bool):
        return str(o).lower() # True -> true
    elif isinstance(o, unicode):
        return repr(o)[1:]    # u'string' -> 'string'
    else:
        return repr(o)

#
# these commands are from the map in \WebKit\webcore\editing\JSEditor.cpp
#
jseditor_commands = (
    'BackColor',
    'Bold',
    'Copy',
    'CreateLink',
    'Cut',
    'Delete',
    'FindString',
    'FontName',
    'FontSize',
    'FontSizeDelta',
    'ForeColor',
    'FormatBlock',
    'ForwardDelete',
    'HiliteColor',
    'Indent',
    'InsertHorizontalRule',
    'InsertHTML',
    'InsertImage',
    'InsertLineBreak',
    'InsertOrderedList',
    'InsertParagraph',
    'InsertNewlineInQuotedContent',
    'InsertText',
    'InsertUnorderedList',
    'Italic',
    'JustifyCenter',
    'JustifyFull',
    'JustifyLeft',
    'JustifyNone',
    'JustifyRight',
    'Outdent',
    'Paste',
    'PasteAndMatchStyle',
    'Print',
    'Redo',
    'RemoveFormat',
    'SelectAll',
    'Strikethrough',
    'Subscript',
    'Superscript',
    'Transpose',
    'Underline',
    'Undo',
    'Unlink',
    'Unselect'
)


if __name__ == '__main__':

    empty_editable_doc = '''\
<html>
    <head>
    <style>
    body {
        /* width: 100%; */
        word-wrap:  break-word;
        font-family: arial;
    }
    </style>
    </head>
    <body>
    </body>
</html>'''

    def Button(parent, text, callback, **kwargs):
        button = wx.Button(parent, -1, text, **kwargs)
        button.Bind(wx.EVT_BUTTON, lambda *e: callback())
        return button



    # construct gui
    app = wx.PySimpleApp()




    f  = wx.Frame(None, title = 'WebKit Editor Test')

    wdc = wx.WindowDC(f)
    gc = wx.GraphicsContext.Create(wdc)

    gc.SetFont(f.GetFont())
    wdc.SetFont(f.GetFont())
    print gc.GetTextExtent(' ')
    print wdc.GetTextExtent(' ')


    f.Sizer = fs = wx.BoxSizer(wx.VERTICAL)

    editor = WebKitEditor(f)
    editor.SetPageSource(empty_editable_doc)
    editor.MakeEditable(True)

    button   = lambda label, callback: Button(f, label, callback, style = wx.BU_EXACTFIT)

    def get_set_color(title, okfunc):
        c = wx.GetColourFromUser(f, caption = title)
        if c.IsOk(): okfunc(c.GetAsString(wx.C2S_HTML_SYNTAX))

    editbuttons = [
        ('B',  editor.Bold),
        ('I',  editor.Italic),
        ('U',  editor.Underline),
        ('A+', lambda: editor.fontsize(16)),
        ('A-', lambda: editor.fontsize(11)),
        ('bg', lambda: get_set_color('Background Color', lambda c: editor.BackColor(True, c))),
        ('fg', lambda: get_set_color('Foreground Color', lambda c: editor.ForeColor(True, c))),
    ]

    # layout gui
    bsizer = wx.BoxSizer(wx.HORIZONTAL)
    for label, callback in editbuttons:
        bsizer.Add(button(label, callback))

    fs.Add(bsizer, 0, wx.EXPAND)
    fs.Add(editor, 1, wx.EXPAND)

    panel = wx.Panel(f)
    panel.Sizer = wx.BoxSizer(wx.HORIZONTAL)
    panel.Sizer.AddSpacer((50, 50))
    def paint(e):
        dc = wx.PaintDC(panel)
        dc.SetFont(f.GetFont())
        dc.DrawText('ggggggg', 0, 0)

    panel.Bind(wx.EVT_PAINT, paint)

    fs.Add(panel, 0, wx.EXPAND)

    # run
    wx.CallAfter(f.Show)
    app.MainLoop()
