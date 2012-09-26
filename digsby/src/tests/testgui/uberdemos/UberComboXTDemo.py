import wx
from DemoApp import App
from gui.uberwidgets.UberCombo import UberCombo
from gui import skin as skincore
from gui.uberwidgets.simplemenu import SimpleMenu,SimpleMenuItem
from util.primitives.funcs import do
from logging import getLogger; log = getLogger('ComboListEditor')

class ComboListEditor(UberCombo):
    def __init__(self, parent, content_callback, objects = None):
        UberCombo.__init__(self, parent, skinkey = 'combobox', typeable = False,
                           valuecallback = self.OnValue,
                           selectioncallback = lambda item: self.ChangeValue(item))

        self.remove_menu = SimpleMenu(self.menu, 'simplemenu',callback = self.OnRemove)
        self.content_cb = content_callback

        if objects is not None:
            self.SetList(objects)

    def SetList(self, objs):
        self.objects = objs

        # create SimpleMenuItems for each domain object
        items = [SimpleMenuItem(self.content_cb(obj)) for obj in objs]
        self.remove_menu.SetItems(items)
        self.SetItems(items)

        self.separator = SimpleMenuItem(id = -1)
        self.AppendItem(self.separator)

        self.remove_item = SimpleMenuItem(_('Remove'), menu = self.remove_menu)

        self.AppendItem(SimpleMenuItem(_('Add'), method = lambda: self.EditValue()))
        self.AppendItem(self.remove_item)


    def OnValue(self, value):
        if value is None: return

        skip = False
        for t in self.GetStringsAndItems():
            if t[0] == value:
                skip = True
                self.ChangeValue( t[1] )
                break

        if not skip:
            item = self.content_cb(value)
            self.InsertItem(-3, item)
            self.remove_menu.AppendItem(item)
            self.ChangeValue(item)

            if not self.remove_item in self:
                self.AppendItem(self.remove_item)
                self.InsertItem(-2, self.separator)

    def OnRemove(self, item):
        i = self.GetItemIndex(item)
        log.info('removing %s', self.objects.pop(i))

        self.RemoveItem(item)
        self.remmenu.RemoveItem(item)

        if self.GetValue() == item:
            self.ChangeValue(self[0])

        if self.remove_menu.Count == 0:
            self.RemoveItem(self.remove_item)
            self.RemoveItem(self.separator)

class Frame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None,title='Add Remove Combo')
        self.panel=wx.Panel(self)

        self.panel.Sizer=wx.BoxSizer(wx.VERTICAL)

        self.uc=UberCombo(self.panel, skinkey = 'combobox',
                          typeable = False, size=(200,20), minmenuwidth=200,
                          valuecallback = self.ValCB,
                          selectioncallback = self.SelCB)

        self.remmenu=SimpleMenu(self.uc.menu,'simplemenu',width=200,callback=self.RemCB)

        items=[
            SimpleMenuItem('atc282@samplemail.com'),
            SimpleMenuItem('x2ndshadow@samplemail.com'),
            SimpleMenuItem('brokenhalo282@samplemail.com'),
            SimpleMenuItem('brok3nhalo@samplemail.com')
        ]

        self.panel.Sizer.Add(self.uc,0,wx.EXPAND)

        do(self.remmenu.AppendItem(item) for item in items)

        do(self.uc.AppendItem(item) for item in items)
        self.sep=SimpleMenuItem(id=-1)
        self.uc.AppendItem(self.sep)

        self.remitem=SimpleMenuItem('Remove', menu = self.remmenu)

        self.uc.AppendItem(SimpleMenuItem('Add', method = self.AddCB))
        self.uc.AppendItem(self.remitem)

    def AddCB(self,item):
        self.uc.EditValue()

    def RemCB(self,item):
        combo = self.uc

        combo.RemoveItem(item)
        self.remmenu.RemoveItem(item)

        if combo.GetValue()==item:
            combo.ChangeValue(combo[0])

        if len(self.remmenu.spine.items) == 0:
            combo.RemoveItem(self.remitem)
            combo.RemoveItem(self.sep)

    def ValCB(self,value):
        value = value.lower()

        if value:
            thelist = self.uc.GetStringsAndItems()
            skip=False
            for t in thelist:
                if t[0] == value:
                    skip=True
                    self.uc.ChangeValue(t[1])
                    break
            if not skip:
                item = SimpleMenuItem(value)
                self.uc.InsertItem(-3,item)
                self.remmenu.AppendItem(item)
                self.uc.ChangeValue(item)

                if not self.remitem in self.uc.menu.spine.items:
                    self.uc.AppendItem(self.remitem)
                    self.uc.InsertItem(-2, self.sep)

    def SelCB(self,item):
        self.uc.ChangeValue(item)

def Go():
    f=Frame()
    f.Show(True)

if __name__=='__main__':
    a = App( Go )
    a.MainLoop()
