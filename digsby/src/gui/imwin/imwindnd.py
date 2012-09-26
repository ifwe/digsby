import wx
import util
from gui import contactdialogs

class ImWinDropTarget( wx.PyDropTarget ):
    def __init__(self, parent):
        wx.PyDropTarget.__init__( self )
        self.dragged = wx.DataObjectComposite()
        self.imwin = parent

        # This drop target will receive certain types of draggable objects.
        import contacts.contactsdnd as contactsdnd
        drag_types = dict(file   = wx.FileDataObject(),
                          text   = wx.TextDataObject(),
                          bitmap = wx.PyBitmapDataObject(),
                          blist_item = contactsdnd.dataobject())

        for dt, dobjs in drag_types.iteritems():
            setattr(self.dragged, dt, dobjs)

        # Add to the wx.DataObjectComposite item, and set as our data object.
        for v in drag_types.itervalues():
            self.dragged.Add(v)

        self.SetDataObject( self.dragged )

    def OnEnter(self, x, y, d): return d
    def OnDrop(self, x, y): return True
    def OnDragOver(self, x, y, d): return wx.DragMove

    def OnData(self, x, y, d):
        if not self.GetData():
            return

        dragged = self.dragged
        dropped = util.Storage(files  = dragged.file.GetFilenames(),
                               bitmap = dragged.bitmap.GetBitmap(),
                               text   = dragged.text.GetText(),
                               blist_item = dragged.blist_item.GetData())

        import contacts.contactsdnd as contactsdnd

        #print 'format count', dragged.GetFormatCount()
        #print 'is supported', dragged.IsSupported(contactsdnd.dataformat())
        #print 'BLIST_ITEM', repr(dropped.blist_item)

        if dropped.files:
            self.imwin.Top.Raise()
            contactdialogs.send_files(self.imwin, self.imwin.convo.buddy, dropped.files)
            return True
        if dropped.bitmap:
            return True
        if dropped.text:
            self.imwin.input_area.SetValue(dropped.text)
            self.imwin.input_area.tc.SetSelection(-1, -1)
            return True

        return False
