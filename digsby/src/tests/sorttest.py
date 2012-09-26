from util import *
import wx
from wx.lib.mixins.listctrl import ColumnSorterMixin
from random import randint

class SortFrame(wx.Frame, ColumnSorterMixin):
    def __init__(self, parent=None, id=-1, title="Sort Test"):
        wx.Frame.__init__(self, parent, id, title)
        
        numColumns = 3

        loadWindowPos(self)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.list=wx.ListCtrl(self,id, style=wx.LC_REPORT)        
        ColumnSorterMixin.__init__(self, numColumns)
                        
        cols = ["Name", "Address", "Phone", "Age"]        
        
        firsts  = "Adam Laura Sara Danielle Dave Kevin Joe Mike Chris Aaron Steve Mary Sally".split()
        lasts   = "Clinton Bush Adams Washington Garfield Ford Kennedy Reagan Taft".split()
        stNames = "Fake Apple Banana Orange Blueberry Mango".split()
        sts     = "Street Avenue Drive Bouelevard".split()
        
        # return a random element from a list
        def rnd(lst): return lst[randint(0,len(lst)-1)]
        
        # generate a bunch of random
        self.itemDataMap = {}
        for i in range(500):
            name = rnd(firsts) + " " + rnd(lasts)
            address = str(randint(1,1000)) + " " + rnd(stNames) + " " + rnd(sts)
            phone = "%d-%d-%d" % (randint(100,999), randint(100,999), randint(1000,9999))
            age = randint(1,100)
            
            self.itemDataMap[i] = [name,address,phone,age]
                
        
        itemDataMap = self.itemDataMap
        
        keys = itemDataMap.keys()
        
        [self.list.InsertColumn(i, cols[i]) for i in range(len(cols))]
        for i in keys:
            o = itemDataMap[i]
            self.list.InsertStringItem(i, o[0])
            for c in range(len(o)):
                self.list.SetStringItem(i,c,str(o[c]))
            self.list.SetItemData(i, i)
            
        self.SetColumnCount(len(cols))
    
    def GetListCtrl(self): return self.list   
    
    def on_close(self,e):
        saveWindowPos(self)
        self.Destroy()

class SortApp(wx.App):
    def OnInit(self):
        f = SortFrame()
        f.Show(True)
        self.SetTopWindow(f)
        
        return True

# not used yet...    
class Person:
    cols = ["name", "address", "phone", "age"]
    
    def __init__(self, **kwargs):
        for k in kwargs:
            self.__dict__[k] = kwargs[k]


if __name__ == '__main__':
    wx.ConfigBase.Set(wx.FileConfig())
    app = SortApp(0)     # Create an instance of the application class    
    app.MainLoop()     # Tell it to start processing events
    