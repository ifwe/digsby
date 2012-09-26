import wx
import sys
import actionIDs

from peak.util.imports import lazyModule

common = lazyModule('common')
from eventStack import AppEventHandlerMixin
config = lazyModule('config')
from weakref import WeakValueDictionary

def stub():
    pass

def tracecall(fn):
    """
    This decorator allows us to register that an event handler has fired
    during automated tests.
    """
    def trace(*args):
        if getattr(wx.GetApp(), "testing", False):
            wx.GetApp().event_fired = fn
            print "function %r fired" % fn
            return stub
        else:
            return fn(*args)

    return trace


# TODO: FInd a better place to put these data structures.
sorts = {
        actionIDs.SortByNone: 'none',
        actionIDs.SortByStatus: 'status',
        actionIDs.SortByName: 'name',
        actionIDs.SortByLogSize: 'log',
        actionIDs.SortByService: 'service'
    }

# For windows, since we have to catch native MENU_OPEN events :(
hwndMap = WeakValueDictionary()

# another cache for avoiding lookups when possible
menuTitles = {}

buddylist_panel_names = dict(status = _('Status Panel'),
                             blist  = _('Buddy List'),
                             elist  = _('Email Accounts'),
                             slist  = _('Social Networks'),
                             clist  = _('Connections'))

class MainMenuEventHandler(AppEventHandlerMixin):
    def __init__(self):
        AppEventHandlerMixin.__init__(self)

    def register_handlers(self):
        self.AddHandlerForID(actionIDs.NewStatusMessage, self.new_status_message)
        self.AddHandlerForID(actionIDs.EditStatusMessage, self.edit_status_message)
        self.AddHandlerForID(actionIDs.MyAccounts, self.accounts)
        self.AddHandlerForID(actionIDs.NewIM, self.new_im)
        self.AddHandlerForID(actionIDs.AddContact, self.add_contact)
        self.AddHandlerForID(actionIDs.AddGroup, self.add_group)
        self.AddHandlerForID(actionIDs.RenameSelection, self.rename_selection)
        self.AddHandlerForID(actionIDs.DeleteSelection, self.delete_selection)
        self.AddHandlerForID(actionIDs.SignOff, self.sign_off)

        self.AddHandlerForID(actionIDs.AlwaysOnTop, self.always_on_top)
        self.AddHandlerForID(actionIDs.Skins, self.skins)
        self.AddHandlerForID(actionIDs.MenuBar, self.show_menubar)
        self.AddHandlerForID(actionIDs.StatusPanel, self.show_status_panel)
        self.AddHandlerForID(actionIDs.ArrangePanels, self.arrange_panels)
        self.AddHandlerForID(actionIDs.ShowMobileContacts, self.show_mobile_contacts)
        self.AddHandlerForID(actionIDs.ShowOfflineContacts, self.show_offline_contacts)
        self.AddHandlerForID(actionIDs.GroupOfflineContacts, self.group_offline_contacts)
        self.AddHandlerForID(actionIDs.HideOfflineGroups, self.hide_offline_groups)

        self.AddHandlerForID(actionIDs.SortByNone, self.sort_by)
        self.AddHandlerForID(actionIDs.SortByStatus, self.sort_by)
        self.AddHandlerForID(actionIDs.SortByName, self.sort_by)
        self.AddHandlerForID(actionIDs.SortByLogSize, self.sort_by)
        self.AddHandlerForID(actionIDs.SortByService, self.sort_by)
        self.AddHandlerForID(actionIDs.SortByAdvanced, self.sort_by)

        self.AddHandlerForID(actionIDs.Preferences, self.show_preferences)
        self.AddHandlerForID(actionIDs.FileTransferHistory, self.show_file_transfer_history)
        self.AddHandlerForID(actionIDs.ChatHistory, self.show_chat_history)

        self.AddHandlerForID(actionIDs.Documentation, self.show_documentation)
        self.AddHandlerForID(actionIDs.SupportForums, self.show_support_forums)
        self.AddHandlerForID(actionIDs.SubmitBugReport, self.submit_bug_report)
        self.AddHandlerForID(actionIDs.SuggestAFeature, self.suggest_a_feature)
        self.AddHandlerForID(actionIDs.ShowDebugConsole, self.show_debug_console)
        # See note in run_tests method.
        # self.AddHandlerForID(actionIDs.RunTests, self.run_tests)
        self.AddHandlerForID(actionIDs.InviteYourFriends, self.invite_your_friends)

        if 'wxMSW' in wx.PlatformInfo:
            parentFrame = self.get_buddy_list_frame()
            parentFrame.Bind(wx.EVT_MENU_OPEN, self.update_menu)
        else:
            self.Bind(wx.EVT_MENU_OPEN, self.update_menu)

    def fire_event_for_action(self, action, target=None):
        return fire_action_event(action, target)

    # TODO: I wonder if we want to move buddylist-specific events into the buddylist
    # itself?
    def get_buddy_list_frame(self):
        buddylist = None
        app = wx.GetApp()
        if app:
            buddylist = app.buddy_frame

        return buddylist

    def get_buddy_list_panel(self):
        buddylist = self.get_buddy_list_frame()

        if buddylist:
            return buddylist.buddyListPanel
        else:
            return None

    def update_menu(self, event):
        menu = event.Menu

        # ooohkay... so wx doesn't allow you to get a menu's title from the menu
        # object, but you can get it by getting them menubar then passing in the
        # menu object's position in the menubar...
        if config.platformName == "mac":
            menubar = self.get_buddy_list_frame().MenuBar
        else:
            menubar = self.get_buddy_list_panel().menubar

        global menuTitles
        if menubar:
            title = None
            if menu in menuTitles:
                title = menuTitles[menu]
            else:
                for i in xrange(menubar.MenuCount):
                    iter_menu = menubar.GetMenu(i)
                    if iter_menu == menu:
                        title = menuTitles[menu] = menubar.GetMenuLabel(i)
                    else:
                        for item in iter_menu.MenuItems:
                            if item.IsSubMenu() and menu == item.SubMenu:
                                title = menuTitles[menu] = item.GetItemLabel()

            if title == _("&Digsby"):
                self.update_digsby_menu(menu)
            elif title == _("&Sort By"):
                self.update_sort_menu(menu)
            elif title == _('&View'):
                self.update_view_menu(menu)

    def update_digsby_menu(self, menu):
        buddylist = self.get_buddy_list_panel()
        if buddylist:
            b = buddylist.blist.SelectedItem

            from contacts.buddylistfilters import OfflineGroup


            allow_add = any(x.allow_contact_add for x in common.profile.account_manager.connected_accounts)
            menu.Enable(actionIDs.NewIM, allow_add) #TODO: Needs to decide if it should be enabled
            menu.Enable(actionIDs.AddContact, allow_add)
            menu.Enable(actionIDs.AddGroup, allow_add)

            renameitem = menu.FindItemById(actionIDs.RenameSelection)
            deleteitem = menu.FindItemById(actionIDs.DeleteSelection)

            if b is None or getattr(b, 'iswidget', False) or isinstance(b, OfflineGroup):

                renameitem.SetItemLabel(_('&Rename Selection'))
                deleteitem.SetItemLabel(_('&Delete Selection'))
                renameitem.Enable(False)
                deleteitem.Enable(False)
            else:
                renameitem.SetItemLabel(_('&Rename {name}').format(name=getattr(b, 'alias', b.name)))
                deleteitem.SetItemLabel(_('&Delete {name}').format(name=getattr(b, 'alias', b.name)))
                renameitem.Enable(True)
                deleteitem.Enable(True)

    def update_sort_menu(self, menu):
        checkedOne = False
        sortby     = common.pref('buddylist.sortby', 'none none')
        global sorts

        for item in menu.MenuItems:
            try:
                if item.Id in sorts:
                    sorttypes = sorts[item.Id] + ' none'
                else:
                    sorttypes = object()
            except IndexError:
                sorttypes = object()

            if item.Kind == wx.ITEM_CHECK:

                val = sorttypes == sortby
                item.Check(val)
                if val:
                    checkedOne = True

        if not checkedOne:
            list(menu.MenuItems)[-1].Check(True)

    def update_view_menu(self, menu):
        sortstatus = common.pref('buddylist.sortby').startswith('*status')

        showoff = common.pref('buddylist.show_offline')
        showmob = common.pref('buddylist.show_mobile')
        hidegroups = common.pref('buddylist.hide_offline_groups')
        groupoff =  common.pref('buddylist.group_offline')

        showstat = common.pref('buddylist.show_status')
        showmenu = common.pref('buddylist.show_menubar')

        ontop = menu.FindItemById(actionIDs.AlwaysOnTop)
        showmobile = menu.FindItemById(actionIDs.ShowMobileContacts)
        showoffline = menu.FindItemById(actionIDs.ShowOfflineContacts)
        groupoffline = menu.FindItemById(actionIDs.GroupOfflineContacts)
        hideoffline = menu.FindItemById(actionIDs.HideOfflineGroups)

        statuspanel = menu.FindItemById(actionIDs.StatusPanel)
        menubar = menu.FindItemById(actionIDs.MenuBar)

        showmobile.Check(showmob)
        showoffline.Check(showoff)
        statuspanel.Check(showstat)
        # Mac doesn't have this option since menubar is always at the top of the screen
        if menubar:
            menubar.Check(showmenu)

        buddy_frame = self.get_buddy_list_frame()
        if buddy_frame:
            ontop.Check(buddy_frame.HasFlag(wx.STAY_ON_TOP))

        groupoffline.Enable(not sortstatus and showoff)
        groupoffline.Check(groupoff and (not sortstatus and showoff))

        hideoffline.Enable(not sortstatus)
        hideoffline.Check((sortstatus and not showoff)
                          or (not sortstatus and hidegroups))

    @tracecall
    def new_status_message(self, event=None):
        from gui.status import new_custom_status
        new_custom_status(None, save_checkbox = True)

    @tracecall
    def edit_status_message(self, event=None):
        import gui.pref.prefsdialog as prefsdialog
        prefsdialog.show('status')

    @tracecall
    def accounts(self, event=None):
        prefsdialog.show('accounts')

    @tracecall
    def update_bool_pref(self, pref):
        common.profile.prefs[pref] = not common.profile.prefs[pref]

    def update_check_pref(self, item, value):
        item.Check(value)

    @tracecall
    def new_im(self, event=None):
        from gui.imdialogs import ShowNewIMDialog
        ShowNewIMDialog()

    @tracecall
    def add_contact(self, event=None):
        from gui.addcontactdialog import AddContactDialog
        AddContactDialog.MakeOrShow()

    @tracecall
    def add_group(self, event=None):
        import gui.protocols
        gui.protocols.add_group()

    @tracecall
    def rename_selection(self, event=None):
        buddylist = self.get_buddy_list_panel()
        if buddylist:
            buddylist.blist.rename_selected()

    @tracecall
    def delete_selection(self, event=None):
        buddylist = self.get_buddy_list_panel()
        if buddylist:
            buddylist.blist.delete_blist_item(buddylist.blist.SelectedItem)

    @tracecall
    def sign_off(self, event=None):
        common.profile.signoff()

    @tracecall
    def always_on_top(self, event=None):
        self.update_bool_pref('buddylist.always_on_top')

    @tracecall
    def skins(self, event=None):
        prefsdialog.show('appearance')

    @tracecall
    def show_menubar(self, event=None):
        pref = 'buddylist.show_menubar'
        self.update_bool_pref(pref)
        if not common.profile.prefs[pref]:
            wx.MessageBox(_('You can bring back the menubar by right clicking '
                            'on the digsby icon in the task tray.'),
                            _('Hide Menu Bar'))

    @tracecall
    def show_status_panel(self, event=None):
        self.update_bool_pref('buddylist.show_status')

    @tracecall
    def arrange_panels(self, event=None):
        from gui.visuallisteditor import VisualListEditor
        if VisualListEditor.RaiseExisting():
            return

        buddylist = self.get_buddy_list_panel()
        editor = VisualListEditor(buddylist, common.profile.prefs['buddylist.order'],
                              buddylist_panel_names,
                              lambda l: common.setpref('buddylist.order', l),
                              _('Arrange Panels'))
        editor.Show()

    @tracecall
    def show_mobile_contacts(self, event=None):
        self.update_bool_pref('buddylist.show_mobile')

    @tracecall
    def show_offline_contacts(self, event=None):
        self.update_bool_pref('buddylist.show_offline')

    @tracecall
    def group_offline_contacts(self, event=None):
        self.update_bool_pref('buddylist.group_offline')

    @tracecall
    def hide_offline_groups(self, event=None):
        self.update_bool_pref('buddylist.hide_offline_groups')

    @tracecall
    def sort_by(self, event):
        global sorts
        if event.GetId() in sorts:
            common.setpref('buddylist.sortby', sorts[event.GetId()] + ' none')
        else:
            prefsdialog.show('contact_list')

    @tracecall
    def show_preferences(self, event=None):
        prefsdialog.show('accounts')

    @tracecall
    def show_file_transfer_history(self, event=None):
        from gui.filetransfer import FileTransferDialog
        FileTransferDialog.Display()

    @tracecall
    def show_chat_history(self, event=None):
        from gui.pastbrowser import PastBrowser
        PastBrowser.MakeOrShow()

    @tracecall
    def show_documentation(self, event=None):
        wx.LaunchDefaultBrowser('http://wiki.digsby.com')

    @tracecall
    def show_support_forums(self, event=None):
        wx.LaunchDefaultBrowser('http://forum.digsby.com')

    @tracecall
    def submit_bug_report(self, event=None):
        from util.diagnostic import do_diagnostic
        do_diagnostic()

    @tracecall
    def suggest_a_feature(self, event=None):
        from gui.native.helpers import createEmail
        createEmail('mailto:features@digsby.com')

    @tracecall
    def show_debug_console(self, event=None):
        wx.GetApp().toggle_crust()

    @tracecall
    def invite_your_friends(self, event=None):
        wx.LaunchDefaultBrowser('http://www.digsby.com/invite')

    # NOTE: Temporarily disabled until we can get path / the AutoUpdater properly
    # handling non-ascii filename characters on Mac.
    #@tracecall
    #def run_tests(self, event=None):
    #    import tests.unittests as test
    #    testDialog = test.UnitTestDialog(None, -1, size=(400,400), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    #    testDialog.Show()

def fire_action_event(action, target=None):
    if not target:
        target = wx.GetApp()

    if target:
        event = wx.CommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, action)
        target.ProcessEvent(event)

