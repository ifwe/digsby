'''
The emoticon dropdown in the IM window.
'''

from __future__ import with_statement

import os.path
import math
import wx

from gui import skin
from gui.skin.skinobjects import Margins
from gui.toolbox.imagefx import wxbitmap_in_square
from gui.toolbox import Monitor, AutoDC
from wx import TextCtrl

UberEmotiBase = wx.PopupTransientWindow

class UberEmotiBox(UberEmotiBase):
    """
    This is a box that shows a preview for the available emoticons and allows insertion by click.
    """
    def __init__(self, parent, emoticons, textctrl, maxwidth = 7, minwidth = 4):
        """
        parent - is required by PopupTransientWindow,
        also will likely be used to know what conversation the emoticon belongs to

        emoticons - [(bitmap, ":) :-) :]"), (bitmap2, ":( :-( :["), ...]
        """
        UberEmotiBase.__init__(self, parent, style=wx.NO_BORDER)
        self.maxwidth = maxwidth
        self.minwidth = minwidth

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.SetExtraStyle(wx.WS_EX_PROCESS_IDLE)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.UpdateSkin()

        self.SetTextCtrl(textctrl)

        # create and layout protocol specific emoticons
        if emoticons != getattr(self, 'emoticons', None):
            self.emoticons = emoticons
            self.DestroyChildren()
            self.pemoticons, pwidth, pheight = self.Arrange(self, emoticons)

        # Set size of box to fit content
        self.lesssize = (pwidth, pheight)
        self.SetSize(self.lesssize)

    def SetTextCtrl(self, textctrl):
        self.textctrl = textctrl

    def UpdateSkin(self):
        skin_elements = [
            ('padding', 'padding',       lambda: wx.Point(3, 3)),
            ('margins', 'margins',       skin.ZeroMargins),
            ('esize',   'emoticonsize',  19),
            ('espace',  'emoticonspace', 23),
            ('bg',      'backgrounds.window', None),
        ]

        for attr, skinattr, default in skin_elements:
            setattr(self, attr, skin.get('emotibox.' + skinattr, default))

    def Arrange(self, parent, emots):
        """
        Calculates the layout based on the passed in parameters
        Creates the emoticons
        Returns a list of the emoticons, and width and height or the layout

        parent - what the emoticons should be drawn in
        emots - the emoticons to be drawn in said space
        """

        # calculate squarest layout
        width = round(math.sqrt(len(emots)))
        if width < self.minwidth: width = self.minwidth
        if width > self.maxwidth: width = self.maxwidth

        size = self.espace
        padding = self.padding
        margins = self.margins
        cx = padding.x + margins.left
        cy = padding.y + margins.top

        emoticons = []
        count = 0

        for emot in emots:
            emoticons.append(Emoticon(parent, emot, (cx, cy)))

            cx += size + padding.x
            count += 1
            if count == width:
                cx=padding.x
                cy += size + padding.y
                count = 0
        if cx != padding.x:
            cy += size + padding.y

        across = width * (size + padding.x) + padding.x + margins.x
        cy += margins.bottom

        if cy < across:
            cy = across

        return emoticons, across, cy

    def OnPaint(self, event):
        dc = AutoDC(self)
        self.bg.Draw(dc, self.ClientRect)

    def Display(self,rect):
        'Set Position and popup'

        pos = rect.BottomLeft
        newrect = wx.RectPS(pos, self.Size)

        screenrect = Monitor.GetFromRect(newrect).ClientArea

        if newrect.bottom > screenrect.bottom:
            pos.y -= rect.height + self.Size.height
        if newrect.right > screenrect.right:
            pos.x += rect.width - self.Size.width

        self.SetPosition(pos) # Position property doesn't work for PopTransWin
        self.Popup()


class Emoticon(wx.Window):
    '''
    An object thats a visual and interactive representation of an emoticon with a tooltip
    '''

    def __init__(self, parent, emot, pos):
        """
        emote - bitmap and keys
        pos - where to draw
        size - how big
        """
        wx.Window.__init__(self, parent, pos = pos)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        events = [(wx.EVT_PAINT,        self.OnPaint),
                  (wx.EVT_ENTER_WINDOW, self.OnMouseInOrOut),
                  (wx.EVT_LEAVE_WINDOW, self.OnMouseInOrOut),
                  (wx.EVT_LEFT_UP,      self.OnLeftUp)]

        for evt, meth in events:
            self.Bind(evt, meth)

        imgpath, self.keys = emot
        self.SetToolTipString('   '.join(self.keys))

        # TODO: load these more lazily
        self.emote = None
        try:
            bitmap = wx.Bitmap(imgpath)
            if bitmap.Ok():
                self.emote = bitmap
        except Exception:
            from traceback import print_exc; print_exc()

        self.UpdateSkin()

    def UpdateSkin(self):
        'Updates local skin references'

        size = skin.get('emotibox.emoticonspace', 24)
        self.Size = wx.Size(size, size)
        esize = skin.get('emotibox.maxemoticonsize', 16)
        self.normalbg = skin.get('emotibox.backgrounds.emoticon', None)
        self.hoverbg = skin.get('emotibox.backgrounds.hover', None)

        emote = self.emote
        if emote is not None:
            self.bitmap = emote.ResizedSmaller(esize)
        else:
            self.bitmap = None


    def OnPaint(self,event):
        dc = wx.AutoBufferedPaintDC(self)

        rect = wx.RectS(self.Size)

        if wx.FindWindowAtPointer() is self:
            self.hoverbg.Draw(dc, rect)
        else:
            self.normalbg.Draw(dc, rect)

        W, H = self.GetSize()
        w, h = self.bitmap.GetSize()

        # drawing it centered on the box
        if self.bitmap is not None:
            dc.DrawBitmap(self.bitmap, W/2 - w/2, H/2 - h/2, True)

    def OnMouseInOrOut(self, event):
        'mouse over highlighting'

        event.Skip()
        self.Refresh()

    def OnLeftUp(self, event):
        'What to do when an emote is clicked.'

        import hooks
        hooks.notify('digsby.statistics.emoticons.chosen')

        textctrl = self.Parent.textctrl
        ip = textctrl.InsertionPoint

        if ip != 0 and textctrl.Value[ip-1] and textctrl.Value[ip-1] != ' ':
            textctrl.WriteText(' ')

        textctrl.WriteText(''.join([self.keys[0], ' ']))

        self.Parent.Dismiss()
        self.Parent.textctrl.SetFocus()
