'''
Input area with formatting bar
'''

from gui.uberwidgets.formattedinput2.formattingbar import FormattingBar
from gui.uberwidgets.formattedinput2.fontutil import StorageToFont, StyleToStorage


import wx
import config
import cgui

from gui.uberwidgets.formattedinput2.FormattedExpandoTextCtrl import FormattedExpandoTextCtrl, FormattedTextCtrl, EVT_ETC_LAYOUT_NEEDED

wxMSW = 'wxMSW' in wx.PlatformInfo

if wxMSW:
    from gui.toolbox import set_rich_layoutdirection

import logging
log = logging.getLogger('formattedinput')

class FormattedInput(cgui.SimplePanel):
    def __init__(self,
                 parent,
#                 pos       = wx.DefaultPosition,
#                 size      = wx.DefaultSize,
                 value     = '',
                 autosize = True,
                 formatOptions = None,
                 multiFormat = True,
                 showFormattingBar = True,
                 format = None,
                 rtl = False,
                 skin = None,
                 validator = wx.DefaultValidator,):

        cgui.SimplePanel.__init__(self, parent)

        self.skin = skin
        self.formatOptions = formatOptions

        sizer = self.Sizer = wx.BoxSizer(wx.VERTICAL)

        if autosize:
            tc = self.tc = FormattedExpandoTextCtrl(self, value = value, multiFormat = multiFormat, validator=validator)
            tc.SetMaxHeight(100)
        else:
            tc = self.tc = FormattedTextCtrl(self, value = value, multiFormat = multiFormat, validator=validator)

        if config.platform == 'mac':
            self.tc.MacCheckSpelling(True)

        if format is not None:
            if isinstance(format, wx.TextAttr):
                tc.SetFormat_Single(format)
            else:
                font, fgc, bgc =  StorageToFont(format)
                tc.SetFormat_Single(wx.TextAttr(wx.Color(*fgc), wx.Color(*bgc), font))


        tc.Bind(wx.EVT_KEY_DOWN, self.OnKey)

        self.Bind(EVT_ETC_LAYOUT_NEEDED, self.OnExpandEvent)

        self.fbar = None

        inputsizer = self.inputsizer = wx.BoxSizer(wx.HORIZONTAL)

        inputsizer.Add(tc, 1, wx.EXPAND)

        sizer.Add(inputsizer, 1, wx.EXPAND)

        if showFormattingBar:
            self.CreatFormattingBar()

        self.SetFormattedValue = self.tc.SetFormattedValue
        self.GetFormattedValue = self.tc.GetFormattedValue


    def OnKey(self, event):
        ctrlIsDown = event.Modifiers == wx.MOD_CONTROL

        if ctrlIsDown:

            font = self.tc.GetFormat().GetFont()

            def IsEnabled(option):
                if self.formatOptions is None:
                    return True

                fO = self.formatOptions
                return fO[option] if option in fO else fO['default'] if 'default' in fO else True

            keycode = event.KeyCode
            if keycode == ord('B'):
                if IsEnabled('bold'):
                    self.tc.ApplyStyle(bold = font.GetWeight() != wx.FONTWEIGHT_BOLD)
                return
            elif keycode == ord('I'):
                if IsEnabled('italic'):
                    self.tc.ApplyStyle(italic = font.GetStyle() != wx.FONTSTYLE_ITALIC)
                return
            elif keycode == ord('U'):
                if IsEnabled('underline'):
                    self.tc.ApplyStyle(underline = not font.GetUnderlined())
                return

            if wxMSW:
                # make Ctrl+R and Ctrl+L modify the RTL setting of the rich edit
                # control, not just the alignment; disable center alignment.
                if keycode == ord('R'):
                    self.tc.SetRTL(True)
                    return
                elif keycode == ord('L'):
                    self.tc.SetRTL(False)
                    return
                elif keycode == ord('E'):
                    return

        return event.Skip()

    def OnExpandEvent(self, event):
        height = (self.fbar.BestSize.height if self.FormattingBarIsShown() else 0) + self.tc.MinSize.height

        self.MinSize = wx.Size(-1, height)

        wx.CallAfter(self.Layout)

    def FormattingBarIsShown(self):
        return self.fbar is not None and self.fbar.IsShown()

    def CreatFormattingBar(self):
        fbar = self.fbar = FormattingBar(self, self.tc, self.skin, self.formatOptions)
        self.Sizer.Insert(0, fbar, 0, wx.EXPAND)
        wx.CallAfter(fbar.UpdateDisplay)

    def ShowFormattingBar(self, show = True):

        hasFBar = self.fbar is not None

        if hasFBar:
            self.fbar.Show(show)
        elif show:
            self.CreatFormattingBar()

        self.tc.ForceExpandEvent()

    def DoUpdateSkin(self, skin):
        self.formattingbar.SetSkinKey(self._skinkey)

    def Clear(self):
        """
            Clears the text from the text field
        """
        tc = self.tc

        if 'wxMSW' in wx.PlatformInfo:
            # Clear() removes any alignment flags that are set in the text control, so
            # reset them
            textattr = tc.GetFormat()
            alignment = cgui.GetRichEditParagraphAlignment(tc)
            tc.Clear()
            if cgui.GetRichEditParagraphAlignment(tc) != alignment:
                cgui.SetRichEditParagraphAlignment(tc, alignment)
            tc.SetFormat(textattr)
        else:
            tc.Clear()


    def __repr__(self):
        try:
            return '<%s under %r>' % (self.__class__.__name__, self.Parent)
        except Exception:
            return object.__repr__(self)

    def GetValue(self):
        return self.tc.GetValue()

    def SetValue(self, value):
        return self.tc.SetValue(value)

    Value = property(GetValue, SetValue)

    def SetFocus(self):
        self.tc.SetFocus()

    def ShowModalFontDialog(self, e = None):
        '''
        Uses the native Mac font dialog to allow the user to select a font
        and a color.
        '''
        diag = wx.FontDialog(self, self.FontData)
        if wx.ID_OK == diag.ShowModal():
            font_data = diag.GetFontData()
            font = font_data.GetChosenFont()
            color = font_data.GetColour()

            tc = self.tc
            attrs = tc.GetDefaultStyle()
            if color.IsOk():
                attrs.SetTextColour(color)
            if font.IsOk():
                attrs.SetFont(font)
            tc.SetDefaultStyle(attrs)

            tc.Refresh()
            tc.SetFocus()

    def CreateFontButton(self, parent, label = _('Set Font...')):
        '''
        Create a small button that will spawn a font dialog for setting
        the properties of this text control.
        '''
        font_button = wx.Button(parent, -1, label)
        font_button.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)
        font_button.Bind(wx.EVT_BUTTON, self.ShowModalFontDialog)
        return font_button

    @property
    def FontData(self):
        d = wx.FontData()
        tc = self.tc
        d.SetInitialFont(tc.GetFont())
        d.SetColour(tc.GetForegroundColour())
        return d

    @property
    def Format(self):
        return StyleToStorage(self.tc.GetDefaultStyle())
