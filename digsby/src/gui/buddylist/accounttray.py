'''
tray icons
'''
import config

import wx
from wx import Point
from gui.taskbar import DigsbyTaskBarIcon
import common.actions as actions
from common import pref
from gui.toolbox import draw_tiny_text, Monitor, GetDoubleClickTime

from util import try_this
import social
from traceback import print_exc
from operator import itemgetter
import common
import protocols
from gettext import ngettext


class ITrayIconProvider(protocols.Interface):
    'This is an intermediate interface, which should be superseded in the future'
    def tray_icon_class():
        '''
        returns a class that can be constructed with (acct, infobox) on Win
        and .initWithAccount(acct, infobox) on mac
        '''
        pass

class AccountTrayIconProvider(object):
    protocols.advise(instancesProvide=[ITrayIconProvider], asAdapterForTypes=[common.AccountBase])
    def __init__(self, subject):
        self.subject = subject

    def tray_icon_class(self):
        from common.emailaccount import EmailAccount
        from myspace.MyspaceAccount import MyspaceAccount as MySpace
        acct = self.subject
        if isinstance(acct, EmailAccount):
            return EmailTrayIcon
        elif isinstance(acct, MySpace):
            return MyspaceTrayIcon
        elif hasattr(acct, 'tray_icon_class'):
            return acct.tray_icon_class() #should this be on the Icon class?  can we set infobox at a later time and have the constructor be ok?
        elif isinstance(acct, social.network):
            return SocialAccountTrayIcon
        else:
            assert False, type(acct)

def should_grey(acct):
    "If this returns True, the account's tray icon will be greyed out when its count is zero."

    return not isinstance(acct, social.network)

baseAccountTrayClass = DigsbyTaskBarIcon
if config.platform == 'mac':
    from gui.native.mac import macmenuicon
    baseAccountTrayClass = macmenuicon.MenuBarIconDelegate

class AccountTrayIcon(baseAccountTrayClass):
    @classmethod
    def create(cls, acct, infobox):
        ###
        ### TODO: this is less awful, but still awful
        ###

        trayClass = ITrayIconProvider(acct).tray_icon_class()

        if config.platform == 'mac':
            object = trayClass.alloc().init()
            object.initWithAccount(acct, infobox)
            return object
        else:
            return trayClass(acct, infobox)

    def __init__(self, acct, infobox = None):

        # This method doesn't run for PyObjC icons (see initWithAccount instead), so it's okay
        # to put wx and Observable code in here.

        self.acct = acct
        self.infobox = infobox
        from gui.uberwidgets.umenu import UMenu
        self._menu = UMenu(wx.FindWindowByName('Buddy List'), onshow = self.update_menu)

        # generate unique tray icon IDs for each account that are persistent
        # across program runs (specifically, for Windows' tray icon hiding options)
        trayid = hash('accounttrayicon_' + acct.protocol + '_' + acct.name)

        super(AccountTrayIcon, self).__init__(acct.icon, menu = self._menu, id = trayid)

        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.on_click)
        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.on_double_click)

        self.register_observers(acct, self.on_account_updated)
        self.on_account_updated()

    def update_menu(self, event=None):
        self._menu.RemoveAllItems()
        actions.menu(wx.FindWindowByName('Buddy List'), self.acct, cls = type(self.acct), menu = self._menu)

    def on_click(self, e = None):
        try: dclick_timer = self.dclick_timer
        except AttributeError:
            dclick_timer = self.dclick_timer = wx.PyTimer(lambda: None)

        if dclick_timer.IsRunning():
            self.on_double_click()
            dclick_timer.Stop()
        else:
            dclick_timer.StartOneShot(GetDoubleClickTime())
            self.show_infobox()

        e.Skip()


    def on_double_click(self, e = None):
        if self.infobox.IsShown():
            self.infobox.Hide()

        url = self.acct.DefaultAction()

        if url is not None:
            wx.LaunchDefaultBrowser(url)

    def show_infobox(self):
        if not self.infobox: return

        info = self.infobox

        if info.IsShown() and getattr(info, 'account', None) is self.acct:
            info.Hide()
        else:
            pt = self.get_infobox_tray_position()
            info.ShowFromTray(pt, self.acct)
#            info.Show()

            # tell the infobox to gain focus, so the mousewheel works
            wx.CallAfter(info.do_focus)

    def get_infobox_tray_position(self):
        #TODO: find taskbar position from the correct HWND. this code assumes the mouse
        # is on the same display as the tray, and that the tray is on the bottom of the
        # "client area" rectangle returned by wxDisplay
        try:
            import cgui
            r = cgui.GetTrayRect()
            pt = Point(r.Right - r.Width / 2, r.Bottom - r.Height / 2)

            display = Monitor.GetFromPoint(pt, find_near = True)
            rect    = display.GetClientArea()
            distances = []

            for p in ('TopLeft', 'TopRight', 'BottomLeft', 'BottomRight'):
                corner = getattr(rect, p)
                distances.append((corner, corner.DistanceTo(pt), p))

            distances.sort(key = itemgetter(1))
            corner, distance, name = distances[0]
            return corner

        except Exception:
            print_exc()
            return Monitor.GetFromPointer().ClientArea.BottomRight

    def Destroy(self):
        self._destroyed = True

        if not config.platform == 'mac':
            self.unregister_observers(self.acct, self.on_account_updated)

        return super(AccountTrayIcon, self).Destroy()

    @property
    def count_string(self):
        acct = self.acct
        if acct.offline_reason != acct.Reasons.NONE:
            count = 'X'
        else:
            count = getattr(acct, 'count', 0)

        return count

    def on_account_updated(self, obj=None, attr=None, old=None, new=None):
        obj_or_event = obj
        if not self or getattr(self, '_destroyed', False):
            return

        acct  = self.acct
        count = self.count_string

        if acct.enabled:
            # todo: remove this lame way figure out icon size
            icon = acct.icon.PIL.Resized(self._IconSize)

            if self.should_show_count() and count:
                # place text in the corner
                icon = draw_tiny_text(icon, str(count)).WX

            if pref('trayicons.email.gray_on_empty', True) and count in (0, 'X') and should_grey(acct):
                icon = icon.WXB.Greyed

            self.SetIcon(icon, self.Tooltip)

    def should_show_count(self):
        return pref('trayicons.email.show_count', True)

    @property
    def Tooltip(self):
        return ''

class UpdateMixinAccountTrayIcon(AccountTrayIcon):
    def register_observers(self, acct, callback):
        acct.add_observer(callback, 'count', 'state')

    def unregister_observers(self, acct, callback):
        acct.remove_observer(callback, 'count', 'state')

class EmailTrayIcon(UpdateMixinAccountTrayIcon):
    def update_menu(self, event=None):
        from common.emailaccount import EmailAccount

        self._menu.RemoveAllItems()
        actions.menu(wx.FindWindowByName('Buddy List'), self.acct, cls = EmailAccount, search_bases = False,
                     menu = self._menu)


    @property
    def Tooltip(self):
        c = self.count_string
        if c == 'X':
            return _(u'{account.offline_reason} ({account.email_address})').format(account=self.acct)
        else:
            try:
                count = int(c)
            except ValueError:
                count = 0

            return ngettext(u'{count} unread message ({account.email_address})',
                            u'{count} unread messages ({account.email_address})', count).format(count=c, account=self.acct)


#
#TODO: maybe have the accounts "publish" which attributes to observe? this is dumb.
#
class SocialAccountTrayIcon(UpdateMixinAccountTrayIcon):
    @property
    def Tooltip(self):
        c = self.count_string
        if c == 'X':
            return _(u'{account.offline_reason} ({account.name})').format(account=self.acct)
        else:
            return try_this(lambda: ngettext(u'{count} new alert ({account.name})',
                                             u'{count} new alerts ({account.name})').format(count=c, account=self.acct), '')

class MyspaceTrayIcon(SocialAccountTrayIcon):
    def register_observers(self, acct, callback):
        SocialAccountTrayIcon.register_observers(self, acct, callback)
        acct.add_observer(callback, 'alerts')

    def unregister_observers(self, acct, callback):
        SocialAccountTrayIcon.unregister_observers(self, acct, callback)
        acct.remove_observer(callback, 'alerts')



