import wx
from util.primitives.funcs import do

def HackedShow(self,pseudosizer,switch=True):
    self.RealShow(switch and pseudosizer.Shown)
    self.ShouldShow = switch
    pseudosizer.Recalc()

class PseudoSizer(list):
    '''
    An artificial sizer that can be positioned and controls the visibility of all it's children
    '''
    def __init__(self):
        list.__init__(self)

        self.position = wx.Point(0,0)
        self.space = 4
        self.Shown=True

    def Add(self,item):
        self.append(item)
        item.Show(self.Shown and item.Shown)
        item.ShouldShow = item.Shown
        item.RealShow = item.Show
        item.Show = lambda s: HackedShow(item, self, s)
        self.Recalc()

    def SetPosition(self,pos):
        if pos[0] != -1: self.position.x = pos[0]
        if pos[1] != -1: self.position.y = pos[1]

        self.Recalc()

    def GetPosition(self):
        return self.position

#    Position=property(GetPosition,SetPosition)

    def SetSpace(self,space):
        self.space=space
        self.Recalc()

    def GetSpace(self):
        return self._space

#    Space=property(GetSpace,SetSpace)

    def Recalc(self):
        x, y = self.position
        pos = wx.Point(x, y)
        space = self.space

        for item in self:
            if item.Shown:
                item.Position = pos
                item.Size = item.BestSize
                pos.x += item.Size.width + space

    def Layout(self):
        self.Recalc()

    def Clear(self,delete=False):
        for item in self[:]:
            item.RealShow(False)
            self.remove(item)
            item.Show=item.RealShow
            if delete: item.Destroy()

    def Remove(self,item):
        self.remove(item)
        item.Show=item.RealShow

    @property
    def Rect(self):
        return wx.RectPS(self.position, self.Size)

    @property
    def Size(self):
        w=0
        h=0
        for item in self:
            if item.Shown:
                if item.Size.height>h: h=item.Size.height
                w+=item.Size.width

        return wx.Size(w,h)

    def Show(self,switch=True):
        self.Shown=switch
        do(item.RealShow(switch and item.ShouldShow) for item in self)
        self.Recalc()
