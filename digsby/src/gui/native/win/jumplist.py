'''
builds the Jumplist -- the menu that appears when you right click the digsby Windows 7 Taskbar icon

the C++ implementation side is in ext/src/win/WinJumpList.cpp
'''
import cgui
import sys
import wx
import common
import traceback
from common import profile
from digsbyipcaction.funcs import funccall

from main import APP_ID

TOP_BUDDIES_ENABLED = False
SHOW_STATUS_ITEMS = True

#
# hooks
#
def buddylist_sorted(view):
    _update_jumplist()

def status_set(status):
    if SHOW_STATUS_ITEMS:
        _set_jumplist_now()

#
#

if getattr(sys, 'DEV', False):
    script = u'Digsby.py '
else:
    script = u''

def action(name, desc, label, icon=None):
    return (script + '--action=' + name, desc, label, icon)

def get_status(name, service):
    return profile.blist.get_status(name, service)

def buddy_item(buddy):
    # disabling icons for now--when users pin buddies, their status icons become
    # out of date.
    status_icon = None

    ipc_call = funccall('chat', idstr=buddy.idstr())

    name = unicode(buddy.alias)
    desc = _('Chat with {name}').format(name=name)

    return action(ipc_call, desc, name, status_icon)

def logging_enabled():
    if not getattr(logging_enabled, 'linked', False):
        logging_enabled.linked = True
        def on_log_ims_pref(val):
            _update_jumplist()

        common.profile.prefs.link('log.ims', on_log_ims_pref, callnow=False, obj=logging_enabled)
    return common.pref('log.ims')

MAX_BUDDIES_IN_LOGSIZE_LIST = 7

def _set_jumplist_now():
    'sets the jumplist immediately'

    popular_buddies = []

    if TOP_BUDDIES_ENABLED:
        try:
            popular_buddies = profile.blist.online_popular_buddies()
        except Exception:
            traceback.print_exc()

    set_app_jumplist(popular_buddies)

def _update_jumplist():
    '''
    updates the jumplist on a timer
    '''
    if not cgui.isWin7OrHigher():
        return
        
    def on_timer():
        _set_jumplist_now()

    @wx.CallAfter
    def after():
        try:
            t = buddylist_sorted.timer
        except AttributeError:
            t = buddylist_sorted.timer = wx.PyTimer(on_timer)
            on_timer()
        else:
            if not t.IsRunning():
                t.StartOneShot(6000)

def _status_icons_for_status(status):
    from gui import skin
    status_icons = dict.fromkeys(('available', 'away', 'invisible'), None)
    checked = skin.get('appdefaults.icons.taskbarcheck', None)
    if checked is not None:
        checked = checked.PIL.Resized(16).WXB

    if status.invisible:
        status_icons['invisible'] = checked
    elif status.away:
        status_icons['away'] = checked
    elif status.available:
        status_icons['available'] = checked

    return status_icons

def jumplist_status_items(current_status):
    '''
    returns a series of status jumplist items. the current status will have
    a check icon.
    '''
    status_icons = _status_icons_for_status(current_status)

    def status_action(name, label):
        tooltip = _('Change IM Status to {status}').format(status=label)
        ipc = funccall('status', status=name)
        return action(ipc, tooltip, label, status_icons[name])

    return [
        status_action('available', _('Available')),
        status_action('away',      _('Away')),
        status_action('invisible', _('Invisible')),
    ]

def set_app_jumplist(log_sizes=None):
    @wx.CallAfter
    def after():
        from gui import skin
        TASKS = [
            action('globalstatus', _('Set your status on multiple networks'), _('Set Global Status'), skin.get('icons.globalstatus', None)),
            action('newim',        _('Open the New IM window'),               _('New IM...'), skin.get('AppDefaults.UnreadMessageIcon', None)),
            action('prefsdialog',  _('Open the Digsby Preferences window'),   _('Preferences...')),
        ]

        if SHOW_STATUS_ITEMS:
            TASKS.append(None) # separator
            TASKS.extend(jumplist_status_items(profile.status))

        # Exit Digsby
        TASKS.append(None)
        TASKS.append(action('exit', _('Close all windows and exit'), _('Exit Digsby'), skin.get('AppDefaults.JumpListCloseIcon', None)))

        jumplist = [
            (u'', TASKS),
        ]

        if TOP_BUDDIES_ENABLED:
            logging = logging_enabled()

            if logging and log_sizes is not None:
                buddies = [buddy_item(buddy)
                           for buddy in log_sizes[:MAX_BUDDIES_IN_LOGSIZE_LIST]
                           if not buddy.__class__.__name__ == 'OfflineBuddy']
            else:
                buddies = [action(funccall('prefsdialog', tabname='text_conversations'), _('Opens the Preferences Window where you can enable logging'), _('Enable Chat Logs'))]

            jumplist.append((u'Top Buddies (by log size)', buddies))

        success = cgui.SetUpJumpList(APP_ID, jumplist)

        # clear jumplist on shutdown
        register_shutdown_hook()

_did_register_shutdown_hook = False
def register_shutdown_hook():
    global _did_register_shutdown_hook
    if _did_register_shutdown_hook: return
    _did_register_shutdown_hook = True

    wx.GetApp().PreShutdown.append(lambda: cgui.SetUpJumpList(APP_ID, []))

