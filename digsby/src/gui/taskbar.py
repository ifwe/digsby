import wx
from gui.toolbox import to_icon
from logging import getLogger; log = getLogger('taskbar')
import config
from gui.animation import Animation

DEFAULT_TASKBAR_ID = 99

class TaskBarIconBase(wx.TaskBarIcon):
    def __init__(self, id = DEFAULT_TASKBAR_ID):
        try:
            # our windows build has a wxTaskBarIcon with an extra ID argument
            # so that Windows can track settings for them across program runs
            wx.TaskBarIcon.__init__(self, id)
        except TypeError:
            wx.TaskBarIcon.__init__(self)

        # FIXME: We need to use CreatePopupMenu on all platforms rather than handling RIGHT_UP,
        # but we can't do that until we have a mechanism for defining callbacks for it elsewhere.
        if config.platform != 'mac':
            self.Bind(wx.EVT_TASKBAR_RIGHT_UP, self.OnRightUp)

    @property
    def _IconSize(self):
        return native_taskbar_icon_size()

    def Destroy(self):
        if getattr(self, '_icon_destroyed', False):
            return log.critical('destroyed %r already. not destroying it again', self)

        log.info('Destroying %r', self)
        self._icon_destroyed = True
        wx.TaskBarIcon.Destroy(self)

    def OnRightUp(self, e):
        menu = self.CreatePopupMenu()
        if menu is not None:
            menu.PopupMenu()

    def CreatePopupMenu(self):
        return self.Menu

    def SetMenu(self, menu):
        self._menu = menu

        # fixes weird taskbar behavior with UMenu
        menu.Windowless = True

    def GetMenu(self):
        return getattr(self, '_menu', None)

    Menu = property(GetMenu, SetMenu)

    def Refresh(self):
        'Resets the icon...used to prevent Windows from hiding tray icons.'
        if not wx.IsDestroyed(self):
            self.SetIcon(self.GetIcon(), self._tooltip)


class AnimatedTaskBarIcon(TaskBarIconBase):
    def __init__(self, id = DEFAULT_TASKBAR_ID):
        TaskBarIconBase.__init__(self, id)

        self.icons = [None]
        self.delays = [1000]

        self.animation = Animation()
        self.animation.add_listener(self._update_tray)

        self._tooltip = ''

    def SetTooltip(self, tooltip):
        if tooltip != self._tooltip:
            self._tooltip = tooltip
            self._update_tray()

    def UpdateAnimation(self, tooltip = None):
        if tooltip is not None:
            assert isinstance(tooltip, basestring)
            self._tooltip = tooltip

        self.animation.set_frames(self.icons, self.delays)

    def _update_tray(self):
        if not wx.IsDestroyed(self):
            self._icon = self.animation.current_frame
            self.SetIcon(self._icon, self._tooltip)

    def GetIcon(self):
        return self._icon

class DigsbyTaskBarIcon(TaskBarIconBase):
    def __init__(self, icon, menu = None, tooltip = None, id = DEFAULT_TASKBAR_ID):
        TaskBarIconBase.__init__(self, id)

        if isinstance(icon, wx.WindowClass):
            raise TypeError

        self._tooltip = ''

        if icon is not None:
            self.SetIcon(icon, tooltip)

        if menu is not None:
            self.Menu = menu

    def SetIcon(self, icon_or_bitmap, tooltip = None):
        '''
        Sets an icon and tooltip for this tray item.

        If tooltip is None, the icon's tooltip will not be changed.
        '''

        size = self._IconSize

        #
        # use PIL to reduce aliasing (on MSW the tray icon size is often a lot smaller than
        # our source images)
        #
        # TODO: On mac, what is the best solution for the Dock?
        #
        self._icon = to_icon(icon_or_bitmap.PIL.ResizedSmaller(size).ResizeCanvas(size, size))

        if tooltip is None:
            tooltip = self._tooltip
        else:
            self._tooltip = tooltip

        wx.TaskBarIcon.SetIcon(self, self._icon, tooltip)

    def GetIcon(self):
        return self._icon

    Icon = property(GetIcon, SetIcon)


if config.platform == 'mac':
    def native_taskbar_icon_size():
        return 128
elif config.platform == 'gtk':
        #CAS: SMALLICON gave -1 on my system, ICON returns 32
        #32 looks like crap, 20 looked about right for my 24 pixel panel.
        #there's got to be a better way, considering there might not even be a tray,
        #and the height of these is shrunk to the height of the panel I have it on.
    def native_taskbar_icon_size():
        return 20
else:
    GetMetric = wx.SystemSettings.GetMetric
    def native_taskbar_icon_size():
        return GetMetric(wx.SYS_SMALLICON_X)

