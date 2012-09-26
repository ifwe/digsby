from __future__ import with_statement


from traceback import print_exc


import wx
import wx.webview as webview
import cgui

import os.path

def main():
    from tests.testapp import testapp
    app = testapp(plugins=False)
    from gui.browser.webkit.webkitwindow import WebKitWindow

    webview.WebView.SetDatabaseDirectory(r'c:\twitter_test')

    f = wx.Frame(None, title='webkit test', size = (950, 600))
    f.BackgroundStyle = wx.BG_STYLE_CUSTOM
    s = f.Sizer = wx.BoxSizer(wx.VERTICAL)

    #url = 'file://c:/Users/Kevin/src/digsby/src/social/twitter/web/twitter.html'
    #url = 'file://c:/leak.html'
    #url = 'file://c:/Users/Kevin/src/digsby/src/social/feed/app.html'

    #filepath = 'd:\\sizetest.html'
    #url = 'file://C:/Users/Aaron/Desktop/ib3.html'
    #url = 'http://symbolsystem.com/wxwebkit/bigimtest.html'

    url = 'file:///C:/users/kevin/desktop/scrollbars.html'
    #url = 'http://it-help.bathspa.ac.uk/iframe_demo.html'
    #url='http://google.com'
    #url = 'http://webkit.org/blog/138/css-animation/'

    #filepath = r'C:\users\kevin\desktop\scrollbars.html'
    #url = ''
    #filepath = 'c:\\mydir\\test.html'

    #url = 'http://webkit.org/misc/DatabaseExample.html'
    #wp = 'file:///C:/src/Digsby/res/MessageStyles/GoneDarkHacked.AdiumMessageStyle/Contents/Resources/'
    #wp = 'file://c:/mydir/'


    #with open(filepath, 'rb') as html:
        #contents = html.read().decode('utf-8')

    #contents = u'<font size="15">\u0647\u064a</font>'

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-z', '--zoom', dest='zoom', type='int', default=100)

    options, args = parser.parse_args()

    print args
    if args:
        url = args[0]

    if os.path.isfile(url):
        from path import path
        url = path(url).url()

    contents = u'''\
<!doctype html>
<html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body>
        <img src="file:///c:/\u0439\u0446\u0443\u043a\u0435\u043d.png" />
    </body>
</html>
'''

    #w = WebKitWindow(f, contents)
    w = WebKitWindow(f, url = url)
    w.BlockWebKitMenu = False
    w.ExternalLinks  = False

    t = wx.TextCtrl(f, -1, locals().get('url', ''), size=(400,-1))

    def gotourl(e):
        w.LoadURL(t.Value)

    t.Bind(wx.EVT_TEXT_ENTER, gotourl)

    set_url_button  = wx.Button(f, -1, 'url')
    set_contents_button = wx.Button(f, -1, 'contents')
    find_button = wx.Button(f, -1, 'find')
    copy_button = wx.Button(f, -1, 'Copy')
    set_contents_delay_button = wx.Button(f, -1, 'set content 5s')
    unicode_button = wx.Button(f, -1, 'add unicode')

#    def foo(e):
#        e.Skip()
#        if e.GetState() == webview.EVT_WEBVIEW_LOAD:
#            print repr(w.HTML)
#            print ' '.join('%02x' % ord(c) for c in w.HTML.encode('utf-8'))
#            t.SetValue(e.GetURL())

    def find(e):
        #const wxString& string, bool forward, bool caseSensitive, bool wrapSelection, bool startInSelection
        w.FindString(t.Value, True, False, True, False)

    # shows the order of EVT_WEBVIEW_LOAD events.
    def show(s):
        def _show(e):
            e.Skip()

            return
            print s
            if s == 'EVT_WEBVIEW_LOAD':
                print webview_evt_constants[e.State]
        return _show

    #w.Bind(webview.EVT_WEBVIEW_LOAD, show('EVT_WEBVIEW_LOAD'))
    #w.Bind(webview.EVT_WEBVIEW_BEFORE_LOAD, show('EVT_WEBVIEW_BEFORE_LOAD'))


    def OnBeforeLoad(e):
        if e.NavigationType == wx.webview.WEBVIEW_NAV_LINK_CLICKED:
            e.Cancel() # don't navigate in webkit
            wx.LaunchDefaultBrowser(e.URL)
        else:
            e.Skip()

    w.Bind(wx.webview.EVT_WEBVIEW_BEFORE_LOAD, OnBeforeLoad)

    def setcontents(e):
        w.SetHTML(t.Value)

    def copy(e):
        w.Copy()

    def setcontentlater(e):
        def later():
            try:
                w.ReleaseMouse()
            except Exception:
                print_exc()

            if w.HasCapture():
                w.ReleaseMouse()
            w.SetHTML(contents)

        wx.CallLater(2000, later)

    def addunicode(e):
        w.RunScript(u'''document.body.innerHTML = '<img align=right src="file:///c:/\u0439\u0446\u0443\u043a\u0435\u043d.png" />';''')

    set_url_button.Bind(wx.EVT_BUTTON,  gotourl)
    set_contents_button.Bind(wx.EVT_BUTTON, setcontents)
    find_button.Bind(wx.EVT_BUTTON, find)
    copy_button.Bind(wx.EVT_BUTTON, copy)
    set_contents_delay_button.Bind(wx.EVT_BUTTON, setcontentlater)
    unicode_button.Bind(wx.EVT_BUTTON, addunicode)

    def OnConsoleMessage(e):
        print e.Message

    zoom = wx.Slider(f, minValue=1, maxValue=400, value=options.zoom)
    def on_zoom(e=None):
        if e is not None: e.Skip()
        w.SetPageZoom(zoom.Value/100.0)
    zoom.Bind(wx.EVT_SCROLL_CHANGED, on_zoom)
    zoom.Bind(wx.EVT_COMMAND_SCROLL_THUMBTRACK, on_zoom)

    def zoom_later():
        zoom.SetValue(options.zoom)
        on_zoom()

    wx.CallLater(500, zoom_later)

    # glass checkbox

    glass_check = wx.CheckBox(f, -1, 'glass')
    def on_glass(e):
        if not e.IsChecked():
            cgui.glassExtendInto(f, 0, 0, 0, 0)
        f.Refresh()
    glass_check.Bind(wx.EVT_CHECKBOX, on_glass)

    f.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
    def paint(e):
        dc = wx.PaintDC(f)
        dc.Brush = wx.BLACK_BRUSH
        dc.Pen = wx.TRANSPARENT_PEN
        dc.DrawRectangleRect(f.ClientRect)
        if glass_check.Value:
            cgui.glassExtendInto(f, 0, 0, 0, w.Size.height)

    f.Bind(wx.EVT_PAINT, paint)

    w.Bind(webview.EVT_WEBVIEW_CONSOLE_MESSAGE, OnConsoleMessage)
    button_sizer = wx.BoxSizer(wx.HORIZONTAL)
    button_sizer.AddMany((button, 1, wx.EXPAND) for button in
            [
                zoom,
                set_url_button,
                glass_check,
                #set_contents_button,
                #find_button,
                #copy_button,
                #set_contents_delay_button,
                #unicode_button,
            ])

    h = wx.BoxSizer(wx.HORIZONTAL)
    h.AddMany([(t, 1, wx.EXPAND), (button_sizer, 0, wx.EXPAND)])



    s.Add(h)
    s.Add(w, 1, wx.EXPAND)

    def later():
        f.Show()
        f.Raise()
        print 'ParseMode', w.ParseMode

    wx.CallAfter(later)
    app.MainLoop()

webview_evt_constants = {webview.WEBVIEW_LOAD_STARTED: 'WEBVIEW_LOAD_STARTED',
                         webview.WEBVIEW_LOAD_NEGOTIATING: 'WEBVIEW_LOAD_NEGOTIATING',
                         webview.WEBVIEW_LOAD_REDIRECTING: 'WEBVIEW_LOAD_REDIRECTING',
                         webview.WEBVIEW_LOAD_TRANSFERRING: 'WEBVIEW_LOAD_TRANSFERRING',
                         webview.WEBVIEW_LOAD_STOPPED: 'WEBVIEW_LOAD_STOPPED',
                         webview.WEBVIEW_LOAD_FAILED: 'WEBVIEW_LOAD_FAILED',
                         webview.WEBVIEW_LOAD_DL_COMPLETED: 'WEBVIEW_LOAD_DL_COMPLETED',
                         webview.WEBVIEW_LOAD_DOC_COMPLETED: 'WEBVIEW_LOAD_DOC_COMPLETED',
                         webview.WEBVIEW_LOAD_ONLOAD_HANDLED: 'WEBVIEW_LOAD_ONLOAD_HANDLED',
                         webview.WEBVIEW_LOAD_WINDOW_OBJECT_CLEARED: 'WEBVIEW_LOAD_WINDOW_OBJECT_CLEARED'}

if __name__ == '__main__':
    main()

