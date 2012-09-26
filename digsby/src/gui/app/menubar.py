import wx
import sys
import actionIDs
from gui.model.menus import *
from config import platformName

def digsbyWxMenuBar():
    menus = []

    # We will want to move this somewhere else, but using it right now for testing.
    digsby = Menu(_('&Digsby'))

    status = Menu()
    status.addItem(_('&New Status Message...'), id=actionIDs.NewStatusMessage)
    status.addItem(_('&Edit Status Messages...'), id=actionIDs.EditStatusMessage)

    digsby.addItem(_('My Status'), subMenu=status)
    digsby.addItem(_('My &Accounts...'), id=actionIDs.MyAccounts)
    digsby.addSep()

    digsby.addItem(_('&New IM...'), id=actionIDs.NewIM, defaultAccel='Ctrl+N')
    digsby.addItem(_('Add &Contact...'), id=actionIDs.AddContact, defaultAccel='Ctrl+A')
    digsby.addItem(_('Add &Group...'), id=actionIDs.AddGroup, type="checkbox")
    digsby.addItem(_('&Rename Selection'), id=actionIDs.RenameSelection)
    digsby.addItem(_('&Delete Selection...'), id=actionIDs.DeleteSelection)
    digsby.addSep()
    digsby.addItem(_('Sign &Off Digsby'), id=actionIDs.SignOff)
        # wx.App handles this for proper shutdown.
    digsby.addItem(_('E&xit Digsby'), id=actionIDs.Exit)
    menus.append(digsby)

    view = Menu(_('&View'))
    view.addItem(_('&Always On Top'), id=actionIDs.AlwaysOnTop, type="checkbox")
    view.addItem(_('Skins...'), id=actionIDs.Skins, defaultAccel='Ctrl+S')
    view.addSep()
    if not platformName == "mac":
        view.addItem(_('&Menu Bar'), id=actionIDs.MenuBar, type="checkbox")
    view.addItem(_('Status Panel'), id=actionIDs.StatusPanel, type="checkbox")
    view.addItem(_('Arrange &Panels...'), id=actionIDs.ArrangePanels)
    view.addSep()
    view.addItem(_('Show &Mobile Contacts'), id=actionIDs.ShowMobileContacts, defaultAccel='Ctrl+M', type="checkbox")
    view.addItem(_('Show &Offline Contacts'), id=actionIDs.ShowOfflineContacts, defaultAccel='Ctrl+O', type="checkbox")
    view.addItem(_('&Group Offline Contacts'), id=actionIDs.GroupOfflineContacts, defaultAccel='Ctrl+G', type="checkbox")
    view.addItem(_('&Hide Offline Groups'), id=actionIDs.HideOfflineGroups, type="checkbox")

    # sort by
    sortby = Menu()
    # TODO: Create one master list of the possible sort orders and iterate through them here.
    sortby.addItem(_('&None'), id=actionIDs.SortByNone, type="checkbox")
    sortby.addItem(_('&Status'), id=actionIDs.SortByStatus, type="checkbox")
    sortby.addItem(_('N&ame'), id=actionIDs.SortByName, type="checkbox")
    sortby.addItem(_('&Log Size'), id=actionIDs.SortByLogSize, type="checkbox")
    sortby.addItem(_('Ser&vice'), id=actionIDs.SortByService, type="checkbox")
    sortby.addItem(_('Advan&ced...'), id=actionIDs.SortByAdvanced, type="checkbox")

    view.addItem(_('&Sort By'), subMenu=sortby)
    menus.append(view)

    tools = Menu(_('&Tools'))
    tools.addItem(_('&Preferences...'), defaultAccel='Ctrl+P', id = actionIDs.Preferences)
    tools.addItem(_('&File Transfer History'), id=actionIDs.FileTransferHistory, defaultAccel='Ctrl+J')
    tools.addItem(_('&Chat History'), id=actionIDs.ChatHistory)
    menus.append(tools)

    help = Menu(_('&Help'))
    help.addItem(_('&Documentation'), id=actionIDs.Documentation)
    help.addItem(_('Support &Forums'), id=actionIDs.SupportForums)
    help.addSep()
    help.addItem(_('&Submit Bug Report'), id=actionIDs.SubmitBugReport)
    help.addItem(_('Su&ggest a Feature'), id=actionIDs.SuggestAFeature)
    help.addSep()

    if getattr(sys, 'DEV', False): # or pref('debug.console', False):
        help.addItem('Show Debug Console', id=actionIDs.ShowDebugConsole)
        help.addItem('Run Tests', id=actionIDs.RunTests)
        help.addSep()

    help.addItem(_('&Invite Your Friends'), id=actionIDs.InviteYourFriends)
    help.addItem(_('&About Digsby'), id=actionIDs.About)
    menus.append(help)

    return menus
