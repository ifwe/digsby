import wx
from logging import getLogger; log = getLogger('dnd')

drag_types = {wx.DF_FILENAME: ('files',  wx.FileDataObject, wx.FileDataObject.GetFilenames),
              wx.DF_TEXT:     ('text',   wx.TextDataObject, wx.TextDataObject.GetText),
              wx.DF_BITMAP:   ('bitmap', wx.PyBitmapDataObject, wx.PyBitmapDataObject.GetBitmap)
}


class SimpleDropTarget( wx.PyDropTarget ):
    accepts_default = (wx.DF_FILENAME,
                       wx.DF_TEXT,
                       wx.DF_BITMAP)

    def __init__( self, calltarget = None, accepts = accepts_default, **callbacks ):
        wx.PyDropTarget.__init__( self )

        if not all(callable(c) for c in callbacks.values()):
            raise TypeError, 'keyword arguments to DropTarget must be callable'

        self.dragged = wx.DataObjectComposite()

        for dragtype in accepts:
            datatype, datainit, datamethod = drag_types[dragtype]

            obj = datainit()
            self.dragged.Add(obj)
            setattr(self.dragged, datatype, obj)

        self.SetDataObject( self.dragged )

        self.accepts = accepts
        self.calltarget = calltarget
        self.callbacks = callbacks
        self.successful_drag_result = wx.DragCopy

    def callif(self, dragtype, data):
        call = getattr(self.calltarget, 'OnDrop' + dragtype.title(), None)
        if callable(call):
            if dragtype == 'files':
                wx.CallLater(300, call, data)
            else:
                call(data)
        elif dragtype in self.callbacks:
            if dragtype == 'files':
                wx.CallLater(300, self.callbacks[dragtype], data)
            else:
                self.callbacks[dragtype](data)
        else:
            log.info('ignored (%s): %s', dragtype, repr(data)[:50])

    def OnDrop( self, x, y ):
        return True

    def OnData( self, x, y, d ):
        "Called when OnDrop returns True. Get data and do something with it."

        self.GetData()

        format = self.dragged.GetReceivedFormat().GetType()

        for format in self.accepts:
            datatype, datainit, datamethod = drag_types[format]
            data = datamethod(getattr(self.dragged, datatype))

            if data:
                self.callif(datatype, data)

        return True

    def OnEnter( self, x, y, d ):
        return d


    def OnDragOver( self, x, y, d ):
        return wx.DragMove


if __name__ == '__main__':
    a = wx.PySimpleApp()
    f = wx.Frame(None)

    def foo(data):
        print data

    p = wx.Panel(f)
    p.SetDropTarget(DropTarget(text = foo, files = foo, bitmap = foo))

    f.Show(True)
    a.MainLoop()

