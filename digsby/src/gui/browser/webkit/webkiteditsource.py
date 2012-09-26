from __future__ import with_statement

def EditSource(self):
    'Brings up a simple editor with the HTML source of this window, available for editing.'

    import wx
    from util import soupify
    from wx.stc import StyledTextCtrl, STC_LEX_HTML

    font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                   wx.FONTWEIGHT_NORMAL, False, "Consolas")

    f = wx.Frame(wx.GetTopLevelParent(self), -1, 'View Source', name = 'View Source', size = (640, 480))
    s = wx.BoxSizer(wx.VERTICAL)
    t = StyledTextCtrl(f, -1, wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
    #t.SetLexer(STC_LEX_HTML)

    orightml = self.HTML

    # TODO: BeautifulSoup is more destructive than is useful here.
    html = soupify(orightml).prettify()
    t.SetText(html)
    #t.SetFont(font)
    wx.CallAfter(t.SetSelection, 0, 0)

    buttons = wx.Panel(f)
    save = wx.Button(buttons, -1, '&Save')
    save.Bind(wx.EVT_BUTTON, lambda e: self.SetHTML(t.GetText()))

    save_as_file = wx.Button(buttons, -1, 'Save &As File...')

    def onsaveasfile(e):
        diag = wx.FileDialog(self, "Save HTML", "contents.html", style=wx.SAVE)

        if diag.ShowModal() == wx.ID_OK:
            with open(diag.GetPath(), 'wb') as f:
                f.write(orightml.encode('utf-8'))

    save_as_file.Bind(wx.EVT_BUTTON, onsaveasfile)

    copybutton = wx.Button(buttons, -1, _('&Copy'))

    def openinbrowser(e):
        from subprocess import Popen
        import os.path, tempfile

        fdesc, fname  = tempfile.mkstemp()
        with os.fdopen(fdesc, 'w') as f:
            f.write(t.GetText().encode('utf-8'))

        if "wxMSW" in wx.PlatformInfo:
            from common import pref
            from path import path

            browser_exe = pref('debug.message_area.debug_browser',
                               r'c:\Program Files\Safari\Safari.exe', type=basestring)
            browser_exe = path(browser_exe).expand()

            if browser_exe.isfile():
                Popen([browser_exe, fname])
            else:
                wx.MessageBox('Error launching browser:\n\n'
                              '"%s"\n\n'
                              'Please set the "debug.message_area.debug_browser" pref to\n'
                              'the path to your web browser.' % browser_exe,
                              'Open in Browser')
        else:
            import webbrowser
            webbrowser.open_new("file://" + fname)


    openbutton = wx.Button(buttons, -1, _('&Open in Browser'))
    openbutton.Bind(wx.EVT_BUTTON, openinbrowser)
    openbutton.SetToolTipString(_('Launches browser in pref "debug.message_area.debug_browser"'))

    def docopy(e):
        clip = wx.TheClipboard
        if clip.Open():
            clip.SetData( wx.TextDataObject(t.Value) )
            clip.Close()

    copybutton.Bind(wx.EVT_BUTTON, docopy)

    buttons.Sizer = wx.BoxSizer(wx.HORIZONTAL)
    buttons.Sizer.AddMany([save, copybutton, openbutton, save_as_file])

    s.Add(t, 1, wx.EXPAND)
    s.Add(buttons, 0, wx.EXPAND)
    f.SetSizer(s)

    # remember position and cascade when necessary
    from gui.toolbox import persist_window_pos
    persist_window_pos(f)
    f.EnsureNotStacked()

    f.Show()

