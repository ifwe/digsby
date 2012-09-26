import wx
from gui.windowfx import fadein, fadeout
from weakref import ref


class DragTimer(wx.Timer):
    """
        A timer handling the movement of the tab preview, Dropmarker hiding,
        and showing of hidden tabbars when dragged over a window.
    """
    def __init__(self,manager):
        wx.Timer.__init__(self)
        self.manager=manager

        self.target=None

    def Start(self,overlayimage):
        """
            Fade in overlay and start timer
        """
        wx.Timer.Start(self,1)
        self.overlay=overlayimage
        self.overlay.Move(wx.GetMousePosition()+(2,4))
        fadein(self.overlay,to=self.overlay.alpha)

    def GetFrame(self, window):
        """
            Finds the frame at the pointer
        """
        if window:
            while not isinstance(window,wx.Frame):
                window=window.Parent

        return window

    def Notify(self):
        """
            On the trigger time does D&D operations
        """

        current=self.GetFrame(wx.FindWindowAtPointer())

        #Toggles tabbar of the window
        if current and current != self.target:
            if hasattr(self.target,'notebook'): self.target.notebook.tabbar.Toggle(False)
            self.target=current
            if hasattr(self.target,'notebook'):
                self.target.notebook.tabbar.Toggle(True)
        elif not current:
            if hasattr(self.target,'notebook'): self.target.notebook.tabbar.Toggle(False)
            self.target=current

        #move overlay with mouse
        self.overlay.Move(wx.GetMousePosition()+(2,4))

        #hides dropmarker if no place to drop
        if (not self.manager.destination or not self.manager.destination.tabbar.Rect.Contains(self.manager.destination.ScreenToClient(wx.GetMousePosition()))) and not self.manager.source.tabbar.Rect.Contains(self.manager.source.ScreenToClient(wx.GetMousePosition())):
            self.manager.ShowDropMarker()
        #trigers dragand drop stuff if mouse button goes up
        if not wx.LeftDown():
            self.manager.Trigger()
            self.Stop()

    def Stop(self):
        """
            Stops the timer
            fade out and del overlay
            toggle target tabbar
        """
        if self.target and hasattr(self.target,'notebook'):
            self.target.notebook.tabbar.Toggle(False)
        self.target = None
        wx.Timer.Stop(self)
        fadeout(self.overlay)
        del self.overlay

class WinDragTimer(wx.Timer):
    'Handles drag and drop release with entire windows.'

    notebook = property(lambda self: self._notebook() if self._notebook is not None else None,
                        lambda self, nb: setattr(self, '_notebook', ref(nb)))

    def __init__(self,*a,**k):
        self._notebook = None
        wx.Timer.__init__(self)

    def Start(self,notebook):
        'Sets the notebook and starts the timer.'

        self.notebook = notebook
        wx.Timer.Start(self, 1)

    def Notify(self):
        'If mouse is released, start transaction.'

        if not wx.LeftDown():
            self.Stop()
            nb = self.notebook
            if nb is not None:
                nb.manager.Transaction(nb)
