'''

Controllers for the to/from combos in the IM window.

'''
from __future__ import with_statement
import wx, sys
from wx import EVT_WINDOW_DESTROY, MessageBox
from operator import attrgetter

from logging import getLogger; log = getLogger('imwin_tofrom'); info = log.info
LOG = log.debug

from common import profile
from common.sms import normalize_sms
from util import repeat_guard, is_email, traceguard
from util.primitives.funcs import Delegate
from util.callbacks import wxcall

from gui.toolbox import calllimit

from gui.skin import get as skinget
from gui.uberwidgets.simplemenu import SimpleMenuItem, SimpleMenu

from common.protocolmeta import emailprotocols, protocols

def can_send_sms(service):
    return service not in ('digsby', 'jabber', 'gtalk', 'fbchat')

class IMControl(object):
    'Manages who you are IMing with, and from which account.'

    def __init__(self, imwin, capsbar, tocombo, fromcombo, onselection = None):

        self.imwin      = imwin
        self.capsbar    = capsbar
        self.tocombo    = tocombo
        self.fromcombo  = fromcombo

        self.contact = None
        self.blist = profile.blist

        self.register_observers()

        self.OnSelection = Delegate()
        self.OnSwitchContact = Delegate()


        self.msgarea = None
        self.ischat = False


#        def ToShowAdd():
#            toshow = (not self.Buddy.protocol.has_buddy_on_list(self.Buddy)) if self.Buddy and self.Account else False
#
#            self.capsbar.badd.Show(toshow)
#            wx.CallAfter(self.capsbar.cbar.OnReSize)


#        self.OnSelection += ToShowAdd

    def register_observers(self):
        accts = profile.connected_accounts
        on_connaccts_changed = lambda *a, **k: wx.CallAfter(self.on_connaccts_changed, *a, **k)

        accts.add_observer(on_connaccts_changed, obj = self)

        def unregister_observers():
            accts.remove_observer(on_connaccts_changed)
            if hasattr(self, 'contacts'):
                for contact in self.contacts:
                    contact.remove_observer(self.buddy_status_changed, 'status')

        #TODO: ToCombo destruction is not the most reliable indication that we need
        # to unregister this observer.
        self.tocombo.Bind(EVT_WINDOW_DESTROY, lambda e: (e.Skip(), unregister_observers()))

    Buddy   = property(attrgetter('contact'))
    Account = property(attrgetter('account'))

    def Apply(self):
        if self.ischat: return

        self.tocombo._control = self

        self.ApplyTo()
        self.ApplyFrom()

    @property
    def HasChoices(self):
        'Returns True if there is more than one possible To/From pair.'

        return len(self.to_menu_items) > 1 or len(self.from_menu_items) > 1

    def ApplyTo(self):
        tocombo = self.tocombo
        if wx.IsDestroyed(tocombo) or self.ischat:
            return

        tocombo.SetCallbacks(selection = self.OnToBuddySelected, value = None)
        tocombo.SetItems(self.to_menu_items)
        tocombo.SetValue(self.to_menu_item)


    def ApplyFrom(self):
        fromcombo = self.fromcombo
        if wx.IsDestroyed(fromcombo):
            return

        fromcombo.SetItems(self.from_menu_items)
        fromcombo.SetValue(self.from_menu_item)
        fromcombo.SetCallbacks(selection = self.OnFromBuddySelected, value = None)

    def OnToBuddySelected(self, item):
        assert item in self.to_menu_items
        assert len(self.contacts) == len(self.to_menu_items)

        contact = self.contacts[self.to_menu_items.index(item)]

        if self.set_target(contact):
            info('selected %s', contact)
            self.Apply()

        self.OnSelection()

    def OnFromBuddySelected(self, item):
        assert item in self.from_menu_items
        assert len(self.accounts) == len(self.from_menu_items)

        i = self.from_menu_items.index(item)
        if self.set_account(self.accounts[i]):
            self.from_menu_item = self.from_menu_items[i]
            self.ApplyFrom()

        self.OnSelection()

    def contacts_changed(self, src, attr, old, new):
        wx.CallAfter(self.contacts_changed_gui, src, attr, old, new)

    def contacts_changed_gui(self, src, attr, old, new):
        self.generate_to_items()
        if getattr(self.tocombo, '_control', None) is self:
            self.Apply()

    def SetPersonality(self, personality):
        pass

    def SetConvo(self, convo, contacts = None):
        LOG('IMControl.SetConvo')
        LOG('  convo: %r', convo)
        LOG('  contacts: %r', contacts)

        self.ischat = convo.ischat
        if self.ischat:
            self.account = convo.protocol
            return

        old_contacts = set(getattr(self, 'contacts', []))

        if contacts is not None:
            self.contacts = contacts
            try: self.contacts.add_observer(self.contacts_changed)
            except AttributeError:
                pass

            self.generate_to_items()

        if not hasattr(self, 'contacts'):
            self.contacts = [convo.buddy]
            self.generate_to_items()

        new_contacts = set(self.contacts)
        changed = self.buddy_status_changed

        for new in new_contacts - old_contacts:
            new.add_observer(changed, 'status')
        for old in old_contacts - new_contacts:
            old.remove_observer(changed, 'status')

        if self.set_target(convo.buddy, from_account = convo.protocol):
            self.Apply()


    def buddy_status_changed(self, buddy, attr=None, old=None, new=None):
        wx.CallAfter(self.buddy_status_changed_gui, buddy, attr, old, new)

    @calllimit(.5)
    def buddy_status_changed_gui(self, buddy, attr=None, old=None, new=None):

        log.debug('buddy_status_changed %r %s (%s -> %s)', buddy, attr, old, new)

        try:
            i = self.contacts.index(buddy)
        except ValueError:
            wx.CallLater(1500, self.proto_change)
        else:
            self.to_menu_items[i] = buddy_menu_item(self.contacts[i])
            if self.contact is buddy:
                self.to_menu_item = self.to_menu_items[i]

        if getattr(self.tocombo, '_control', None) is self:
            if wx.IsDestroyed(self.tocombo):
                print >> sys.stderr, "WARNING: buddy_status_changed_gui being called but combo is destroyed"
            else:
                self.ApplyTo()

    def proto_change(self, *a):
        self.generate_to_items()
        log.debug('proto_change, new items: %r', self.to_menu_items)

        n, s = self.contact.name, self.contact.service
        for i, c in enumerate(self.contacts):
            if c.name == n and c.service == c:
                self.contact = c
                self.to_menu_item = self.to_menu_items[i]

        if getattr(self.tocombo, '_control', None) is self:
            self.ApplyTo()

    def generate_to_items(self):
        self.to_menu_items = [buddy_menu_item(b) for b in self.contacts]

    def set_to_item(self, contact):
        #settoitem:print '+'*80
        #settoitem:print 'set_to_item'
        #settoitem:print '  contact:', contact


        item = None
        for i, c in enumerate(self.contacts):
            #settoitem:print '    ', i, c
            #settoitem:print '       infokeys:', c.info_key, contact.info_key
            if c.info_key == contact.info_key:
                item = self.to_menu_items[i]
                break
        else:
            with traceguard:
                log.critical('could not match info_key %r against %r',
                             contact.info_key, [c.info_key for c in self.contacts])

            if len(self.to_menu_items) > 0:
                item = self.to_menu_items[i]

        self.to_menu_item = item

        #settoitem:print 'selected to item:', item
        #settoitem:print '+'*80

    def set_target(self, contact, from_account = None, disconnected=False):
        info('set_target (%r): %r', self, contact)

        self.set_to_item(contact)

        contacts = self.contacts

        suggested_account, contact, self.accounts = self.blist.imaccts_for_buddy(contact, contacts,
            force_has_on_list=disconnected)

        self.contact = contact
        LOG('%r', contact)
        LOG('  conn: %r', profile.connected_accounts)
        LOG('  sugg: %r', suggested_account)
        LOG('  capable: ' + ('%r, ' * len(self.accounts)), *self.accounts)

        self.account = from_account if from_account in self.accounts else suggested_account

        if type(self.contacts) is list and self.account is not None and self.account is not self.contact.protocol:
            log.warning('account did not match contact protocol, changing')
            self.contact = self.account.get_buddy(self.contact.name)
            self.contacts = [self.contact]
            self.contact.add_observer(self.contacts_changed)
            wx.CallLater(2000, self.buddy_status_changed, self.contact, 'status', None, None)
            self.OnSwitchContact(self.contact)

            log.warning('got %r with status %s', self.contact, self.contact.status)

        #fromlogics:print 'Final selections:', contact, self.account, '\n\n'

        self.set_to_item(self.contact)
        self._update_menu_items()
        return True

    def _update_menu_items(self):
        self.from_menu_items = [account_menu_item(a) for a in self.accounts]

        if self.from_menu_items:
            try:
                idx = self.accounts.index(self.account)
            except ValueError:
                item = ''
            else:
                item = self.from_menu_items[idx]
        else:
            item = ''

        self.from_menu_item = item

    def set_account(self, account):
        if self.account == account:
            return False

        self.account = account
        return True

    def on_connaccts_changed(self, *a):

        contact = self.contact
        account = self.account

        if not self.imwin.convo.ischat and getattr(self.tocombo, '_control', None) is self:
            if self.set_target(contact, account, disconnected=True):
                self.Apply()

            wx.CallLater(1000, self.buddy_status_changed, self.contact)

        if self.account != account and self.msgarea is not None:
            if account is not None:
                self.imwin.convo.system_message(_('{username} disconnected').format(username=account.username))

            if self.account is not None and self.contact is not None:
                self.imwin.convo.system_message(_('now sending from: {username}').format(username=self.account.username))


    def __repr__(self):
        return '<IMControl>'


class ComboListEditor(object):
    '''
    Given an UberCombo and a list of strings, allows the combo to "edit"
    the list.
    '''

    def __init__(self, combo, OnLoseFocus):
        self.combo = combo

        # the "remove" menu contains every item
        menu = combo.menu
        self.remove_menu = SimpleMenu(menu, combo.menuskin, callback = self.OnRemove)

        self.remove_item = SimpleMenuItem(_('Remove'), menu = self.remove_menu)
        self.add_item    = SimpleMenuItem(_('Add...'), method = self.OnAdd)

        self.OnLoseFocus = OnLoseFocus

    def SetContentCallback(self, cb):
        if not hasattr(cb, '__call__'): raise TypeError
        self.content_cb = cb

    def EditList(self, seq, selected_item = None,
                 add_cb = None,
                 remove_cb = None,
                 default = ''):

        self.default = default

        if add_cb is not None: self.add_cb = add_cb
        if remove_cb is not None: self.remove_cb = remove_cb

        assert isinstance(seq, list), repr(list)
        self.seq         = list(seq)
        self.menu_items  = [SimpleMenuItem(self.content_cb(i)) for i in seq]
        self.remove_menu.SetItems(list(self.menu_items))

        if selected_item is not None:
            self.selection   = seq.index(selected_item)
        else:
            self.selection = -1 if len(seq) == 0 else 0

    def Apply(self):
        items = list(self.menu_items)                 # Normal Items

        if len(self.menu_items):
            items.append(SimpleMenuItem(id = -1)),    # ---- a separator

        items.append(self.add_item)                   # Add

        if len(self.menu_items):
            items.append(self.remove_item)  # Remove (if there are items to remove)

        combo = self.combo
        combo.SetCallbacks(selection = self.OnComboSelection,
                           value     = self.OnValue)
        combo.menu.SetItems(items)

        newval = self.menu_items[self.selection] if len(self.menu_items) and self.selection != -1 else self.default
        combo.ChangeValue(newval)

    def OnComboSelection(self, item):
        LOG('OnSelection: %r', item)

        self.selection = self.menu_items.index(item)
        self.combo.ChangeValue(item)
        self.OnLoseFocus()

    def GetValue(self):

        return self.menu_items[self.selection].GetContentAsString() if self.selection != -1 else (None if not self.default else self.default)

    def OnAdd(self, item):
        'Invoked when the "Add" menu item is clicked.'

        self.combo.EditValue('')

    def OnValue(self, val):
        wx.CallAfter(self.OnValueLater, val)

    def OnValueLater(self, val):

        # This method is called when the editable part of the combo loses focus.
        # - if the combo is on screen, the user hit enter or otherwise caused this to happen.
        #   in this case, perform validation and display an error dialog if the validation fails
        # - otherwise, maybe another app stole focus--some external event cause this to happen
        #   popping up a modal dialog would be bad, so just return the value to what it was before

        if val == '' or not self.combo.IsShown() or not self.combo.Top.IsActive():

            LOG("Val: %s\nCombo is ShownOnScreen: %s\nTop level parent is Active: %s",
                val, self.combo.IsShownOnScreen(), not self.combo.Top.IsActive())

            if val == '': LOG('empty string, selection is %s', self.selection)
            else:         LOG('combo not on screen, falling back to %s', self.selection)

            # Restore the combo's value.
            if self.combo.Top.IsActive():
                self.OnLoseFocus()
            return self.combo.ChangeValue(self.menu_items[self.selection] if self.selection != -1 else self.default)

        val = self.add_cb(val)

        if val is None:
            self.combo.EditValue()
        else:
            LOG('add_cb returned True')

            self.seq.append(val)
            self.menu_items.append(SimpleMenuItem(self.content_cb(val)))
            self.remove_menu.AppendItem(SimpleMenuItem(self.content_cb(val)))
            self.selection = len(self.menu_items)-1
            self.Apply()


    def OnRemove(self, item):
        'Invoked when one of the "remove" menu items is clicked.'
        i = self.remove_menu.GetItemIndex(item)
        assert len(self.menu_items) <= len(self.remove_menu)

        if self.remove_cb(self.seq[i]):
            LOG('removing item %d (selection is %s)', i, self.selection)
            self.seq.pop(i)
            self.remove_menu.RemoveItem(i)
            self.menu_items.pop(i)

            if i == self.selection:
                l = len(self.menu_items)
                if l:
                    i = i % len(self.menu_items)
                    newval = self.menu_items[i]
                else:
                    i = -1
                    newval = self.default
                self.combo.ChangeValue(newval)
            elif i < self.selection:
                i -= 1

            self.selection = i
            LOG('now selection is %s', self.selection)
            self.Apply()

class BInfoControl(object):
    def __init__(self, tocombo, fromcombo, info_attr, content_cb):
        self.tocombo, self.fromcombo = tocombo, fromcombo
        self._editing = False

        assert isinstance(info_attr, str)
        self.info_attr = info_attr

        self.OnLoseFocus = Delegate()
        e = self.to_editor = ComboListEditor(tocombo, self.OnLoseFocus)
        e.SetContentCallback(content_cb)

        self.blist = profile.blist

class SMSControl(BInfoControl):
    def __init__(self, tocombo, fromcombo):
        BInfoControl.__init__(self, tocombo, fromcombo, 'sms', sms_menu_content)
        self.acct = None

        caccts = profile.connected_accounts

        cb = repeat_guard(lambda *a, **k: wx.CallAfter(self.conn_accts_changed, *a, **k))
        caccts.add_observer(cb, obj = self)
        self.conn_accts_changed(caccts)
        self.tocombo.Bind(EVT_WINDOW_DESTROY, lambda e: (e.Skip(), caccts.remove_observer(cb)))

    def conn_accts_changed(self, *a):
        wx.CallAfter(self.update_senders)

    def update_senders(self):
        LOG('SMSControl: connected accounts changed')
        senders = self.sms_senders()
        LOG("%r", senders)
        self.from_menu_items = [account_menu_item(a) for a in senders]

        if self.acct not in senders:
            self.acct = senders[0] if senders else None

        if getattr(self.tocombo, '_control', None) is self:
            self.Apply()

    @property
    def ToSMS(self):
        'Returns the currently selected SMS number. (can be None)'

        if self.contact_sms:
            return self.contact_sms
        else:
            return self.to_editor.GetValue()

    @property
    def FromAccount(self):
        'Returns the currently selected account to send SMS messages from. (can be None)'

        return self.acct

    def SetContact(self, contact):
        self.info_key = contact.info_key
        self.contact_sms = None #contact.name if contact.sms else None
        self.update_items()

    def get_contact_sms(self):
        sms = self.blist.get_contact_info(self.info_key, self.info_attr)

        if not isinstance(sms, list):
            return []

        return [s for s in sms if isinstance(s, basestring)]

    def sms_senders(self):
        return [a.connection for a in profile.connected_accounts
                if a.connection is not None and can_send_sms(a.connection.service)]

    def update_items(self):
        # get list of SMS numbers for our contact
        sms = self.get_contact_sms()

        if self.contact_sms:
            self.sms_item = SimpleMenuItem([self.contact_sms])
        else:

            # obtain a "best choice" SMS number
            best_sms, best_acct  = self.blist.get_tofrom_sms(self.info_key)

            self.to_editor.EditList(sms, best_sms,
                                    add_cb    = self.OnAddSMS,
                                    remove_cb = self.OnRemoveSMS)

    def Apply(self):
        self.tocombo._control = self

        # Set To
        if self.contact_sms:
            self.tocombo.SetCallbacks(None, None)
            self.tocombo.SetItems([])
            self.tocombo.ChangeValue(self.contact_sms)
        else:
            wx.CallAfter(self.to_editor.Apply)

        # Set From
        senders = self.sms_senders()
        i = senders.index(self.acct) if self.acct in senders else -1
        self.fromcombo.SetItems(self.from_menu_items)
        self.fromcombo.ChangeValue(self.from_menu_items[i] if i != -1 else '')
        self.fromcombo.SetCallbacks(None, None)

    def OnAddSMS(self, sms):
        blist   = self.blist
        smslist = blist.get_contact_info(self.info_key, 'sms')
        smslist = list(smslist) if smslist is not None else []

        try:
            sms = normalize_sms(sms)
        except ValueError:
            MessageBox(_('Please enter a valid SMS number (ie: 555-555-5555 or 5555555555)'),
                       _('Invalid SMS Number'), style = wx.ICON_ERROR)
        else:
            if sms not in smslist:
                smslist.append(sms)
                blist.set_contact_info(self.info_key, 'sms', smslist)
                self.OnLoseFocus()
                return sms
            else:
                MessageBox(_("That SMS number is already in this buddy's list."),
                           _('Add SMS Number'))


    def OnRemoveSMS(self, sms):
        blist  = self.blist
        smslist = blist.get_contact_info(self.info_key, 'sms')
        smslist = list(smslist) if smslist is not None else []

        if sms in smslist:
            smslist.remove(sms)
            blist.set_contact_info(self.info_key, 'sms', smslist)
            self.OnLoseFocus()
            return True

class EmailControl(BInfoControl):
    def __init__(self, tocombo, fromcombo):
        BInfoControl.__init__(self, tocombo, fromcombo, 'email', email_menu_content)

        self._obs_link = None
        self.setup_from_accts()
        self.OnEmailAccountChanged = Delegate()

    @property
    def ToEmail(self):
        return self.to_editor.GetValue()

    @property
    def FromAccount(self):
        return self.acct

    def setup_from_accts(self):
        # add an "Add" menu containing each email account type
        self.addList = addList = SimpleMenu(self.fromcombo.menu, 'simplemenu')
        for emailtype in emailprotocols.keys():
            addList.Append([skinget('serviceicons.%s' % emailtype).Resized(16),
                            protocols[emailtype].name],
                            method = lambda item, emailtype=emailtype: add_email_account(emailtype))

        # link to creating an email account
        from gui.pref import prefsdialog
        self.accounts_item = SimpleMenuItem(_('Accounts...'), method = lambda *a: prefsdialog.show('accounts'))

        # watch the email list for changes
        pass

        self._obs_link = profile.emailaccounts.add_list_observer(self.on_email_accounts_changed, self.on_email_accounts_changed, 'enabled')

        self.tocombo.Bind(EVT_WINDOW_DESTROY, lambda e: (e.Skip(), self.unregister_observers()))

    def unregister_observers(self, *a):
        if self._obs_link is not None:
            self._obs_link.disconnect()
            self._obs_link = None
        profile.emailaccounts.remove_list_observer(self.on_email_accounts_changed, self.on_email_accounts_changed, 'enabled')

    @wxcall
    def on_email_accounts_changed(self, src, attr, old, new):
        if getattr(self.tocombo, '_control', None) is self:
            self.ApplyFrom()

    def SetContact(self, contact):
        self.info_key = contact.info_key
        hint     = getattr(contact, 'email_hint', '')
        email_list    = self.blist.get_contact_info(self.info_key, 'email')

        if email_list is None: email_list = []

        self.to_editor.EditList(email_list,
                                add_cb    = self.OnAddEmail,
                                remove_cb = self.OnRemoveEmail,
                                default   = hint)


    def OnAddEmail(self, email):
        blist  = self.blist
        emails = blist.get_contact_info(self.info_key, 'email')
        emails = list(emails) if emails is not None else []

        if not is_email(email):
            MessageBox(_('Please enter a valid email address (ie: john123@digsby.com)'),
                       _('Invalid Email Address'), style = wx.ICON_ERROR)

        elif email in emails:
            MessageBox(_('That email is already registered with this buddy.'),
                       _('Add Email Address'))

        else:
            emails.append(email)
            blist.set_contact_info(self.info_key, 'email', emails)
            self.OnLoseFocus()
            return email


    def OnRemoveEmail(self, email):
        blist  = self.blist
        emails = blist.get_contact_info(self.info_key, 'email')
        emails = list(emails) if emails is not None else []

        if email in emails:
            emails.remove(email)
            blist.set_contact_info(self.info_key, 'email', emails)
            self.OnLoseFocus()
            return True

    def Apply(self):
        self.tocombo._control = self

        LOG('Control.Apply: %s', self.info_attr)
        self.to_editor.Apply()
        self.ApplyFrom()

    def ApplyFrom(self):
        frm   = self.fromcombo
        accts = [a for a in profile.emailaccounts if a.enabled]

        #TODO: UberCombo doesn't store items :(

        def sel(item, acct):
            frm.ChangeValue(item)
            self.OnEmailAccountChanged(acct)
            self.acct = acct

        # Create menu items for each enabled email account.
        fitems = self.from_menu_items = []
        for a in accts:
            item = SimpleMenuItem(emailacct_menu_content(a), method = lambda item, a=a: sel(item, a))
            item.acct = a
            fitems.append(item)

        # Add extra account managment items.
        items = list(fitems)

        if len(fitems):
            items.append(SimpleMenuItem(id = -1)) # separator

        items.append(SimpleMenuItem(_('Add Email Account'), menu = self.addList))
        items.append(self.accounts_item)

        self.fromcombo.SetCallbacks(None, None)
        self.fromcombo.SetItems(items)


        if accts:
            try:                i = accts.index(getattr(self, 'acct', None))
            except ValueError:  i = 0

            sel(fitems[i], accts[i])
        else:
            self.fromcombo.ChangeValue('')
            self.OnEmailAccountChanged(None)




tofromIconSize = lambda: int(skinget('capabilities.tofrom.iconsize', 16))


def buddy_menucontent(buddy):
    return [skinget("statusicons.%s"  % buddy.status_orb),
            buddy.serviceicon.Resized(tofromIconSize()), buddy.nice_name]

def buddy_menu_item(buddy):
    'Return a menu item object for a "To" buddy.'

    return SimpleMenuItem(buddy_menucontent(buddy))

def account_menucontent(acct):
    'Returns the menu content for a "from" account.'

    return [acct.serviceicon.Resized(tofromIconSize()),
            acct.username]

def account_menu_item(acct):
    'Return a menu item object for a "From" account.'

    return SimpleMenuItem(account_menucontent(acct))

def email_menu_content(email):
    return [email]

def sms_menu_content(sms):
    return [sms]

def emailacct_menu_content(emailacct):
    return [emailacct.icon.Resized(16), emailacct.display_name]

def add_email_account(protocol_name):
    from gui.accountdialog import AccountPrefsDialog
    import wx
    diag = AccountPrefsDialog.create_new(wx.GetTopLevelWindows()[0], protocol_name)
    res = diag.ShowModal()

    if diag.ReturnCode == wx.ID_SAVE:
        profile.add_email_account(**diag.info())

    diag.Destroy()
