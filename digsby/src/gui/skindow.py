'''
skindow.py

Skinned windows.
'''

import wx, util
from gui import skin, MultiImage
from gui.toolbox import rect_with_negatives

class Skindow( wx.Frame ):

    framestyles = {True:  wx.FRAME_SHAPED | wx.SIMPLE_BORDER,
                   False: wx.DEFAULT_FRAME_STYLE}

    def __init__(self, parent, name, content_panel = None, use_skin = True, **kws ):
        if parent is not None and not isinstance(parent, wx.Window):
            raise TypeError("first argument to Skindow __init__ is a wxWindow parent")

        wx.Frame.__init__( self, parent, style = self.framestyles[use_skin], **kws )

        self.margins = skin.get('%s.content' % name)
        self.content_pane = wx.Panel(self)
        self.sizer = wx.BoxSizer()
        self.content_pane.SetSizer(self.sizer)

        if not isinstance(name, (str, unicode)):
            raise TypeError('second argument name must be a string')
        self.name = name

        self.skin_events = [
            ( wx.EVT_SIZE, self.on_size ),
            ( wx.EVT_PAINT, self.on_paint ),
            ( wx.EVT_LEFT_UP, self.OnLeftUp ),
            ( wx.EVT_LEFT_DOWN, self.on_left_down ),
            ( wx.EVT_MOTION, self.on_motion ),
            ( wx.EVT_ERASE_BACKGROUND, lambda e: None ), # reduce flickering
        ]

        self.Bind(wx.EVT_CLOSE, lambda e: self.Destroy())

        self.set_skinned(use_skin)

    def set_skinned(self, skinned = True):
        if skinned:
            self.multi = skin.get('%s.images' % self.name)

            [self.Bind( e, m ) for e, m in self.skin_events]
            self.cdc = wx.ClientDC( self )
            self.sizing = False
            self.on_size()
            self.SetWindowShape()
        else:
            [self.Unbind(e) for e,m in self.skin_events]
            self.margins = (0,0,-1,-1)

            if self.GetWindowStyleFlag() == self.framestyles[True]:
                self.SetShape(wx.Region().Union(self.content_pane.GetRect()))

        self.SetWindowStyleFlag( self.framestyles[skinned] )
        self.Refresh()

    def get_skinned(self):
        return self.GetWindowStyleFlag() == self.framestyles[True]

    skinned = property(get_skinned, set_skinned)

    def set_content(self, content):
#        if self.content: self.sizer.Remove(self.content)
#        self.sizer.Add(content)
#        self.content = content
        self.Refresh()

    def on_size( self, e=None ):
        m = rect_with_negatives(self.margins, self.GetSize())
        self.content_pane.SetPosition(m[:2])
        self.content_pane.SetSize(m[2:])
        #self.Update()
        #self.Refresh()
        if e: e.Skip( True )

    def on_paint( self, e=None ):
        dc = wx.AutoBufferedPaintDC( self )
        self.multi.Draw(dc, wx.Rect(0,0,*self.GetClientSizeTuple()))
        self.SetShape(self.multi.region)

    def SetWindowShape( self, *evt ):
        # Use the bitmap's mask to determine the region
        new = (w, h) = self.GetClientSizeTuple()

        if hasattr(self.multi, 'region'):
            print '%r has a region: %r' %(self.multi, self.multi.region)
            self.hasShape = self.SetShape( self.multi.region )

    def on_left_down( self, evt ):
        self.CaptureMouse()
        if 'dragger' in self.multi and wx.Rect( *self.multi.tag_rect( 'dragger' ) ).Contains( evt.GetPosition() ):
            self.orig = self.ClientToScreen( evt.GetPosition() )
            self.origsize = self.GetSize()
            self.click_state = 'resizing'
        else:
            self.click_state = 'moving'
            x, y             = self.ClientToScreen( evt.GetPosition() )
            originx, originy = self.GetPosition()
            self.delta       = ( ( x - originx, y - originy ) )


    def OnLeftUp( self, evt ):
        self.on_size()
        if self.HasCapture():
            self.ReleaseMouse()

    def on_motion( self, evt ):

        if 'dragger' in self.multi.tags:
            if wx.Rect( *self.multi.tag_rect( 'dragger' ) ).Contains( evt.GetPosition() ):
                self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENWSE))
            else:
                self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))

        if evt.Dragging() and evt.LeftIsDown():
            x, y = self.ClientToScreen( evt.GetPosition() )
            if self.click_state == 'resizing':
                self.method_sizing()
                if not self.sizing:
                    self.sizing = True
                    dx, dy = x - self.orig[0], y - self.orig[1]
                    self.SetSize( ( self.origsize[0] + dx, self.origsize[1] + dy ) )
                    self.sizing = False
            elif self.click_state == 'moving':
                fp = (x - self.delta[0], y - self.delta[1])
                self.Move( fp )

    def method_sizing(self):
        pass

if __name__ == '__main__':
    import util
    import windowfx


    app = wx.PySimpleApp()
    from gui import skininit
    skininit('../../res','halloween')


    frame = Skindow( None,'IMWin', title='Skindow Test' )

    from uberwidgets.UberBook import SamplePanel
    frame.set_content(SamplePanel(frame.content, 'orange'))


    windowfx.fadein( frame )
    app.SetTopWindow( frame )
    util.profile(app.MainLoop)
