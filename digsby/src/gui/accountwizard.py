'''
Account wizard.
'''

import wx
from gui.pref import pg_accounts
from gui import skin
from gui.native.win.winutil import is_vista
import traceback

import util.primitives.funcs as utilfuncs

def show():
    if not AccountWizard.RaiseExisting():
        w = AccountWizard()
        w.CenterOnScreen()
        w.Show()

def bind_paint(ctrl, paint):
    def on_paint(e):
        dc = wx.AutoBufferedPaintDC(ctrl)
        return paint(dc)

    ctrl.Bind(wx.EVT_PAINT, on_paint)

class AccountWizard(wx.Frame):
    MIN_SIZE = (567, 569)

    def __init__(self, parent=None):
        wx.Frame.__init__(self, parent, -1,
                          title=_('Digsby Setup Wizard'))

        self.SetFrameIcon(skin.get('AppDefaults.TaskbarIcon'))
        self.Bind(wx.EVT_CLOSE, self.on_close)
        big_panel = wx.Panel(self)

        # header
        header = wx.Panel(big_panel)
        header.SetBackgroundColour(wx.Colour(244, 249, 251))
        hdr1 = wx.StaticText(header, -1, _('Welcome to Digsby!'))
        set_font(hdr1, 18, True)

        elems = \
        [(False, 'All your '),
         (True, 'IM'),
         (False, ', '),
         (True, 'Email'),
         (False, ' and '),
         (True, 'Social Network'),
         (False, ' accounts under one roof.')]

        txts = []
        for emphasis, text in elems:
            txt = wx.StaticText(header, -1, text)
            set_font(txt, 12, bold=emphasis, underline=False)
            txts.append(txt)

        txt_sizer = wx.BoxSizer(wx.HORIZONTAL)
        txt_sizer.AddMany(txts)

        icon = skin.get('AppDefaults.TaskBarIcon').PIL.Resized(48).WXB
        bind_paint(header, lambda dc: dc.DrawBitmap(icon, 5, 3, True))
        icon_pad = icon.Width + 6

        header.Sizer = sz = wx.BoxSizer(wx.VERTICAL)
        sz.AddMany([(hdr1, 0, wx.EXPAND | wx.LEFT, 6 + icon_pad),
                    (3, 3),
                    (txt_sizer, 0, wx.EXPAND | wx.LEFT, 6 + icon_pad)])

        # accounts panel
        panel = wx.Panel(big_panel)
        panel.BackgroundColour = wx.WHITE

        panel.Sizer = sizer = wx.BoxSizer(wx.VERTICAL)
        self.exithooks = utilfuncs.Delegate()
        pg_accounts.panel(panel, sizer, None, self.exithooks)

        # paint the background + line
        def paint(e):
            dc = wx.AutoBufferedPaintDC(big_panel)
            dc.Brush = wx.WHITE_BRUSH
            dc.Pen = wx.TRANSPARENT_PEN
            r = big_panel.ClientRect
            dc.DrawRectangleRect(r)
            dc.Brush = wx.Brush(header.BackgroundColour)

            y = header.Size.height + 19
            dc.DrawRectangle(0, 0, r.width, y)
            dc.Brush = wx.Brush(wx.BLACK)
            dc.DrawRectangle(0, y, r.width, 1)

        big_panel.BackgroundStyle = wx.BG_STYLE_CUSTOM
        big_panel.Bind(wx.EVT_PAINT, paint)

        # Done button
#        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
#        button_sizer.AddStretchSpacer(1)
#        done = wx.Button(panel, -1, _('&Done'))
#        done.Bind(wx.EVT_BUTTON, lambda e: self.Close())
#        button_sizer.Add(done, 0, wx.EXPAND)
#        sizer.Add(button_sizer, 0, wx.EXPAND | wx.TOP, 10)

        big_panel.Sizer = sz = wx.BoxSizer(wx.VERTICAL)
        sz.Add(header, 0, wx.EXPAND | wx.ALL, 8)
        sz.Add((5, 5))
        sz.Add(panel, 1, wx.EXPAND | wx.ALL, 12)

        self.SetMinSize(self.MIN_SIZE)
        self.SetSize(self.MIN_SIZE)

    def on_close(self, e):
        def show_hint():
            icons = wx.GetApp().buddy_frame.buddyListPanel.tray_icons
            if icons:
                icon = icons[0][1]
                icon.ShowBalloon(_('Quick Access to Newsfeeds'),
                _('\nYou can access social network and email newsfeeds'
                ' by clicking their icons in the tray.\n'
                '\nDouble click to update your status (social networks)'
                ' or launch your inbox (email accounts).\n'
                ' \n'), 0, wx.ICON_INFORMATION)
        wx.CallLater(300, show_hint)
        if getattr(self, 'exithooks', None) is not None:
            self.exithooks()
        e.Skip(True)


def set_font(ctrl, size, bold=False, underline=False):
    f = ctrl.Font
    if is_vista(): f.SetFaceName('Segoe UI')
    f.PointSize = size
    if bold: f.Weight = wx.FONTWEIGHT_BOLD
    if underline: f.SetUnderlined(True)
    ctrl.Font = f
