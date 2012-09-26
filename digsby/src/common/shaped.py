from common.MultiImage import MultiImage
import yaml
import util

import  wx


#----------------------------------------------------------------------

class TestFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Shaped Window",
                         style = wx.FRAME_SHAPED | wx.SIMPLE_BORDER |
                                 wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP )

        self.hasShape = False
        self.delta = (0,0)

        [self.Bind(e, m) for e,m in [
         (wx.EVT_LEFT_DCLICK,   self.OnDoubleClick),
         (wx.EVT_LEFT_DOWN,     self.OnLeftDown),
         (wx.EVT_LEFT_UP,       self.OnLeftUp),
         (wx.EVT_MOTION,        self.OnMouseMove),
         (wx.EVT_RIGHT_UP,      self.OnExit),
         (wx.EVT_PAINT,         self.OnPaint),
        ]]

        from skins import images as imgmngr
        from skins import skins

        f = file("../../res/skins/halloween/skin.yaml")
        images = util.to_storage(yaml.load(f)).Images
        f.close()

        skins.res_path = "../../res/skins/halloween"

        mimg = MultiImage(images)

        from gui.uberwidgets.UberBar import UberBar as UberBar
        from gui.uberwidgets.UberButton import UberButton as UberButton

        self.content = wx.Panel(self)

        innerSizer = wx.BoxSizer(wx.HORIZONTAL)


        self.bsizer = wx.BoxSizer(wx.VERTICAL)
        self.menu = UberBar(self.content)
        [self.menu.add(UberButton(self.menu, -1, s))
                       for s in 'Digsby Edit Help'.split()]

        self.bsizer.Add(self.menu, 0, wx.EXPAND, 0)
        self.content.SetSizer(self.bsizer)

        self.hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.hsizer.Add(self.content, 1, wx.EXPAND | wx.ALL, 140)
        self.SetSizer(self.hsizer)

        w, h = 400, 400
        self.SetClientSize( (w, h) )
        dc = wx.ClientDC(self)
        destbitmap = wx.EmptyBitmap(w, h)

        temp_dc = wx.MemoryDC();
        temp_dc.SelectObject(destbitmap);
        mimg.draw(temp_dc, wx.Rect(0,0,w,h))
        temp_dc.SelectObject(wx.NullBitmap)
        destbitmap.SetMask(wx.Mask(destbitmap, wx.BLACK))
        self.bmp=destbitmap

        if wx.Platform != "__WXMAC__":
            # wxMac clips the tooltip to the window shape, YUCK!!!
            self.SetToolTipString("Right-click to close the window\n"
                                  "Double-click the image to set/unset the window shape")

        if wx.Platform == "__WXGTK__":
            # wxGTK requires that the window be created before you can
            # set its shape, so delay the call to SetWindowShape until
            # this event.
            self.Bind(wx.EVT_WINDOW_CREATE, self.SetWindowShape)
        else:
            # On wxMSW and wxMac the window has already been created, so go for it.
            self.SetWindowShape()

        dc.DrawBitmap(destbitmap, 0,0,True)




    def SetWindowShape(self, *evt):
        # Use the bitmap's mask to determine the region
        r = wx.RegionFromBitmap(self.bmp)
        self.hasShape = self.SetShape(r)


    def OnDoubleClick(self, evt):
        if self.hasShape:
            self.SetShape(wx.Region())
            self.hasShape = False
        else:
            self.SetWindowShape()


    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        dc.DrawBitmap(self.bmp, 0,0, True)

    def OnExit(self, evt):
        self.Close()


    def OnLeftDown(self, evt):
        self.CaptureMouse()
        x, y = self.ClientToScreen(evt.GetPosition())
        originx, originy = self.GetPosition()
        dx = x - originx
        dy = y - originy
        self.delta = ((dx, dy))


    def OnLeftUp(self, evt):
        if self.HasCapture():
            self.ReleaseMouse()


    def OnMouseMove(self, evt):
        if evt.Dragging() and evt.LeftIsDown():
            x, y = self.ClientToScreen(evt.GetPosition())
            fp = (x - self.delta[0], y - self.delta[1])
            self.Move(fp)

if __name__ == '__main__':
    import sys,os
    app = wx.PySimpleApp()
    win = TestFrame(None)
    win.Show(True)
    app.MainLoop()

