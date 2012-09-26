"""
The purpose of this class is to have a Menu class focused only on the menu itself,
leaving the event handling and menu display to the controller and view, respectively.

On Mac, since the main menubar is always displayed, having the main menu tied tightly to
a particular view is problematic, as once that view loses focus, some of the menu items
may not do the correct thing, for example.
"""

import wx
import sys
import gui.uberwidgets.umenu

item_types = ["normal", "checkbox", "radio", "separator"]

def wxTypeForItemType(type):
    if not type or type == "normal":
        return wx.ITEM_NORMAL
    if type == "checkbox":
        return wx.ITEM_CHECK
    if type == "radio":
        return wx.ITEM_RADIO
    if type == "separator":
        return wx.ITEM_SEPARATOR

    assert(type in item_types)

def set_menubar(parent, menus, umenu = False):
    if not umenu:
        menubar = wx.MenuBar()
    else:
        menubar = gui.uberwidgets.umenu.UMenuBar(parent)

    for menu in menus:
        label = menu.label

        if umenu:
            menu = menu.asUMenu(parent)
        else:
            menu = menu.asWxMenu()

        menubar.Append(menu, label)

    if not umenu:
        parent.SetMenuBar(menubar)

    return menubar

class Menu(object):
    def __init__(self, label="", items=None):
        self.label = label
        if items:
            self.items = items
        else:
            self.items = []

    def __repr__(self):
        return '<Menu "%s"\n%s>' % (self.label, '\n'.join('    ' + repr(item) for item in self))

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def addItem(self, label, description="", id=None, type="normal",
                    defaultAccel=None, customAccel=None, subMenu=None, bitmap=None):

        item = MenuItem(label, description, id, type, defaultAccel, customAccel, subMenu, bitmap)
        self.items.append(item)
        return item

    def addSep(self):
        item = MenuItem(label="", type="separator")
        self.items.append(item)
        return item

    def asWxMenu(self):
        menu = wx.Menu()
        for item in self.items:
            menu.AppendItem(item.asWxMenuItem(menu))

        return menu

    def asUMenu(self, parent, windowless = False):
        menu = gui.uberwidgets.umenu.UMenu(parent, windowless = windowless)
        for item in self.items:
            item.asUMenuItem(menu)

        assert len(menu) == len(self.items)
        return menu

class MenuItem(object):
    def __init__(self, label, description = "", id = None, type = "normal",
                    defaultAccel = None, customAccel = None, subMenu = None, bitmap = None):
        self.label = label
        self.description = description
        self.defaultAccel = defaultAccel
        self.customAccel = customAccel
        self.type = type
        self.subMenu = subMenu
        self.bitmap = bitmap


        if type == "separator":
            assert id is None, 'separators cannot have ids, you gave %r' % id
            id = wx.ID_SEPARATOR
        elif id is None:
            id = wx.NewId()

        self.id = id

    def __repr__(self):
        if self.type == 'separator':
            return '<MenuItem (separator)>'
        else:
            return "<MenuItem: id=%d, label=%r, desc=%s, defaultAccel=%s, customAccel=%s, type=%s>" % \
                (self.id, self.label, self.description, self.defaultAccel, self.customAccel, self.type)

    def asWxMenuItem(self, menu=None):
        label = self.label
        if self.customAccel:
            label += "\t" + self.customAccel
        elif self.defaultAccel:
            label += "\t" + self.defaultAccel

        subMenu = None
        if self.subMenu is not None:
            subMenu = self.subMenu.asWxMenu()

        item = wx.MenuItem(menu, self.id, label, self.description,
                    wxTypeForItemType(self.type), subMenu)

        if self.bitmap:
            item.SetBitmap(self.bitmap)

        return item

    def asUMenuItem(self, umenu):
        if self.subMenu is not None:
            return umenu.AddSubMenu(self.subMenu.asUMenu(umenu.Window), self.label, self.bitmap)
        else:
            if self.type == "checkbox":
                item = umenu.AddCheckItem(self.label)
                item.Id = self.id
                return item

            elif self.type == "radio":
                item = umenu.AddRadioItem(self.label)
                item.Id = self.id
                return item
            else:
                return umenu.Append(self.id, self.label, self.bitmap)

if __name__ == "__main__":
    def _(text):
        return text

    from tests.testapp import testapp
    app = testapp('../../..')
    frame = wx.Frame(None, -1)
    frame.Sizer = sizer = wx.BoxSizer(wx.VERTICAL)


    use_umenu = False
    menus = digsbyWxMenuBar(use_umenu, frame)
    menubar = set_menubar(frame, menus, use_umenu)

    app.SetTopWindow(frame)

    if use_umenu:
        sizer.Add(menubar.SizableWindow, 0, wx.EXPAND)

    frame.Show()



    app.MainLoop()
