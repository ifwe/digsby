'''

A status combo box for quickly choosing statuses.

Also doubles as a searchbox for the buddylist.

'''

from __future__ import with_statement

import wx
from gui import skin
from gui.uberwidgets.UberCombo import UberCombo
from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.simplemenu import SimpleMenuItem, SimpleMenu
from common.statusmessage import StatusMessage
from logging import getLogger; log = getLogger('statuscombo'); info = log.info
from common import profile, search, pref, setpref
from gui.toolbox import calllimit
from gui.toolbox.keynames import non_alphanumeric
from util.primitives.funcs import Delegate

from gui.status import new_custom_status

import gui.model.menus as menus
import actionIDs
import hooks

from peak.util.plugins import Hook

# this is a dict of status -> ID references that we re-create each time a popup menu
# is displayed.
status_dict = {}

def PROMOTE_STATUS_STRING():
    import branding
    url = branding.get('digsby.promote.url', 'digsby_promote', 'http://im.digsby.com')
    return u'I use Digsby to manage IM + Email + Social Networks - ' + url

def set_profile_status(msg):
    '''
    The combo calls this method by default when setting a new status.

    This can be changed in the constructor.
    '''
    import hooks; hooks.notify('digsby.statistics.ui.select_status')
    return profile.set_status(msg)

def get_profile_status():
    return profile.status

BUTTON_HOLD_TIME = 1000

def group_profile_statuses():
    msgs = sorted((c for c in profile.statuses), key = lambda msg: msg.away)

    j = -1
    for j, msg in enumerate(msgs):
        if msg.away: break
    else:
        j = -1

    if j == -1:
        j = len(msgs)

    avail_msgs = msgs[:j]
    avail_msgs.insert(0, StatusMessage.Available.copy())

    away_msgs = msgs[j:]
    away_msgs.insert(0, StatusMessage.Away.copy())
    return avail_msgs, away_msgs, filter(None, [s() for s in Hook('digsby.im.statusmessages')])

def get_profile_statuses():

    # Find where to insert the special "Away" status item
    avail, away, plugins = group_profile_statuses()

    return avail + away + plugins

def umenuitem(menu, status):
    menu.AddItem(status.title, bitmap = status.icon,
                 callback = lambda status=status: profile.set_status(status))

def global_status_enabled():
    return pref('social.use_global_status', type = bool, default = False)

def add_global_to_menu(menu, text = _('Global Status'), use_icon = True, icon_key = 'icons.globalstatus', init_text = u''):
    if not global_status_enabled():
        return

    _add_thingy_to_menu(menu, text, use_icon, icon_key, init_text)

def _add_thingy_to_menu(menu, text, use_icon, icon_key, init_text):
    if use_icon:
        bmp = skin.get(icon_key)
    else:
        bmp = None
    menu.AddItem(text, bitmap = bmp,
                 callback = lambda: wx.GetApp().SetStatusPrompt('ALL',
                                                                initial_text = init_text,
                                                                editable = False,
                                                                edit_toggle = False,
                                                                select_text = bool(init_text)))

def add_promote_to_menu(menu, text = _('Promote Digsby!'), use_icon = True, icon_key = 'statusicons.promote',
                        init_text = None):
    if init_text is None:
        init_text = PROMOTE_STATUS_STRING()
    if not global_status_enabled():
        return
    return _add_thingy_to_menu(menu, text, use_icon, icon_key, init_text)

def status_menu(menu, add_custom = False, add_global = False, add_promote = False):
    'Adds statuses to menu.'

    avail, away, plugins = group_profile_statuses()

    for status in avail:
        umenuitem(menu, status)

    for status in away:
        umenuitem(menu, status)

    if add_custom:
        menu.AddItem(_('Custom...'),
                     callback = lambda: edit_custom_status(None))

    menu.AddSep()

    if add_global:
        add_global_to_menu(menu)

    for status in plugins:
        umenuitem(menu, status)

    if add_promote:
        add_promote_to_menu(menu)

    umenuitem(menu, StatusMessage.Invisible.copy(message = profile.status.message))

    if profile.allow_status_changes:
        # cannot go offline while only connected account is to the Digsby servers
        umenuitem(menu, StatusMessage.Offline)


def create_status_menu(add_custom=False, add_global = False):
    '''
    status_menu function adapted to work with gui.model.menus instead of UMenu
    '''
    status_menu = menus.Menu()
    global status_dict

    status_dict = {}

    for status in get_profile_statuses():
        status_dict[status] = wx.NewId()
        item = status_menu.addItem(status.title, id=status_dict[status], bitmap=status.icon)

    if add_custom:
        status_menu.addItem(_('Custom...'), id=actionIDs.SetStatusCustom)

    status_menu.addSep()

    if add_global and global_status_enabled():
        status_menu.addItem(_('Global Status'), bitmap = skin.get('icons.globalstatus'), id = actionIDs.SetStatusGlobal)

    invisible = StatusMessage.Invisible.copy(message = profile.status.message)
    status_dict[invisible] = wx.NewId()
    status_menu.addItem(invisible.title, id=status_dict[invisible], bitmap=invisible.icon)

    if profile.allow_status_changes:
        # cannot go offline while only connected account is to the Digsby servers
        offline = StatusMessage.Offline
        status_dict[offline] = wx.NewId()
        status_menu.addItem(StatusMessage.Offline.title, id=status_dict[offline], bitmap=StatusMessage.Offline.icon)

    return status_menu

def edit_custom_status(window_parent):
    '''
    Show GUI to edit a custom status.
    '''

    s = profile.status

    if s.editable:
        new_custom_status(window_parent, init_status = s.copy(), save_checkbox = True)
    else:
        # Don't copy the messages from non-editable statuses like Now Playing
        new_custom_status(window_parent, save_checkbox = True)

def edit_global_status():
    wx.CallAfter(wx.GetApp().SetStatusPrompt)


class StatusCombo(UberCombo):

    # number of milliseconds to wait after clicking the status button before the
    # status is set (if the user hasn't entered any text)
    set_delay = 3000

    def __init__(self, parent, buddylist, statuses,
                 get_status_method = get_profile_status,
                 set_status_method = set_profile_status):
        '''
        StatusCombo constructor.

        parent   - a wx.Window parent window
        statuses - an observable list of StatusMessage objects
        '''

        self.buddylist = buddylist
        self.buddylist.Bind(wx.EVT_KEY_DOWN, self.on_buddylist_key)
        self.searching = False
        self.searchHintShown = False

        if not getattr(StatusCombo, 'searchThresholdRegistered', False) and pref('search.buddylist.show_hint', True):
            def SearchThresholdReached(*a, **k):
                if pref('search.buddylist.show_hint', True):
                    setpref('search.buddylist.show_hint', False)
            Hook('digsby.achievements.threshold', 'buddylist.search').register(SearchThresholdReached)
            StatusCombo.searchThresholdRegistered = True

        self.offline_item = None
        self.get_profile_status = get_status_method
        self.set_profile_status = set_status_method

        status = self.get_profile_status()

        UberCombo.__init__(self, parent, skinkey = 'combobox',
                           typeable = True,
                           valuecallback  = self.on_text_lose_focus,
                           empty_text=getattr(status, 'hint', status.title.title()),
                           maxmenuheight = 15)

        self.buttoncallback = self.on_status_button
        self.cbutton = UberButton(self, -1, skin=self.cbuttonskin)
        self.cbutton.Bind(wx.EVT_BUTTON, self._on_left_button)
        self.content.Insert(0,self.cbutton, 0, wx.EXPAND)

        self.cbutton.BBind(RIGHT_UP  = self.on_status_button_right_click,
                           LEFT_DOWN = self.on_status_button_left_click,
                           LEFT_UP   = self.on_status_button_left_up)

        self.display.Bind(wx.EVT_LEFT_DOWN, lambda e: (e.Skip(), setattr(self, 'oldValue', self.Value)))


        # the on_allow_status_changes method is called when the list of connected
        # im accounts changes size. if all accounts are offline this control
        # becomes disabled..

        #profile.account_manager.connected_accounts.add_observer(self.on_allow_status_changes)
        profile.account_manager.connected_accounts.add_observer(self.on_offline_allowed, obj = self)

        # Listen on status messages (changes, additions, deletes).
        _obs_link = statuses.add_list_observer(self.on_status_messages_changed,
                                               self.on_status_messages_changed)
        self.Bind(wx.EVT_WINDOW_DESTROY,
                  lambda e: (log.info('status combo removing observers'), e.Skip(), _obs_link.disconnect()))

        self.on_status_messages_changed(statuses)

        # when the profile's status changes, update to reflect it
        profile.add_observer(self.on_profile_status_changed, 'status')

        # Display the current status.
        self.show_status(self.get_profile_status())

        # Timer for committing status messages after a delay.
        self.timer = wx.PyTimer(self.SetFocus)
        self.Bind(wx.EVT_TEXT, self.on_typing)

        self.button_timer = wx.PyTimer(self.on_status_button_right_click)

        textbind = self.TextField.Bind
        textbind(wx.EVT_SET_FOCUS, lambda e: setattr(self, 'skipenter', False))
        textbind(wx.EVT_KEY_DOWN, self._on_key_down)
        textbind(wx.EVT_TEXT_ENTER, self._on_enter)

        self.DropDownButton.Bind(wx.EVT_LEFT_DOWN, self._dbutton_left)

        self.OnActivateSearch = Delegate()
        self.OnDeactivateSearch = Delegate()

    def UpdateSkin(self):
        key = 'statuspanel'

        if not skin.get(key, False) or skin.get(key+ '.mode','') == 'native':
            s = lambda k,d: None
        else:
            s = lambda k, default: skin.get('%s.%s' % (key, k), default)

        comboskinkey = s('comboboxskin',None)
        self.cbuttonskin = cbskinkey = s('statusbuttonskin',None)


        self.SetSkinKey(comboskinkey)
        UberCombo.UpdateSkin(self)

        if hasattr(self, 'cbutton'):
            self.cbutton.SetSkinKey(cbskinkey, True)
            self.SetButtonIcon(StatusMessage.icon_for(self.status_state))


        if hasattr(self,'menu') and self.menu:
            self.on_status_messages_changed()


    def SetButtonIcon(self, icon):
        """set the icon for the cycle button"""
        self.cbutton.SetIcon(icon)
        self._button_icon = icon
        self.Layout()

    def SetCallbacks(self, selection = sentinel, value = sentinel, button = sentinel):
        'Sets callbacks for this combobox.'

        UberCombo.SetCallbacks(self, selection, value)
        if button is not sentinel: self.buttoncallback = button

    def on_allow_status_changes(self, *a, **k):
        if self.Show(profile.allow_status_changes):
            self.Parent.gui_layout()

    def setandshow(self, statusmsg):
        'Immediately sets the status message and shows it.'

        log.info('setandshow %r', statusmsg)
        self.oldValue = None
        self.show_status(statusmsg)
        self.set_profile_status( statusmsg )

    def show_status(self, status, force=False):
        'Displays the specified status message.'

        if not force and status is getattr(self, '_shown_status', None):
            return

        # make the text area not editable for statuses like "Invisble" and
        # "Offline", which have the "editable" attribute set to False
        self.Editable = status.editable

        self.display.empty_text = getattr(status, 'hint', '')
        self.ChangeValue(status.message)                    # change text
        self.SetButtonIcon(StatusMessage.icon_for(status))  # change icon
        self.status_state = status.status                   # store the state
        self._shown_status = status

    #
    # events
    #

    def on_typing(self, e):
        'Invoked when the user is typing in the textfield.'

        if self.searching:
            search.link_prefs(profile.prefs)
            e.Skip()
            self.buddylist.search(e.EventObject.Value)
        else:
            self.cancel_timer()

    def on_status_button(self, button):
        '''
        Invoked when the user clicks the state button to the left of the
        dropdown.
        '''
        # toggle the control's status state
        isavail = StatusMessage.is_available_state(self.status_state)

        # do we need to change the shown text?
        needs_change = self._shown_status in StatusMessage.SpecialStatuses or not self._shown_status.editable

        self.oldValue = None

        self.change_state(state = 'Away' if isavail else 'Available',)
                          #change_text = needs_change)

    def change_state(self, state, change_text = False):
        if not isinstance(state, basestring):
            raise TypeError('change_state takes a string got a %s' % type(state))
        self.status_state = state

        if change_text:
            self.ChangeValue(self.status_state, state.title())
        else:
            self.Default = state.title()

        edit_toggle = getattr(profile.status, 'edit_toggle', True)
        if getattr(profile.status, 'edit_toggle', True):
            # update the icon
            self.SetButtonIcon(StatusMessage.icon_for(self.status_state))

            self.cancel_timer()
            self.timer.StartOneShot(self.set_delay)

            # select all text in the textfield
            disp = self.display
            disp.TypeField()
            wx.CallAfter(disp.txtfld.SetSelection, -1, -1)
        else:
            self.setandshow(profile.status.copy(status = self.status_state, editable = None, edit_toggle = None))

    def on_status_button_left_click(self, e = None):
        if self.searching:
            return self.TextField.SetFocus()
        self.skipenter = True
        self.button_timer.Start(BUTTON_HOLD_TIME, True)
        if e: e.Skip(True)

    def on_status_button_left_up(self, e = None):
        if not self.searching:
            self.button_timer.Stop()
        if e: e.Skip(True)

    def on_status_button_right_click(self, e = None):
        if not self.searching:
            self.show_extended_status_menu()

    def show_extended_status_menu(self):
        from gui.status import get_state_choices

        m = SimpleMenu(self, skinkey = skin.get('%s.MenuSkin'%self.skinkey))

        for status in get_state_choices():
            statusname, statuslabel = status

            def onclick(item, state=statusname):
                self.change_state(state)#, change_text = self.status_state == self.GetValue())

            m.AppendItem(SimpleMenuItem([StatusMessage.icon_for(statusname), statuslabel],
                                        method = onclick))

        if m.GetCount() > 0:
            m.Display(self.cbutton)

    def on_text_lose_focus(self, new_msg):
        if self.searching:
            return self.on_search_timer()

        # Cancel the status button timer if it's running.
        self.cancel_timer()

        if getattr(self, 'skipenter', False):
            wx.CallAfter(lambda: setattr(self, 'skipenter', False))
        else:
            # don't set status if we lost focus because the user is clicking
            # on the state button
            if wx.GetMouseState().LeftDown() and wx.FindWindowAtPoint(wx.GetMousePosition()) is self.cbutton:
                return

            profile_status = self.get_profile_status()
            if new_msg == '':
                self.display.empty_text = profile_status.hint
            if new_msg != profile_status.message or self.status_state != profile_status.status:
                # entering a new text value clears all exceptions
                newmsg = StatusMessage(new_msg, self.status_state, new_msg)
                self.set_profile_status(newmsg)

    def on_profile_status_changed(self, *a):
        "Invoked when the profile's status changes."

        self.show_status(profile.status)

    @calllimit(1)
    def on_offline_allowed(self, *a):
        if not self: return
        show_offline = profile.allow_status_changes

        if not show_offline and self.offline_item:
            log.info('removing the offline item')
            self.RemoveItem(self.offline_item)
            self.offline_item = None
        elif show_offline and not self.offline_item:
            log.info('adding the offline item')
            self.offline_item = self.additem([skin.get('statusicons.offline'),  _('Offline')], self.on_offline)


    def additem(self, *a, **k):
        i = SimpleMenuItem(*a, **k)
        self.AppendItem(i)
        return i

    @calllimit(1)
    def on_status_messages_changed(self, *a):
        '''
        Invoked when a status message changes, or the user status list changes.

        Rebuilds the status menu items.
        '''
        log.info('on_status_messages_changed, updating menu')

        self.RemoveAllItems()
        additem = self.additem

        def add_status_item(pname, name):
            additem([skin.get('statusicons.%s' % pname), name],
                     method = getattr(self, 'on_' + pname))

        # Available
        add_status_item('available', _('Available'))

        # user statuses
        self.sortedstatuses = msgs = sorted([c for c in profile.statuses],
                                            key = lambda msg: msg.away)

        # Find where to insert the special "Away" status item
        j = -1
        found = False
        for j, msg in enumerate(msgs):
            if msg.away:
                found = True
                break

        for i, msg in enumerate(msgs):
            if found and i == j:
                add_status_item('away', _('Away'))
            online_image = skin.get('statusicons.away' if msg.away else 'statusicons.available')
            additem([online_image, msg.title], method = lambda mi, msg=msg: self.setandshow(msg), id = i)

        if not found or j == -1:
            add_status_item('away', _('Away'))


        # Custom...
        additem(_('Custom...'), method = self.on_custom)
        self.AppendSeparator()
        if global_status_enabled():
            additem([skin.get('icons.globalstatus'), _('Global Status')],
                    method = self.on_global)

        log.info('updating status menu with %d extra statuses', len(Hook('digsby.im.statusmessages')))
        for msg in Hook('digsby.im.statusmessages'):
            message = msg()
            if message is None:
                continue
            additem([message.icon, message.title], method = lambda mi, msg=msg: self.setandshow(msg()))

        if global_status_enabled():
            additem([skin.get('statusicons.promote'), _('Promote Digsby!')],
                    method = self.on_promote)

        # Invisible
        additem([skin.get('statusicons.invisible'),  _('Invisible')], self.on_invisible)

        # Offline
        self.offline_item = None
        self.on_offline_allowed()


    #
    # special entries in the status menu.
    #

    def on_offline(self, combo_item):
        self.setandshow(StatusMessage.Offline)

    def on_available(self, comboitem):
        self.show_status(StatusMessage.Available)
        self.display.TypeField()

    def on_away(self, comboitem):
        self.show_status(StatusMessage.Away)
        self.display.TypeField()

    def on_custom(self, combo_item):
        edit_custom_status(self)

    def on_global(self, combo_item):
        wx.CallAfter(wx.GetApp().SetStatusPrompt)

    def on_promote(self, combo_item):
        wx.CallAfter(wx.GetApp().SetStatusPrompt, 'ALL', PROMOTE_STATUS_STRING(), editable = False, edit_toggle = False)

    def on_nowplaying(self, combo_item):
        self.setandshow(StatusMessage.NowPlaying)

    def on_invisible(self, combo_item):
        sta = self.get_profile_status()
        cpy = StatusMessage.Invisible.copy(message=sta.message)
        self.setandshow(cpy)

    def cancel_timer(self):
        if self.timer.IsRunning():
            self.timer.Stop()

    #
    # search functionality
    #

    def _on_left_button(self, e):
        if not self.searching:
            return self.buttoncallback(self.cbutton)

    def _on_enter(self, e):
        if self.searching:
            self.buddylist.activate_selected_item()
            self.stop_searching()
        else:
            e.Skip()

    def _on_key_down(self, e):
        if self.searching:
            if e.KeyCode == wx.WXK_ESCAPE:
                self.buddylist.SetFocus()
                self.stop_searching()
            elif e.KeyCode in txtcontrol_keys:
                e.Skip()
            else:
                self.buddylist.on_key_down(e)
        else:
            e.Skip()

    def _interpret_char_event(self, e):
        key = None
        backspace = False

        if e is not None:
            mod = e.Modifiers & ~wx.MOD_SHIFT
            if e.KeyCode == wx.WXK_BACK:
                backspace = True
            elif mod or e.KeyCode <= ord(' ') or e.KeyCode in non_alphanumeric:
                return key, backspace
            else:
                key = unichr(e.UnicodeKey)

        return key, backspace


    def ShowSearchHint(self):
        self.searchHintShown = True

        def size_like(img, i):
            img = img.ResizedSmaller(max(i.Width, i.Height)).PIL
            return img.ResizeCanvas(i.Width, i.Height).WXB

        self.cbutton.SetIcon(size_like(skin.get('StatusPanel.SearchIcon'), self._button_icon))
        self.DropDownButton.SetIcon(skin.get('StatusPanel.CancelSearchIcon'))
        self.display.DisplayLabel = _("Press 'Ctrl+F' to Search List")

    def HideSearchHint(self):
        self.SetButtonIcon(self._button_icon)
        self.DropDownButton.SetIcon(self.dropdownicon)
        self.searchHintShown = False
        self.display.DisplayLabel = None

    def search(self, e=None):
        if not pref('search.buddylist.enabled', True):
            if e is not None: e.Skip()
            return

        key, backspace = self._interpret_char_event(e)

        def size_like(img, i):
            img = img.ResizedSmaller(max(i.Width, i.Height)).PIL
            return img.ResizeCanvas(i.Width, i.Height).WXB

        icon = skin.get('StatusPanel.SearchIcon')
        self.ForceTextFieldBackground = True
        self.cbutton.SetIcon(size_like(icon, self._button_icon))
        self.DropDownButton.SetIcon(skin.get('StatusPanel.CancelSearchIcon'))
        self.searching = True
        if not hasattr(self, 'search_timer'):
            self.search_timer = wx.PyTimer(self.on_search_timer)
        self.search_timer.Start(500)

        self.display.TypeField()

        # emulate a keypress if one started the search
        self.TextField.ChangeValue(profile.blist.search_string)

        if key is not None:
            self.TextField.AppendText(key)
        if backspace:
            # emulate a backspace
            size = self.TextField.LastPosition
            self.TextField.Remove(size-1, size)

        self.OnActivateSearch()

    def on_search_timer(self):
        active = wx.GetActiveWindow()
        focused = wx.Window.FindFocus()

        if active is None or not self.searching:
            self.stop_searching()

        if not hasattr(self, '_allowed_windows'):
            # active windows search will stick around for
            from gui.infobox.infobox import InfoBox
            from gui.buddylist.buddylistframe import BuddyListFrame
            from gui.searchgui import SearchEditDialog

            self._allowed_windows = frozenset([InfoBox, BuddyListFrame, SearchEditDialog])
            self._empty_textfield_cancels = frozenset([BuddyListFrame])

        clz = active.__class__

        if clz not in self._allowed_windows:
            self.stop_searching()

        # if search loses focus to the buddylist and there is no text in the
        # search field, just cancel the search
        elif clz in self._empty_textfield_cancels and \
                focused is not self.TextField and \
                not self.TextField.Value:
            self.stop_searching()

    def stop_searching(self):
        if not self.searching:
            return

        log.info('stopping search')
        self.ForceTextFieldBackground = False
        self.SetButtonIcon(self._button_icon)
        self.DropDownButton.SetIcon(self.dropdownicon)
        self.search_timer.Stop()
        self.searching = False
        focused_window = wx.Window.FindFocus()
        if focused_window is self.TextField:
            self.buddylist.SetFocus()
        self.show_status(get_profile_status(), force=True)
        self.buddylist.clear_search()
        self.OnDeactivateSearch()

        hooks.notify('digsby.statistics.buddylist.search')

    def _dbutton_left(self, e):
        if self.searching:
            return self.stop_searching()
        else:
            e.Skip()

    def on_buddylist_key(self, e):
        if self.searching and e.KeyCode == wx.WXK_ESCAPE:
            self.stop_searching()
        else:
            e.Skip()

# keys which, when focus is in the statuscombo's text control, are not
# forwarded to the buddylist when searching.
txtcontrol_keys = frozenset([
    wx.WXK_LEFT,
    wx.WXK_RIGHT,
    wx.WXK_NUMPAD_LEFT,
    wx.WXK_NUMPAD_RIGHT
])
