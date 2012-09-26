'''

the "Notifications" panel in Preferences

'''

USE_TREE_VIEW = False

import copy

import wx
from gui.pref.prefcontrols import *
from gui.controls import Button

from gui.uberwidgets.PrefPanel import PrefPanel,PrefCollection
from gui.notifications.notificationlist import NotifyPanel
from gui.toolbox import Monitor

from common import pref
from config import platformName

popupchoices = [
    ('lowerright', _('bottom right corner')),
    ('lowerleft',  _('bottom left corner')),
    ('upperright', _('top right corner')),
    ('upperleft',  _('top left corner')),
]

def panel(panel, sizer, newgroup, exithooks):
    display_choices = [(n, str(n+1)) for n in xrange(Monitor.GetCount())]

    dddict = {'{location_dropdown}' : ('notifications.popups.location', popupchoices),
              '{monitor_dropdown}'  : ('notifications.popups.monitor',  display_choices)}

    popup_panel = wx.Panel(panel)
    popup_sizer = popup_panel.Sizer = HSizer()

    popupposstr = _('Enable &pop-up notifications in the {location_dropdown} on monitor {monitor_dropdown}')

    pattern = re.compile('(.*?)(\{\w*\})(.*?)(\{\w*\})(.*)')

    m = pattern.search(popupposstr)
    startstr  = m.group(1)
    dd1       = m.group(2)
    middlestr = m.group(3)
    dd2       = m.group(4)
    endstr    = m.group(5)

    popup_sizer.Add(CheckChoice('notifications.enable_popup', dddict[dd1][0],
                    startstr, dddict[dd1][1])(popup_panel),
                    0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

    choice2 = Choice(dddict[dd2][0], dddict[dd2][1], caption = middlestr)(popup_panel)
    choice2.Enable(get_pref('notifications.enable_popup'))
    profile.prefs.add_observer(lambda *a: choice2.Enable(get_pref('notifications.enable_popup')),
                               'notifications.enable_popup',
                               obj = panel)
    popup_sizer.Add(choice2, 0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

    if endstr:
        popup_sizer.Add(Label(endstr)(popup_panel), 0, 3)



    top = PrefPanel(
        panel,
        PrefCollection(
            popup_panel,
            Check('enable_sound', _('Enable &sounds'))),
        _('Notifications'),
        prefix='notifications'
    )

    notifications_view = build_notification_area(panel)
    notifications_view.SetFocus()

    bottom = PrefPanel(panel, notifications_view,_('Events'))

    restore_default_button = Button(panel, _('Restore Defaults'),
                                    lambda: restore_default_notifications(notifications_view))
    if platformName == 'mac':
        restore_default_button.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)

    sizer.AddMany([
        (top,    0, wx.EXPAND | wx.ALL, 3),
        (bottom, 1, wx.EXPAND | wx.ALL, 3),
        (restore_default_button, 0, wx.BOTTOM | wx.LEFT, 4 if platformName == 'mac' else 0),
    ])

    return panel

def restore_default_notifications(ctrl):
    if wx.YES == wx.MessageBox(_('Are you sure you want to restore the default '
                                 'notification set?\n\nAll of your notification '
                                 'settings will be lost.'),
                                 _('Restore Default Notifications'),
                                 wx.ICON_EXCLAMATION | wx.YES_NO):

        import common.notifications as commnot
        nots = profile.notifications
        nots.clear()
        nots.update(copy.deepcopy(commnot.default_notifications))
        ctrl.Refresh()

def build_notification_area(parent):
    notification_viewer = pref('notifications.editor.view', type=str, default='simple')

    if notification_viewer == 'tree':
        # use the treelist view to edit notifications
        from gui.notificationview import NotificationView
        return NotificationView(parent, profile.notifications)
    else:
        # use a simple viewer with checkboxes for Popup and Sound
        from common.notifications import get_notification_info
        notifypanel = NotifyPanel(parent)
        n = notifypanel.NotifyView
        n.SetNotificationInfo(get_notification_info())
        n.SetUserNotifications(profile.notifications)
        n.UpdateSkin()
        return notifypanel

