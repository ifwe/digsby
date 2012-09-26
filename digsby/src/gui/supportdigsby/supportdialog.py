import traceback

import wx
import gui.toolbox
import gui.wxextensions
import gui.pref.prefcontrols as pc
import supportoptions

#import wx.lib.sized_controls as sc
#parentclass = sc.SizedPanel
_parentclass = wx.Panel

def _SetColors(thing, fg, bg):
    thing.BackgroundColour = bg
    thing.ForegroundColour = fg

class SupportPanel(_parentclass):
    SPACING = 6
    def __init__(self, options, *a, **k):
        self.separators = []
        self.options = options
        _parentclass.__init__(self, *a, **k)
        self.build()
        self.do_layout()

    def OnClose(self):
        pass

    def do_layout(self):
        self.Layout()
        self.Fit()
        self.SetMinSize(self.Size)
        self.SetMaxSize(self.Size)

        self.Parent.Layout()
        self.Parent.Fit()

        self.Refresh()

    def build(self):
        sz = pc.VSizer()

        #_SetColors(self, wx.WHITE, wx.BLACK)

        for option in self.options[:-1]:
            sz.Add(self.build_option(option), border = self.SPACING, flag = wx.EXPAND | wx.ALL)
            sz.Add(self.make_separator(), flag = wx.CENTER | wx.EXPAND)

        sz.Add(self.build_option(self.options[-1]), border = self.SPACING, flag = wx.EXPAND | wx.ALL)

        main_sz = pc.HSizer()
        main_sz.Add(sz, 1, flag = wx.EXPAND | wx.LEFT | wx.RIGHT, border = self.SPACING)
        self.Sizer = main_sz

    def make_separator(self):
        sz = pc.HSizer()
        sz.AddSpacer((5, 0))
        line = wx.StaticLine(self, size = wx.Size(0, 2))
        #_SetColors(line, wx.WHITE, wx.BLACK)
        sz.Add(line, proportion = 1, flag = wx.EXPAND | wx.CENTER)
        sz.AddSpacer((5, 0))
        return sz

    def build_option(self, o):
        sz = pc.HSizer()

        txt = wx.StaticText(self, label = o.description)
        btn = wx.Button(self, label = o.action_text)

#        txt.SetBold(True)
        #_SetColors(txt, wx.WHITE, wx.BLACK)

        sz.Add(txt, flag = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border = self.SPACING)
        
        help_link = getattr(o, 'help_link', None)
        if help_link is not None:
            from gui.toolbox import HelpLink
            sz.Add(HelpLink(self, help_link))
        
        sz.AddSpacer(10)
        sz.AddStretchSpacer()
        sz.Add(btn, flag = wx.ALIGN_RIGHT)

        btn.Bind(wx.EVT_BUTTON, self.make_click_handler(o, txt, btn))

        return sz

    def make_click_handler(self, o, txt, btn):
        def click_handler(e = None):
            on_action = getattr(o, 'on_action', None)
            action_url = getattr(o, 'action_url', None)

            perform_action = True

            if getattr(o, 'confirm', False) and getattr(o, 'should_confirm', lambda: True)():
                confirm_title = getattr(o, 'confirm_title', _('Are you sure?'))
                confirm_msg = getattr(o, 'confirm_text', _('Are you sure you want do this?'))
                default = getattr(o, 'confirm_default', True)

                if not gui.toolbox.yes_no_prompt(confirm_title, confirm_msg, default):
                    perform_action = False

            if perform_action:
                if on_action is not None:
                    on_action()

                if action_url is not None:
                    wx.LaunchDefaultBrowser(action_url)

                if getattr(o, 'say_thanks', False):
                    wx.MessageBox(_("Thank you for supporting Digsby."), _("Thank you!"))

            txt.Label = o.description
            btn.Label = o.action_text

        return click_handler

class SupportFrame(wx.Frame):
    def __init__(self, parent = None, **k):
        title = k.pop('title', _('Support Digsby'))
        style = k.pop('style', wx.DEFAULT_FRAME_STYLE & ~wx.RESIZE_BORDER & ~wx.MAXIMIZE_BOX)
        components = k.pop('components', None)
        if components is None:
            components = [o() for o in supportoptions.get_enabled()]
        wx.Frame.__init__(self, parent, title = title, style = style, **k)
        self.AutoLayout = True
        self._supportpanel = SupportPanel(components, self)
        self.Fit()

        try:
            import gui.skin as skin
            self.SetFrameIcon(skin.get('AppDefaults.TaskbarIcon'))
        except Exception:
            traceback.print_exc()

        self.CenterOnScreen()

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, e = None):
        self._supportpanel.OnClose()
        del self._supportpanel
        self.Destroy()

if __name__ == '__main__':
    a = wx.PySimpleApp()
    f = SupportFrame.MakeOrShow()
    a.MainLoop()
