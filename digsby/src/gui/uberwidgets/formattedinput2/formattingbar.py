'''
Button bar with text formatting options
'''

from gui.prototypes.fontdropdown import FontDropDown
from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.simplemenu import SimpleMenu, SimpleMenuItem
from gui.uberwidgets.UberEmotiBox import UberEmotiBox
from gui.uberwidgets.formattedinput2.fromattedinputevents import EVT_TEXT_FORMAT_CHANGED

import sys
import wx
import config

if config.platform == 'win':
    from cgui import EVT_SELECTION_CHANGED

from gui.uberwidgets.formattedinput2.toolbar import ToolBar, ToolBarSkinDefaults
from gui.prototypes.newskinmodule import NewSkinModule, SkinProxy

from common import setpref, pref

DEFAULT_SIZES = [8, 10, 12, 14, 18, 24, 36]

FormattingBarSkinDefaults = {
    'toolbarskin'           : lambda: None,
    'iconsize'              : lambda: 15,
    'fontdropdownwidth'     : lambda: 100,
    'sizedropdownwidth'     : lambda: 33,
    'icons.bold'            : lambda: wx.EmptyBitmap(1,1),
    'icons.italic'          : lambda: wx.EmptyBitmap(1,1),
    'icons.underline'       : lambda: wx.EmptyBitmap(1,1),
    'icons.foregroundcolor' : lambda: wx.EmptyBitmap(1,1),
    'icons.backgroundcolor' : lambda: wx.EmptyBitmap(1,1),
    'icons.emote'           : lambda: wx.EmptyBitmap(1,1),
}


class FormattingBar(ToolBar, NewSkinModule):

    initover = False

    def __init__(self, parent, textctrl, skinkey, formatOptions):

        ToolBar.__init__(self, parent, skinkey = None, alignment = wx.ALIGN_LEFT)

        self.SetSkinKey(skinkey, FormattingBarSkinDefaults)

        self.textctrl = textctrl
        if sys.platform.startswith("win"):
            textctrl.Bind(EVT_SELECTION_CHANGED, self.OnCursorMove)
        textctrl.Bind(EVT_TEXT_FORMAT_CHANGED, self.OnCursorMove)

        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)

        self.fontdd = FontDropDown(self, skinkey = self.skinTB['buttonskin'])
        self.fontdd.SetMenuSkinKey(self.skinTB["menuskin"])
        self.fontdd.Bind(wx.EVT_COMMAND_CHOICE_SELECTED, self.OnFontSelected)

        icons = self.icons

        self.msize = SimpleMenu(self, self.skinTB['menuskin'], maxheight = 10)
        self.msize.SetItems(self.GenSizeItems(DEFAULT_SIZES)) #TODO: None default sizes
#        self.msize.Bind(wx.EVT_COMMAND_CHOICE_SELECTED, self.OnSizeSelected)

        self.bsize = UberButton(self, -1, '10', menu = self.msize, type = 'menu')
        self.bsize.SetStaticWidth(self.skinFB['sizedropdownwidth'])
        self.msize.SetWidth(self.skinFB['sizedropdownwidth'])

        self.bbold = UberButton(self, -1, icon = icons['bold'], type = 'toggle')
        self.bbold.Bind(wx.EVT_TOGGLEBUTTON, self.OnBoldButton)

        self.bitalic = UberButton(self, -1, icon = icons['italic'], type="toggle")
        self.bitalic.Bind(wx.EVT_TOGGLEBUTTON, self.OnItalicButton)

        self.bunderline = UberButton(self, -1, icon = icons['underline'],  type="toggle")
        self.bunderline.Bind(wx.EVT_TOGGLEBUTTON, self.OnUnderlineButton)

        self.bcolor = UberButton(self, -1, icon = icons['foregroundcolor'] )
        self.bcolor.Bind(wx.EVT_BUTTON, self.OnColorButton)

        self.bbgcolor = UberButton(self,-1, icon = icons['backgroundcolor'])
        self.bbgcolor.Bind(wx.EVT_BUTTON, self.OnBGColorButton)

        self.bemote = UberButton(self, -1, icon = icons['emote'])
        self.bemote.Bind(wx.EVT_BUTTON, self.OnEmoteButton)

#        import pdb
#        pdb.set_trace()
        self.AddMany([self.fontdd,
                      self.bsize,
                      self.bbold,
                      self.bitalic,
                      self.bunderline,
                      self.bcolor,
                      self.bbgcolor,
                      self.bemote])


        self.initover = True
        self.EnableFormattingButtons(formatOptions)
        self.UpdateDisplay()

    def OnContextMenu(self, event):
        from gui.uberwidgets.umenu import UMenu
        m = UMenu(self)
        m.AddItem(_('Hide Formatting Bar'), callback = lambda: wx.CallAfter(setpref, 'messaging.show_formatting_bar', False))
        m.PopupMenu()

    def OnFontSelected(self, event):
        """
            Updates the button to the new font and applies it to the selection
            or calls ApplyStlye
        """
        self.textctrl.ApplyStyle(facename = self.fontdd.GetClientData(self.fontdd.GetSelection()).GetFaceName())


    def OnSizeSelected(self, item):
        """
            Updates the Size button to the new size and applies it to the selection
            or calls ApplyStyle
        """
        self.bsize.label = str(item.id)
        self.textctrl.ApplyStyle(pointsize = item.id)

    def OnBoldButton(self, event):
        self.textctrl.ApplyStyle(bold = event.EventObject.IsActive())

    def OnItalicButton(self, event):
        self.textctrl.ApplyStyle(italic = event.EventObject.IsActive())

    def OnUnderlineButton(self, event):
        self.textctrl.ApplyStyle(underline = event.EventObject.IsActive())

    def OnColorButton(self, event):
        oldtextcolor = self.textctrl.GetFormat().GetTextColour()
        self.textctrl.ApplyStyle(textcolor = wx.GetColourFromUser(self, oldtextcolor, _('Choose a foreground color')))

    def OnBGColorButton(self, event):
        oldbgcolor = self.textctrl.GetFormat().GetTextColour()
        self.textctrl.ApplyStyle(bgcolor = wx.GetColourFromUser(self, oldbgcolor, _('Choose a background color')))

    def OnEmoteButton(self, event):
        self.DisplayEmotibox(self.bemote.ScreenRect)

    def DisplayEmotibox(self, rect):
        import hooks
        hooks.notify('digsby.statistics.emoticons.box_viewed')
        ebox = self.GetEmotibox()
        # position and display the emotibox
        ebox.Display(rect)

    def GetEmotibox(self):
        'Shares the emoticon box between all instances of this class.'

        b = None
        old_name, new_name = getattr(self, '_emotipack_name', None), pref('appearance.conversations.emoticons.pack', type = unicode, default = u'default')
        self._emotipack_name = new_name

        try:
            b = self.__class__.emotibox
            if not wx.IsDestroyed(b):
                if old_name != new_name:
                    b.Destroy()
                elif b.Parent is not self:
                    b.Reparent(self)

        except AttributeError:
            pass

        if b is None or wx.IsDestroyed(b):
            from gui.imwin.emoticons import get_emoticon_bitmaps
            b = self.__class__.emotibox = UberEmotiBox(self, get_emoticon_bitmaps(self._emotipack_name), self.textctrl, maxwidth = 12)
        else:
            b.SetTextCtrl(self.textctrl)

        return b

    def OnCursorMove(self, event):

        event.Skip()
        wx.CallAfter(self.UpdateDisplay)

    def UpdateDisplay(self):
        if wx.IsDestroyed(self.textctrl):
            return

        selection = self.textctrl.GetSelection()
        if selection[0] != selection[1]:
            return

        textattr = self.textctrl.GetFormat()
        font = textattr.GetFont()

        facename = font.GetFaceName()
        self.fontdd.SetSelection(self.fontdd.FindString(facename, False))
        self.bsize.SetLabel(str(font.GetPointSize()))

        self.bbold.Active(font.GetWeight() == wx.FONTWEIGHT_BOLD)
        self.bitalic.Active(font.GetStyle() == wx.FONTSTYLE_ITALIC)
        self.bunderline.Active(font.GetUnderlined())


    def EnableFormattingButtons(self, enabledict):

        if enabledict is None:
            return

        default = enabledict['default'] if 'default' in enabledict else True

        #TODO: fontdd should be disableable
        buttons = [#('font', self.fontdd),
                   ('size',      self.bsize),
                   ('bold',      self.bbold),
                   ('italic',    self.bitalic),
                   ('underline', self.bunderline),
                   ('color',     self.bcolor),
                   ('bgcolor',   self.bbgcolor),
                   ('emote',     self.bemote)]

        for key, button in buttons:
            button.Enable(enabledict[key] if key in enabledict else default)

    def GenSizeItems(self, sizes = DEFAULT_SIZES):
        """
            Sets the list of selectable sizes
            If not set sizes default to ['8', '10', '12', '14', '18', '24', '36']
        """
        return [SimpleMenuItem([str(size)], id=size, method = self.OnSizeSelected) for size in sizes]

    def DoUpdateSkin(self, skin):

        self.skinFB = skin

        ToolBar.DoUpdateSkin(self, SkinProxy(skin['toolbarskin'], ToolBarSkinDefaults))

        icons = self.icons = {}
        icons['bold'] = skin['icons.bold']
        icons['italic'] = skin['icons.italic']
        icons['underline'] = skin['icons.underline']
        icons['foregroundcolor'] = skin['icons.foregroundcolor']
        icons['backgroundcolor'] = skin['icons.backgroundcolor']
        icons['emote'] = skin['icons.emote']

        iconsize = skin['iconsize']
        for key in icons:
            if icons[key] is not None:
                icons[key] = icons[key].Resized(iconsize)

        if self.initover:
            self.bsize.SetStaticWidth(skin['sizedropdownwidth'])
            self.msize.SetWidth(skin['sizedropdownwidth'])

            self.bbold.SetIcon(icons['bold'])
            self.bitalic.SetIcon(icons['italic'])
            self.bunderline.SetIcon(icons['underline'])
            self.bcolor.SetIcon(icons['foregroundcolor'])
            self.bbgcolor.SetIcon(icons['backgroundcolor'])
            self.bemote.SetIcon(icons['emote'])

    def GetSkinProxy(self):
        return self.skinFB if hasattr(self, 'skinFB') else None
