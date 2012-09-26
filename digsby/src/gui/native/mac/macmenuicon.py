import os

import wx
import objc
from AppKit import *
from Foundation import *
import tempfile
import util.observe as observe

from gui.uberwidgets.umenu import UMenu
from .machelpers import *

NSApplicationLoad()

class Notifier(observe.Observable):
    def __init__(self, parent):
        self.parent = parent

    def on_account_updated(self, *a):
        with nspool():
            wx.CallAfter(self.parent.on_account_updated, a)

class MenuBarIconDelegate(NSObject):
    def initWithAccount(self, acct, infobox):
        with nspool():
            self.acct = acct
            self.infobox = infobox
            from gui.uberwidgets.umenu import UMenu
            self._menu = UMenu(wx.FindWindowByName('Buddy List'), onshow = self.update_menu)
            statusbar = NSStatusBar.systemStatusBar()
            self.statusitem = statusbar.statusItemWithLength_(NSVariableStatusItemLength)

            self.statusitem.setTarget_(self)
            self.statusitem.setAction_("itemClicked:")

            # set up our observer
            self.observer = Notifier(self)
            acct.add_observer(self.observer.on_account_updated, 'count', 'state', obj = self.observer)
            self.on_account_updated()

    def Destroy(self):
        with nspool():
            self.acct.remove_observer(self.observer.on_account_updated)
            NSStatusBar.systemStatusBar().removeStatusItem_(self.statusitem)
            del self.statusitem
        return True

    def SetIcon(self, icon, tooltip = None):
        with nspool():
            handle, filename = tempfile.mkstemp()
            pngfilename = filename + ".png"
            os.close(handle)
            os.rename(filename, pngfilename)
            icon.WXB.SaveFile(pngfilename, wx.BITMAP_TYPE_PNG)

            nsicon = NSImage.alloc().initWithContentsOfFile_(pngfilename)

            self.statusitem.setImage_(nsicon)
            if tooltip:
                self.statusitem.setToolTip_(tooltip)

    @property
    def _IconSize(self):
        return 16

    def umenuToNSMenu(self, umenu):
        with nspool():
            menu = NSMenu.alloc().initWithTitle_("submenu")
            for item in umenu:
                fullname = item.GetItemLabel()
                accel = ""
                if fullname.find("\\t") != -1:
                    fullname, accel = fullname.split("\\t")
                if item.IsSeparator():
                    menu.addItem_(NSMenuItem.separatorItem())
                else:
                    nsitem = menu.addItemWithTitle_action_keyEquivalent_(item.GetItemLabelText(), "menuItemClicked:", accel)
                    if item.GetSubMenu():
                        submenu = self.umenuToNSMenu(item.GetSubMenu())
                        menu.setSubMenu_forItem_(submenu, nsitem)
    
                    nsitem.setTarget_(self)
            return menu

    def itemClicked_(self, sender):
        with nspool():
            self.update_menu()
            if hasattr(self, "subMenu"):
                del self.subMenu

            self.subMenu = self.umenuToNSMenu(self._menu)
            if self.subMenu:
                self.statusitem.popUpStatusItemMenu_(self.subMenu)

    def menuItemClicked_(self, sender):
        with nspool():
            self.fireHandlerForMenu(sender, self._menu)

    def fireHandlerForMenu(self, sender, menu):
        for item in menu:
            if item.GetItemLabelText() == sender.title():
                try:
                    callback = self._menu.cbs[item.GetId()]
                    callback()
                except KeyError:
                    pass
            elif item.GetSubMenu():
                self.fireHandlerForMenu(sender, item.GetSubMenu())
