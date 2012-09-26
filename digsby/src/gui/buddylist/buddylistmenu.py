'''


Main window's main menu


'''
import wx, sys

from gui.uberwidgets.umenu import UMenuBar as MenuBar, UMenu as Menu

from common import actions, profile, pref, setpref
from common.statusmessage import StatusMessage
from logging import getLogger; log = getLogger('blistmenu')
from peak.util.plugins import Hook

import config

import traceback
import gui.supportdigsby as support
from gui.filetransfer import FileTransferDialog
from gui.addcontactdialog import AddContactDialog
from gui.imdialogs import ShowNewIMDialog
from gui.visuallisteditor import VisualListEditor
from util.diagnostic import do_diagnostic
from gui.native.helpers import createEmail
from peak.events import trellis

import contacts
from contacts.sort_model import GROUP_BY_CHOICES, SORT_BY_CHOICES

def prefsdialog_show(name):
    import gui.pref.prefsdialog as prefsdialog
    return prefsdialog.show(name)

def update_statuses(menu):
    # New Status
    # Edit Statuses
    # ---- (separator)
    # << STATUSES >>

    while len(menu) > 3: # ignore first three items.
        menu.RemoveItem(menu[3])

    from gui.statuscombo import status_menu
    status_menu(menu, add_global = True, add_promote = True)

def new_status_message():
    from gui.status import new_custom_status
    new_custom_status(None, save_checkbox = True)

def allow_rename(b):
    from contacts.buddylistfilters import OfflineGroup
    if b is None or getattr(b, 'iswidget', False) or isinstance(b, OfflineGroup):
        return False

    if not isinstance(b, contacts.renamable):
        return False

    if hasattr(b, '_disallow_actions'):
        return False

    return True

class reset_checks_SortOptionWatcher(trellis.Component):
    model = trellis.attr(None)
    names = trellis.attr(None)
    view  = trellis.attr(None)
    @trellis.perform
    def sync(self):
        model_keys = [v[0] for v in self.model.values]
        selection = self.model.selection
        for i, item in enumerate(self.view):
            if i < len(self.names):
                val_key = self.names[i][0]
                item.Check(val_key == model_keys[selection])
                item.Enable(val_key in model_keys)
#            else:
#                item.Check(False)
#                item.Enable(True)

class reset_check_AdvWatcher(trellis.Component):
    model = trellis.attr(None)
    view  = trellis.attr(None)
    @trellis.perform
    def sync(self):
        selection = self.model.selection
        self.view.Check(selection > 0)


# TODO: Remove this code once the kinks have been worked out in the
# new menubar implementation.
def create_main_menu(parent):
    'Returns the main menu object.'

    menu   = MenuBar(parent, skinkey = 'menubar')
    digsby = Menu(parent)
    view   = Menu(parent)
    tools  = Menu(parent)
    help   = Menu(parent)

    def makeadd(m):
        return (lambda title, callback = None, id = -1: m.AddItem(title, callback = callback, id = id))

    #
    # My Status
    #
    mystatus = Menu(parent, onshow = update_statuses); add = makeadd(mystatus)
    add(_('&New Status Message...'), new_status_message)
    add(_('&Edit Status Messages...'), lambda: prefsdialog_show('status'))
    mystatus.AddSep()

    from gui.protocols import add_group

    def add_chat():
        import gui.chatgui
        gui.chatgui.join_chat()

    #
    # Digsby
    #
    digsby.AddSubMenu(mystatus, _('My Status')); add = makeadd(digsby)
    add(_('My &Accounts...'), lambda: prefsdialog_show('accounts'))
    digsby.AddSep()
    sendimitem     = add(_('&New IM...\tCtrl+N'), ShowNewIMDialog)
    if pref('messaging.groupchat.enabled', False):
        groupchatitem = add(_('New Group C&hat...\tCtrl+Shift+N'), add_chat)
    else:
        groupchatitem = None
    digsby.AddSep()
    addcontactitem = add(_('Add &Contact...\tCtrl+A'),lambda : AddContactDialog.MakeOrShow())
    addgroupitem   = add(_('Add &Group...\tCtrl+Shift+A'), lambda: add_group())
    renameitem = add(_('&Rename Selection'), lambda: parent.blist.rename_selected())
    deleteitem = add(_('&Delete Selection...'), lambda: parent.blist.delete_blist_item(parent.blist.SelectedItem))
    digsby.AddSep()
    add(_('Sign &Off Digsby (%s)') % profile.name, lambda: profile.signoff())
    # wx.App handles this for proper shutdown.
    add(_('E&xit Digsby'), id = wx.ID_EXIT)

    def on_digsby_show(_m):
        b = parent.blist.SelectedItem

        allow_add = any(x.allow_contact_add for x in profile.account_manager.connected_accounts)

        for item in (sendimitem, groupchatitem, addcontactitem, addgroupitem):
            if item is not None:
                item.Enable(allow_add)

        if not allow_rename(b):
            renameitem.SetItemLabel(_('&Rename Selection'))
            deleteitem.SetItemLabel(_('&Delete Selection'))
            renameitem.Enable(False)
            deleteitem.Enable(False)
        else:
            renameitem.SetItemLabel(_('&Rename {name}').format(name=getattr(b, 'alias', b.name)))
            deleteitem.SetItemLabel(_('&Delete {name}').format(name=getattr(b, 'alias', b.name)))
            renameitem.Enable(True)
            deleteitem.Enable(True)

    #
    # View
    #

    add = makeadd(view)
    view.AddPrefCheck('buddylist.always_on_top', _('&Always On Top'))
    add(_('Skins...\tCtrl+S'), lambda: prefsdialog_show('appearance'))
    view.AddSep()
    view.AddPrefCheck('buddylist.show_menubar', _('&Menu Bar'))

    def on_menubar(val):
        if not val:
            wx.MessageBox(_('You can bring back the menubar by right clicking '
                            'on the digsby icon in the task tray.'),
                            _('Hide Menu Bar'))

    profile.prefs.link('buddylist.show_menubar', lambda val: wx.CallAfter(on_menubar, val), False, menu)

    view.AddPrefCheck('buddylist.show_status',  _('Status Panel'))
    add(_('Arrange &Panels...'), callback = lambda *_a: edit_buddylist_order(parent))
    view.AddSep()
    view.AddPrefCheck('buddylist.show_mobile',  _('Show &Mobile Contacts\tCtrl+M'))
    view.AddPrefCheck('buddylist.show_offline', _('Show &Offline Contacts\tCtrl+O'))
    groupoffline = view.AddPrefCheck('buddylist.group_offline', _('&Group Offline Contacts\tCtrl+G'))

    hideoffline = view.AddPrefCheck('buddylist.hide_offline_groups', _('&Hide Offline Groups'))

    groupby = Menu(parent); add = makeadd(groupby)
    groupby.sorttypes = []

    # sort by
    sortby = Menu(parent); add = makeadd(sortby)
    sortby.sorttypes = []

    sort_models = profile.blist.sort_models
    group_by = sort_models[0]
    sort_by = sort_models[1]
    then_by = sort_models[2]

    def addsort(model, view, sortstr, title):
        def set(model = model, view = view, sortstr = sortstr):
            model.selection = [v[0] for v in model.values].index(sortstr)
            view[model.selection].Check(True)

        mi = view.AddCheckItem(title, set)
        view.sorttypes.append( sortstr )
        return mi

    sort_names = dict((('none', _('&None')),
        ('status', _('&Status')),
        ('name', _('N&ame')),
        ('log', _('&Log Size')),
        ('service', _('Ser&vice'))))

    def addsorts(model, view, names):
        for name in names:
            addsort(model = model, view = view,
                    sortstr = name, title = sort_names[name])

    addsorts(model = group_by, view = groupby,
             names = [k for k,_v in GROUP_BY_CHOICES])
    groupby.AddSep()
    groupby.AddItem(_('Advan&ced...'), callback = lambda: prefsdialog_show('contact_list'))

    addsorts(model = sort_by, view = sortby,
             names = [k for k,_v in SORT_BY_CHOICES])
    sortby.AddSep()
    def sortby_adv_click():
        sortby[-1].Check(then_by.selection > 0)
        prefsdialog_show('contact_list')
    sortby.AddCheckItem(_('Advan&ced...'), callback = sortby_adv_click)
    sortby_adv = sortby[-1]

    groupby.reset_watcher = reset_checks_SortOptionWatcher(model = group_by,
                                                           view  = groupby,
                                                           names = GROUP_BY_CHOICES)
    sortby.reset_watcher  = reset_checks_SortOptionWatcher(model = sort_by,
                                                           view  = sortby,
                                                           names = SORT_BY_CHOICES)
    sortby.adv_watcher = reset_check_AdvWatcher(model = then_by, view = sortby_adv)

    view.AddSep()
    view.AddSubMenu(groupby, _('&Group By'))
    view.AddSubMenu(sortby,  _('&Sort By'))

    #
    # Tools
    #

    add = makeadd(tools)
    add(_('&Preferences...\tCtrl+P'), id = wx.ID_PREFERENCES, callback = lambda: prefsdialog_show('accounts'))
    add(_('Buddy List &Search\tCtrl+F'), parent.start_search)
    add(_('&File Transfer History\tCtrl+J'), FileTransferDialog.Display)

    def pb_show():
        from gui.pastbrowser import PastBrowser
        PastBrowser.MakeOrShow()

    add(_('&Chat History\tCtrl+H'), pb_show)


    #
    # Help
    #
    add = makeadd(help)
    add(_('&Documentation'), lambda: wx.LaunchDefaultBrowser('http://wiki.digsby.com'))
    add(_('Support &Forums'), lambda: wx.LaunchDefaultBrowser('http://forum.digsby.com'))
    help.AddSep()
    add(_('&Submit Bug Report'), do_diagnostic)
    add(_('Su&ggest a Feature'), send_features_email)
    help.AddSep()

    if getattr(sys, 'DEV', False) or pref('debug.console', False):
        add(_('Show Debug Console'), wx.GetApp().toggle_crust)
        help.AddSep()

    add(_('Su&pport Digsby'), lambda: support.SupportFrame.MakeOrShow(parent))

    for hook in Hook("digsby.help.actions"):
        help_menu_items = hook()
        for item in help_menu_items:
            add(*item)

    def on_view_show(_m):
        sortstatus = pref('buddylist.sortby').startswith('*status')

        showoffline = pref('buddylist.show_offline')
        hidegroups = pref('buddylist.hide_offline_groups')
        groupoff =  pref('buddylist.group_offline')

        groupoffline.Enable(not sortstatus and showoffline)
        groupoffline.Check(groupoff and (not sortstatus and showoffline))

        hideoffline.Enable(not sortstatus)
        hideoffline.Check((sortstatus and not showoffline)
                          or (not sortstatus and hidegroups))

    digsbyMenuName = _('&Digsby')
    if config.platformName == "mac":
        digsbyMenuName = _("&File")

    menu.Append(digsby, digsbyMenuName, onshow = on_digsby_show)
    menu.Append(view,   _('&View'), onshow = on_view_show)
    menu.Append(tools,  _('&Tools'), onshow = lambda m: on_accounts_entries(parent, m))
    menu.Append(help,   _('&Help'))
    return menu

buddylist_panel_names = dict(status = _('Status Panel'),
                             blist  = _('Buddy List'),
                             elist  = _('Email Accounts'),
                             slist  = _('Social Networks'),
                             clist  = _('Connections'))

def edit_buddylist_order(parent, *_a):
    # show an existing one if already on screen

    if VisualListEditor.RaiseExisting():
        return

    editor = VisualListEditor(parent, profile.prefs['buddylist.order'],
                              buddylist_panel_names,
                              lambda l: setpref('buddylist.order', l),
                              _('Arrange Panels'))
    editor.Show()

def im_account_menu(parent, menu, account):
    'Builds a menu for an IM account.'

    menu.RemoveAllItems()

    # Sign On / Sign Off
    if account.connected: menu.AddItem(_('&Sign Off'), callback = account.disconnect)
    else:                 menu.AddItem(_('&Sign On'),  callback = account.connect)

    # Edit Account
    menu.AddItem(_('&Edit Account...'), callback = lambda: profile.account_manager.edit(account))

    # if connected, append more action menu items
    if account.connected:
        menu.AddSep()

        # grab actions for the connection (ignoring Connect and Disconnect methods, since
        # we already have "Sign On/Off" above)
        actions.menu(parent, account.connection, menu,
                     filter = lambda func: func.__name__ not in ('Disconnect', 'Connect'))

        actions.menu(parent, account, menu)


def status_setter(status):
    def _do_set_status(s = status):
        import hooks; hooks.notify('digsby.statistics.ui.select_status')
        return profile.set_status(s)
    return _do_set_status

def add_status_menu_item(menu, statusmsg):
    return menu.Append(statusmsg.title,
                       bitmap = StatusMessage.icon_for(statusmsg),
                       callback = status_setter(statusmsg))


def on_accounts_entries(parent, menu):
    accounts = profile.account_manager.accounts

    if hasattr(menu, '_oldaccts'):
        if getattr(menu, '_oldaccts', []) == [(id(acct), acct.connected) for acct in accounts]:
            return # early exit if the accounts list hasn't changed

    if not hasattr(menu, '_account_items'):
        menu._account_items = []

    item_ids = menu._account_items

    # first: remove old
    for itemid in item_ids:
        menu.Remove(itemid)

    item_ids[:] = []
    parent.Unbind(wx.EVT_MENU_OPEN)

    if accounts and not menu[-1].IsSeparator():
        menu.AddSep()

    for acct in accounts:
        accticon = acct.serviceicon
        bitmap = accticon.Greyed if not acct.connected else accticon
        mi = menu.AppendLazyMenu(acct.name, (lambda m, acct=acct: im_account_menu(parent, m, acct)),
                                 bitmap = bitmap)

        # add a (potentially greyed) service icon
        item_ids += [mi.Id]

    menu._oldaccts = [(id(acct), acct.connected) for acct in accounts]

    if menu[-1].IsSeparator(): menu.RemoveItem(menu[-1])


def yahoo_buddy_menu(menu, contact):
    '''
    Appends a Yahoo-specific "Stealth Settings" submenu to "menu".

    account   - YahooProtocol object
    menu      - a UMenu
    selection - the selected Contact object or None
    '''
    menu_title   = _('&Stealth Settings')

    stealth_menu = Menu(menu.Window)
    enable       = stealth_menu.Enable
    a            = stealth_menu.AddCheckItem

    name = getattr(contact, 'name', _('Selection'))

    # append an item for each stealth option
    items = [a(_('Appear Online to {name}').format(name=name),
               callback = lambda: contact.set_stealth_session(False)),
             a(_('Appear Offline to {name}').format(name=name),
               callback = lambda: contact.set_stealth_session(True)),
             a(_('Appear Permanently Offline to {name}').format(name=name),
               callback = lambda: contact.set_stealth_perm(True))]

    # append a separator and a link to the webpage explaining stealth mode
    stealth_menu.AddSep()
    a(_('Learn More (URL)'),
      callback = lambda: wx.LaunchDefaultBrowser('http://messenger.yahoo.com/stealth.php'))

    online, offline, perm = items

    # items are disabled unless a yahoo buddy is selected
    if contact is None or contact.service != 'yahoo':
        for item in items:
            enable(item.Id, False)
            item.Check(False)
    else:
        invisible = profile.status.invisible
        enable(online.Id, True)
        enable(offline.Id, invisible)
        enable(perm.Id, True)

        if contact.stealth_perm:
            perm.Check(True)
        elif invisible and contact.stealth_session:
            offline.Check(True)
        elif not invisible or not contact.stealth_session:
            online.Check(True)

    menu.AddSubMenu(stealth_menu, menu_title)

def jabber_buddy_menu(menu, contact):

    # offline contacts have no resources
        #don't need a menu if there's only one, and it is None
    if not contact.online or getattr(contact, 'iswidget', False) or \
        (len(list(contact))==1 and list(contact)[0].jid.resource is None):
        return

    resource_menu = Menu(menu.Window)
    a = resource_menu.AddItem

    for resource in contact:
        # append a menu item for each resource
        a(resource.name, callback = lambda r=resource: r.chat())

    menu.AddSubMenu(resource_menu, _('Chat with Resource'))

def metacontact_buddy_menu(menu, mc):
    lenmc = len(mc)

    for contact in mc:
        # add a service specific menu for each contact in the metacontact
        contact_menu = Menu(menu.Window)

        # search_bases = False means we'll get the actions specific to the buddy's service
        actions.menu(menu.Window, contact, contact_menu, search_bases = False)

        if contact_menu[0].IsSeparator():
            contact_menu.RemoveItem(contact_menu[0])

        if lenmc > 2:
            contact_menu.AddSep()
            contact_menu.AddItem(_('&Remove from Merged Contact'),
                                 callback = lambda contact=contact:
                                 mc.manager.remove(mc, contact))

        # use the contact's service icon for the submenu (greyed out if offline)
        icon = contact.serviceicon
        if not contact.online:
            icon = icon.Greyed

        menu.AddSubMenu(contact_menu, contact.name, bitmap = icon)

def send_features_email():
    try:
        createEmail('mailto:features@digsby.com')
    except Exception:
        traceback.print_exc()

        from common.emailaccount import mailclient_launch_error
        mailclient_launch_error()

