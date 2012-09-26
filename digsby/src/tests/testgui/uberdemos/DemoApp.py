import wx
from gui.skin import skininit

class App(wx.App):
    def __init__(self, callback):

        self.Go=callback

        wx.App.__init__(self,0)

    def OnInit(self):

        skininit('../../../../res')
        self.Go()

        return True