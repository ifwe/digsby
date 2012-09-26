'''
Widgets tab in the preferences dialog.
'''
import wx
from gui.pref.prefcontrols import VSizer, HSizer
from gui.uberwidgets.PrefPanel import PrefPanel

from common import profile
from gui.widgetlist import WidgetList
from gui.browser import Browser
from wx import RIGHT, LEFT, EXPAND, TOP, BOTTOM
from config import platformName

preview_widget_url = ('http://w.digsby.com/dw.swf?'
                      'STATE=creator&field=ffffff&statustext=777777&'
                      'nick=my.nickname&bgcolor=eaeaea&text=444444&'
                      'title=Digsby+Widget&titletext=7a7a7a')

preview_placeholder='''
<html><head>
<style type="text/css">
    body { border: 0px; padding: 0px; margin: 0px;}
    *{overflow:hidden;}
</style>
</head>
<body border=0 padding=0 margin=0>
    <div id="widget">
    <embed src="%s" type="application/x-shockwave-flash" wmode="transparent" width="%%s" height="%%s"></embed>
    </div>
</body>
</html>''' % preview_widget_url

from logging import getLogger; log = getLogger('pg_widgets')

def panel(p, sizer, addgroup, exithooks):
    widgetlist = WidgetList(p, profile.widgets)

    browser = Browser(p)
    browser.SetMinSize((235, -1))

    preview = PrefPanel(p, browser, _('Widget Preview'))
    preview.SetMinSize((235, -1))

    embedpanel = wx.Panel(p)
    es = embedpanel.Sizer = VSizer()
    embedtext  = wx.TextCtrl(embedpanel, -1, '', style = wx.TE_MULTILINE | wx.TE_READONLY)
    embedtext.SetMinSize((-1, 60))

    copybutton = wx.Button(embedpanel, -1, _('&Copy To Clipboard'),
                           style = wx.BU_EXACTFIT if platformName == 'mac' else 0)

    if platformName == 'mac':
        copybutton.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)
        button_flags = 0, wx.ALIGN_RIGHT | RIGHT | TOP | BOTTOM, 3
    else:
        button_flags = 0, EXPAND | TOP, 3

    es.Add(embedtext, 1, EXPAND)
    es.Add(copybutton, *button_flags)

    def docopy(e):
        clip = wx.TheClipboard
        if clip.Open():
            clip.SetData( wx.TextDataObject(embedtext.Value) )
            clip.Close()

    copybutton.Bind(wx.EVT_BUTTON, docopy)
    copybutton.Enable(False)


    def show_widget(widget_embed_text):
        browser.SetPage(widget_embed_text)

    def on_widget_selection(e):
        i = e.Int
        log.info('widget %d selected', i)
        if i != -1:
            widget = widgetlist.GetDataObject(i)
            embedtext.Value = widget.embed_tag
            copybutton.Enable(bool(embedtext.Value))

            wx.CallLater(150, show_widget, widget.embed_creator(*browser.Size))
        else:
            copybutton.Enable(False)

    widgetlist.Bind(wx.EVT_LIST_ITEM_SELECTED, on_widget_selection)

    widgets = PrefPanel(p, widgetlist, _('Widgets'), _('New Widget'), lambda b: widgetlist.OnNew())

    embed = PrefPanel(p, embedpanel, _('Embed Tag'))

    top = HSizer()
    top.Add(widgets, 1, EXPAND)
    top.Add(preview, 0, EXPAND | LEFT,6)

    sizer.Add(top, 1, EXPAND)
    sizer.Add(embed, 0, EXPAND | TOP,6)

    p.on_close = widgetlist.on_close
    wx.CallLater(10, lambda: browser.SetPage(preview_placeholder % tuple(browser.Size)))
    return p


