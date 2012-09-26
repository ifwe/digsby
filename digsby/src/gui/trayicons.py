'''
the main digsby tray icon
'''

import config
import sys
import wx
import hooks
import actionIDs
from common import profile, pref
from config import platformName
from logging import getLogger; log = getLogger('trayicons')
from gettext import ngettext
from gui import statuscombo
from gui.toolbox import draw_tiny_text, to_icon
from gui.taskbar import AnimatedTaskBarIcon
from gui.uberwidgets.umenu import UMenu
from gui.windowfx import vista

TRAY_SHOW_STATUS_PREF = 'trayicons.digsby.show_status_orb'

MAIN_ICON = 0
MESSAGE_ICON = 1

TASKBAR_REFRESH_MS = 5 * 60 * 1000

UNREADPREF = 'trayicons.digsby.unread_messages.'

class BuddyListEventHandler(object):
    def __init__(self):
        bind = wx.GetApp().Bind

        bind(wx.EVT_MENU, self.OnShowHideBuddylist, id=actionIDs.ShowBuddyList)
        bind(wx.EVT_MENU, self.OnMenubarPref, id=actionIDs.ShowMenuBar)
        bind(wx.EVT_MENU, self.OnStatusCustom, id=actionIDs.SetStatusCustom)

    def SetupStatusHandlers(self):
        for id in statuscombo.status_dict.values():
            wx.GetApp().Bind(wx.EVT_MENU, self.OnStatus, id=id)

    def OnMenubarPref(self, event):
        # called when the user checks the item
        prefs = profile.prefs
        thepref = 'buddylist.show_menubar'
        prefs[thepref] = not prefs[thepref]

    def OnStatus(self, event):
        status_dict = statuscombo.status_dict
        for status in status_dict:
            if status_dict[status] == event.GetId():
                import hooks; hooks.notify('digsby.statistics.ui.select_status')
                profile.set_status(status)

    def OnStatusCustom(self, event):
        statuscombo.edit_custom_status(None)

class BuddyListTaskBarIcon(AnimatedTaskBarIcon, BuddyListEventHandler):
    '''
    the main digsby tray icon
    '''

    def __init__(self, *args, **kwargs):
        AnimatedTaskBarIcon.__init__(self, id=hash('digsby_tray_icon'))
        BuddyListEventHandler.__init__(self)

        hooks.register('digsby.im.mystatuschange.async', lambda status: wx.CallAfter(self.on_status_change, status))
        hooks.register('digsby.im.message_hidden', self.on_hidden_message)

        # regenerate icon when the pref changes
        profile.prefs.link(TRAY_SHOW_STATUS_PREF, self.on_show_status_pref, callnow=True)

        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.OnShowHideBuddylist)
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN,  self.OnLeftClick)

        if config.platform == 'win':
            # refresh the tray icon image every couple of minutes to keep it
            # out of Window's inactive tray icon list
            self.refresh_timer = wx.PyTimer(self.Refresh)
            self.refresh_timer.Start(TASKBAR_REFRESH_MS, False)

    def on_hidden_message(self, hidden_conversations):
        assert wx.IsMainThread()
        self.set_hidden_messages(len(hidden_conversations))

    def OnLeftClick(self, e):
        e.Skip()

        # left click shows one hidden message, if there are any
        import gui.imwin.imhub as imhub
        if imhub.hidden_count():
            imhub.pop_all_hidden()
            self.set_hidden_messages(imhub.hidden_count())

    def OnShowHideBuddylist(self, e):
        buddy_frame = wx.GetApp().buddy_frame

        if not buddy_frame.Docked:
            return wx.GetApp().buddy_frame.toggle_show_hide()

        if buddy_frame.AutoHidden:
            buddy_frame.docker.ComeBack()
            buddy_frame.Raise()
        else:
            pass # do nothing if just docked

    def set_hidden_messages(self, n):
        '''
        n can be

         -1: show bubble with no count, and no flashing
          0: show just the digsby head
         >0: flash between digsby head and bubble with count, which is n
        '''

        status = profile.status
        digsby_head = self.status_tray_icon(status)

        if pref(UNREADPREF + 'flash_only_count', False):
            from gui import skin
            message_icon = skin.get('AppDefaults.TaskbarIcon')
        else:
            message_icon = None

        if n == -1:
            icons = [generate_hidden_message_icon(None)]
        elif n == 0:
            icons = [digsby_head]
        else:
            count = n if pref(UNREADPREF + 'show_count', True) else None
            unread_icon = generate_hidden_message_icon(count, message_icon)
            icons = [digsby_head, unread_icon]

        intervalms = pref(UNREADPREF + 'flash_interval_ms', default=1000)

        self.icons = [to_icon(i) for i in icons]
        self.delays = [intervalms] * len(self.icons)
        self.UpdateAnimation(status_tooltip(status))

    def on_show_status_pref(self, val):
        self.on_status_change(profile.status)

    def on_status_change(self, status):
        assert wx.IsMainThread()

        icon = self.status_tray_icon(status)
        tooltip = status_tooltip(status)

        self.icons[MAIN_ICON] = (icon)
        self.UpdateAnimation(tooltip)

    def status_tray_icon(self, status):
        if not self.show_status_orb:
            status = None
        elif status.available and not pref('trayicons.digsby.show_available_orb', default=False):
            # by default, don't show an available orb.
            status = None

        return to_icon(generate_tray_icon(status, self._IconSize))

    @property
    def show_status_orb(self):
        return pref(TRAY_SHOW_STATUS_PREF)

    def CreatePopupMenu(self):
        buddy_frame = wx.FindWindowByName('Buddy List')

        # TODO: fix skinned menus so that they don't need to be told they are in the system tray!
        umenu = UMenu(buddy_frame, onshow = None, windowless = True)

        add_hidden_convo_menu_items(umenu)

        statuscombo.add_global_to_menu(umenu, _('Set &Global Status...'))
        statmenu = UMenu(buddy_frame, onshow = None)#statuscombo.create_status_menu(add_custom = True)
        statuscombo.status_menu(statmenu, add_custom=True, add_promote = True)
        umenu.AddSubMenu(statmenu, _('Set IM &Status'))

        umenu.AddSep()

        show_hide   = umenu.AddItem(_('Show &Buddy List'), id=actionIDs.ShowBuddyList)
        if buddy_frame:
            docker = getattr(buddy_frame, 'docker', None)

            if docker:
                disable_hide = docker.Enabled and docker.docked and docker.AutoHide
                show_hide.label = _('Hide &Buddy List') if buddy_frame.Shown else _('Show &Buddy List')
                show_hide.Enable(not disable_hide)

        # The menubar is the "app" menubar on Mac and thus cannot be hidden.
        if platformName != 'mac':
            umenu.AddPrefCheck('buddylist.show_menubar', _('Show Menu Bar'))

        umenu.AddItem(_('&Preferences...'), id=wx.ID_PREFERENCES)

        # Mac gets this menu item standard on the Dock, don't duplicate it.
        if platformName != 'mac':
            umenu.AddSep()
            umenu.AddItem(_('E&xit Digsby'), id = wx.ID_EXIT)

        # since status items are created dynamically, we must bind to them on the fly.
        self.SetupStatusHandlers()

        return umenu

def status_tooltip(status_obj):
    'Returns the tooltip used in the main Digsby tray icon.'

    dev = ' DEV' if getattr(sys, 'DEV', False) else u' '

    if status_obj is None:
        status = u''
    else:
        status = u'- %s' % status_obj.nice_status

    tooltip = _('Digsby')
    tooltip += dev + status

    # add tooltip lines for each hidden message
    from gui.imwin import imhub
    if imhub.hidden_windows:
        elems = []
        for contact_infokey, messages in imhub.hidden_windows.items():
            contact = messages[0].buddy

            if config.platform != 'win' or vista:
                message_str = ngettext('{msgs} message', '{msgs} messages', len(messages)).format(msgs=len(messages))
            else:
                # xp cuts off longer tray icon tooltips
                message_str = '%d' % len(messages)

            elems.append(_('{alias} ({service}) - {message}').format(
                alias=contact.alias, service=contact.service, message=message_str))

        tooltip += '\n\n' + '\n'.join(elems)

    return tooltip


def generate_tray_icon(status, size):
    '''
    generates the Digsby tray icon. if status is not None, include a status
    orb badge.
    '''

    from gui import skin
    icon = skin.get('AppDefaults.TaskbarIcon')
    if status is None:
        return icon.PIL.ResizedSmaller(size)

    status_size = 8
    status_string = status.icon_status(status) if not profile.quiet else 'quiet'
    status_icon = skin.get('AppDefaults.TrayStatus.Icons.' + status_string)
    status_icon = status_icon.PIL.ResizedSmaller(status_size)

    from PIL import Image
    resized_icon = icon.PIL.ResizedSmaller(size).ResizeCanvas(size, size)

    i = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    i.paste(resized_icon, (0, 0))
    i.paste(status_icon, (size - status_size, size - status_size), status_icon)
    return i

from gui.taskbar import native_taskbar_icon_size

def generate_hidden_message_icon(nummessages, icon = None):
    from gui import skin

    if icon is None:
        icon = skin.get('AppDefaults.UnreadMessageIcon')

    size = native_taskbar_icon_size()
    icon = icon.PIL.ResizedSmaller(size).ResizeCanvas(size, size)

    if nummessages is not None:
        icon = draw_tiny_text(icon, str(nummessages))

    return icon

def stop_flashing():
    wx.GetApp().tbicon.set_hidden_messages(-1)

def add_hidden_convo_menu_items(menu):
    'populates a menu with items for hidden conversations'

    import gui.imwin.imhub as imhub
    if not imhub.hidden_windows:
        return

    for contact_infokey, messages in imhub.hidden_windows.items():
        contact = messages[0].buddy
        if contact is None:
            log.warning("Not adding hidden menu item, message object had None for .buddy: %r", messages[0])
        else:
            callback = lambda c=contact_infokey: imhub.pop_any_hidden(c)
            menu.AddItem(contact.alias,
                         callback=callback,
                         bitmap=contact.serviceicon)

    menu.AddItem(_('Show All'), callback=imhub.pop_all_hidden)
    #menu.AddItem(_('Dismiss All'), callback=stop_flashing)
    menu.AddSep()

