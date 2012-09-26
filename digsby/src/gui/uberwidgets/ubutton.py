import wx

from wx import Size
from gui.skin import get as skinget
from gui.uberwidgets.ucontrol import UControl
from time import time

class UButton(UControl):
    def __init__(self, parent, id = -1,
                 skinkey = 'Button',
                 label = '',
                 bitmap = None,
                 bitmapSize = None,
                 menuMode = False,    # left down == activate
                 callback = None,     # shortcut for button.Bind(wx.EVT_BUTTON, ...
                 style = wx.BU_LEFT   # see other flags like wx.BU_EXACTFIT
                 ):

        self.bitmap     = bitmap
        self.bitmapSize = bitmapSize
        self.Active     = False
        self.menuMode   = menuMode

        UControl.__init__(self, parent, skinkey, id, label,
                          style = style | wx.NO_BORDER | wx.FULL_REPAINT_ON_RESIZE)

        self.BindHover(self.OnHover)
        self.BindFocus(self.OnFocus)

        Bind = self.Bind
        Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        Bind(wx.EVT_LEFT_UP,   self.OnLeftUp)
        Bind(wx.EVT_KEY_DOWN,  self.OnKeyDown)
        Bind(wx.EVT_KEY_UP,    self.OnKeyUp)
        Bind(wx.EVT_SIZE,      lambda e: self.Cut(self.BackgroundRegion.GetBitmap(e.Size)))


        self.UpdateSkin()

        if 'wxMSW' in wx.PlatformInfo:
            self.Bind(wx.EVT_LEFT_DCLICK,  self.OnLeftDown)

        if callback is not None:
            self.Bind(wx.EVT_BUTTON, callback)

    def __repr__(self):
        return '<%s "%s">' % (self.__class__.__name__, self.LabelText)

    def OnFocus(self, focused):
        if self._native and focused:
            self._nativebutton.SetFocus()

        if self.Active and not focused:
            self.Active = False
            self.ChooseBG()

        self.Refresh(False)

    def Enable(self, val):
        UControl.Enable(self, val)
        self.ChooseBG()
        self.Refresh(False)

    def OnKeyDown(self, e):
        e.Skip()
        if self._native or not self.Enabled or not self.IsShown(): return

        if e.KeyCode == wx.WXK_SPACE: self.OnLeftDown()

    def OnKeyUp(self, e):
        e.Skip()
        if self._native or not self.Enabled or not self.IsShown(): return

        c = e.KeyCode
        if c == wx.WXK_SPACE: self.OnLeftUp()

    def OnLeftDown(self, e = None):
        if e: e.Skip()
        if self._native or not self.Enabled or not self.IsShown(): return

        if not self.menuMode:
            if isinstance(e, wx.MouseEvent):
                self.CaptureMouse()

            if self.FindFocus() is not self:
                self.SetFocus()
        else:
            self._fire()

        self.Active = True
        self.ChooseBG()
        self.Refresh(False)

    def OnLeftUp(self, e = None, fire = True):
        if e: e.Skip()
        if self._native or not self.IsEnabled(): return

        while self.HasCapture():
            self.ReleaseMouse()

        if self.Active and fire and not self.menuMode: self._fire()
        self.Active = False
        self.ChooseBG()
        self.Refresh(False)

    def OnHover(self, hover):
        if self.HasCapture():
            self.Active = hover

        self.ChooseBG()
        self.Refresh(False)

    def ChooseBG(self):
        bgs = self.bgs
        if not self.IsEnabled():
            bg = 'disabled'
        else:
            bg = ''
            if self.menuMode:
                if self.Active or self.Hover: bg = 'hover'
            else:
                if self.Active: bg += 'active'
                if self.Hover:  bg += 'hover'
            if not bg:
                bg =  'normal'

        newbg = getattr(bgs, bg)

        if newbg is not getattr(self, 'BackgroundRegion', None):
            self.BackgroundRegion = newbg

        return bg


    def UpdateSkin(self):
        UControl.UpdateSkin(self)

        if skinget('Button.Native', False):
            self.Native = True
        else:
            self.bgs = skinget('Button.Backgrounds')
            self.ChooseBG()

        font = skinget('Button.Font', None)
        if isinstance(font, wx.Font): self.Font = font


    def GetDefaultAttributes(self):
        return wx.Button.GetClassDefaultAttributes()

    def GetContentSize(self):
        dc      = wx.ClientDC(self)
        dc.Font = self.Font
        size    = Size(*dc.GetTextExtent(self.LabelText))
        b       = self.bitmap
        s       = self.WindowStyle
        padding = self.Padding

        if b is not None:
            imgw, imgh = self.bitmapSize if self.bitmapSize is not None else (b.Width, b.Height)

            if s & wx.BU_LEFT or s & wx.BU_RIGHT:
                size.IncBy(padding.width + imgw, 0)
                size = Size(size.width, max(imgh, size.height))
            else:
                size.IncBy(0, padding.height + imgh)
                size = Size(max(imgw, size.width), size.height)

        size.IncBy(padding.width * 2, padding.height * 2)

        if not (s & wx.BU_EXACTFIT):
            size = Size(max(size.width, 65), max(size.height, 17))

        return size


    def _fire(self, e = None):
        if e: e.Skip()

        evt = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.Id)
        evt.SetTimestamp(time())
        evt.SetEventObject(self)

        self.AddPendingEvent(evt)

    def Draw(self, dc, rect):
        padding = self.Padding

        rect.Deflate(padding.x, padding.y)

        dc.Font = self.Font

        if not self.IsEnabled():
            fg = 'disabled'
        else:
            fg = ''
            if self.Active: fg += 'active'
            if self.Hover:  fg += 'hover'
            if not fg:      fg = 'normal'

        dc.SetTextForeground(self.skin.fontcolors.get(fg, self.ForegroundColour))

        s = self.WindowStyle
        bitmap, bitmapSize = self.Bitmap, self.BitmapSize
        bitmapSize = self.BitmapSize

        if self.FindFocus() is self and not self.menuMode:
            self.DrawFocusRect(dc, rect)

        if bitmap is not None:
            bitmap = bitmap.Resized(self.BitmapSize)

            if s & wx.BU_LEFT:
                dc.DrawBitmap(bitmap, rect.Left, rect.Top + rect.Height / 2 - bitmapSize.height / 2)
                rect.Subtract(left = bitmapSize.width + padding.width)
            elif s & wx.BU_RIGHT:
                dc.DrawBitmap(bitmap, rect.Right - bitmapSize.width, rect.Top + rect.Height / 2 - bitmapSize.height / 2)
                rect.Subtract(right = bitmapSize.width + padding.width)

        dc.DrawLabel(self.LabelText, rect, indexAccel = self.Label.find('&'),
                     alignment = wx.ALIGN_CENTER)

    def AcceptsFocus(self):
        return self.IsShown() and self.IsEnabled() and not self.menuMode

    def SetLabel(self, newLabel):
        oldLabel = self.Label

        i = oldLabel.find('&')
        if i != -1 and i < len(oldLabel) - 1 and oldLabel[i+1] != '&':
            self.KeyCatcher.RemoveDown('alt+%s' % newLabel[i+1], oldLabel[i+1])

        i = newLabel.find('&')
        if i != -1 and i < len(newLabel) - 1 and newLabel[i+1] != '&':
            print self, 'adding alt+%s' % newLabel[i+1]
            self.KeyCatcher.OnDown('alt+%s' % str(newLabel[i+1]), self._fire)

        UControl.SetLabel(self, newLabel)

    Label = property(UControl.GetLabel, SetLabel)

    def SetBitmap(self, bitmap):
        self.bitmap = bitmap
        self.Refresh(False)

    Bitmap = property(lambda self: self.bitmap, SetBitmap)

    #
    # bitmap size: defaults to None if you haven't set a bitmap
    #              becomes the image size if you set a bitmap
    #              can be set to some other size
    #

    def SetBitmapSize(self, size):
        self.bitmapSize = size

    def GetBitmapSize(self):
        if self.bitmapSize is not None:
            return self.bitmapSize
        elif self.bitmap is not None:
            return Size(self.bitmap.Width, self.bitmap.Height)
        else:
            return None

    BitmapSize = property(GetBitmapSize, SetBitmapSize)

    def SetNative(self, native):
        if native and not self._native:
            print self.Id
            self._nativebutton = wx.Button(self, self.Id, label = self.Label, size = self.Size, pos = self.Position,
                                           style = self.WindowStyle)
            self._nativebutton.SetFocus()

        elif not native and self._native:
            self._nativebutton.Destroy()

        if self._native != native:
            self.Parent.Layout()
            self.Parent.Refresh()

        self._native = native

    Native = property(lambda self: self._native, SetNative)

if __name__ == '__main__':
    from tests.testapp import testapp
    from gui import skin
    a = testapp('../../..')

    #from util import trace
    #trace(UButton)

    f = wx.Frame(None, style = wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)
    p = wx.Panel(f)
    p.Sizer = s = wx.BoxSizer(wx.VERTICAL)
    bitmap = skin.load_bitmap('error.png')

    b = UButton(p, label = '&Digsby', bitmap = bitmap); s.Add(b)

    b.Bind(wx.EVT_BUTTON, lambda e, but=b: setattr(but, 'Native', not getattr(but, 'Native')))

    b = UButton(p, label = 'Digsby &Rocks', bitmap = bitmap); s.Add(b)
    b = UButton(p, label = '&Exact Fit', style = wx.BU_EXACTFIT); s.Add(b)
    b = UButton(p, label = '&Cancel'); s.Add(b)
    b = UButton(p, label = 'Disab&led'); s.Add(b); b.Enable(False)

    b = UButton(p, label = 'Digs&by', bitmap = bitmap, style = wx.BU_RIGHT, menuMode = True); s.Add(b, 0, wx.EXPAND)
    b = UButton(p, label = 'Digsby Rocks', bitmap = bitmap, style = wx.BU_RIGHT); s.Add(b, 0, wx.EXPAND)
    b = UButton(p, label = '&OK'); s.Add(b, 0, wx.EXPAND)
    b = UButton(p, label = 'Cancel'); s.Add(b, 0, wx.EXPAND)

    s.AddSpacer((30,30))

    from gui.uberwidgets.UberButton import UberButton

    hs = wx.BoxSizer(wx.HORIZONTAL)
    for x in xrange(4):
        b = UberButton(p, label = 'UberButton'); hs.Add(b, 1, wx.EXPAND)

    s.Add(hs, 0, wx.EXPAND)

    def printsrc(e): print e.EventObject
    p.Bind(wx.EVT_BUTTON, printsrc)

    f.Show()
    a.MainLoop()