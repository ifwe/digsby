'''

a simplified notification list editor

'''

from __future__ import with_statement

import wx
from wx import Rect, Point, ALIGN_CENTER_VERTICAL, Brush, \
    TRANSPARENT_PEN, WHITE_BRUSH, CONTROL_CHECKED
from operator import attrgetter
GetSysColor = wx.SystemSettings.GetColour

from gui import skin
from gui.skin.skinobjects import Margins
from gui.vlist.skinvlist import SkinVListBox
from gui.toolbox import AutoDC
from gui.anylists import bgcolors
from cgui import SimplePanel

from config import platformName
from logging import getLogger; log = getLogger('notificationlist')

_hdralign = wx.ALIGN_BOTTOM | wx.ALIGN_CENTER_HORIZONTAL

# values for positioning the header labels
W = 45
H = 20 if platformName != 'mac' else 15

class NotifyPanel(SimplePanel):
    def __init__(self, parent):
        SimplePanel.__init__(self, parent, wx.FULL_REPAINT_ON_RESIZE)

        s = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(s)

        self.list = NotifyView(self)

        s.AddSpacer((1, H))
        s.Add(self.list, 1, wx.EXPAND| wx.ALL & ~wx.TOP,1)

        self.Bind(wx.EVT_PAINT, self.__paint)

        f = self.Font
        f.SetWeight(wx.FONTWEIGHT_BOLD)
        if platformName == 'mac':
            f.SetPointSize(11)
        self.Font = f

        self.Bind(wx.EVT_MOUSEWHEEL, lambda e: self.SetFocus())

    def __paint(self, e):
        dc = AutoDC(self)
        dc.Font = self.Font
        rect = self.list.ClientRect

        if platformName != 'mac':
            dc.Pen   = TRANSPARENT_PEN
            dc.Brush = WHITE_BRUSH
            dc.DrawRectangle(0, 0, self.ClientRect.width, H)

        r1 = Rect( rect.Right - W * 2, rect.y, W, H )
        r2 = Rect( rect.Right - W, rect.y, W, H )
        r3 = Rect(*self.list.Rect)
        r3.Inflate(1,1)

        dc.DrawLabel(_('Sound'), r1, _hdralign)
        dc.DrawLabel(_('Popup'), r2, _hdralign)

        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetPen(wx.Pen(wx.Colour(213,213,213)))
        dc.DrawRectangleRect(r3)

    NotifyView = property(attrgetter('list'))

class NotifyView(SkinVListBox):

    def __init__(self, parent):
        SkinVListBox.__init__(self, parent)
        self.InitDefaults()
        self.BindEvents()

        self._hovered = -1

    def GetHovered(self):
        return self._hovered

    def SetHovered(self,i):
        n = self._hovered

        if i != n:
            self._hovered = i

            if n != -1:
                self.RefreshLine(n)
            if i != -1:
                self.RefreshLine(i)

    Hovered = property(GetHovered,SetHovered)

    def InitDefaults(self):
        self.IconSize     = 32
        self.margins      = Margins((3, 3))
        self.padding      = Point(5, 5)
        self.CheckBoxSize = 16

        self.SetNotificationInfo({})
        self.SetUserNotifications({})

        self.UpdateSkin()

    def BindEvents(self):
        Bind = self.Bind
        Bind(wx.EVT_LEFT_DOWN, self.__leftdown)
        Bind(wx.EVT_MOTION, self.OnMotion)


    def OnMotion(self,event):
        rect = wx.RectS(self.ClientSize)
        wap = wx.FindWindowAtPointer()
        mp = event.Position

        if not rect.Contains(mp) or wap != self:
            while self.HasCapture():
                self.ReleaseMouse()

            self.Hovered = -1
            return

        elif not self.HasCapture():
            self.CaptureMouse()

        self.Hovered = self.HitTest(mp)

    def OnDrawItem(self, dc, rect, n):

        # setup

        ninfo = self.NotificationInfo
        rect = rect.AddMargins(self.margins)

        key = ninfo._keys[n]
        topic, info = key, ninfo[key]

        title      = info['description']
        icon = None
        icon_topic = topic
        while icon is None:
            icon = self.icons.get(icon_topic, None)

            if '.' in icon_topic:
                icon_topic = icon_topic.split('.')[0]
            else:
                break

        if isinstance(icon, basestring):
            icon = skin.get(icon)
        iconsize   = self.IconSize
#        selected   = self.IsSelected(n)

        # draw

        dc.Font = self.Font
        dc.SetTextForeground(wx.BLACK)

        if icon is not None:
            dc.DrawBitmap(icon.Resized(iconsize), self.padding.x, rect.y)

        rect.Subtract(left = iconsize + self.padding.x * 2)

        dc.DrawLabel(title, rect, alignment = ALIGN_CENTER_VERTICAL)

        self.DrawChecks(dc, n, rect)

    def DrawChecks(self, dc, idx, rect):
        r = wx.RendererNative.Get()

        for i, cbrect in enumerate(self.CheckBoxRects(rect)):
            flags = CONTROL_CHECKED if self.Checked(idx, i) else 0
            r.DrawCheckBox(self, dc, cbrect, flags)

    def CheckBoxRects(self, rect):
        cbsize = self.CheckBoxSize

        num_checkboxes = 2
        rects = []

        y = rect.VCenterH(cbsize)

        for i in reversed(range(num_checkboxes)):
            r1 = Rect(rect.Right - W * (i+1), y, W, rect.height)
            r1.x, r1.y = r1.HCenterW(cbsize) + 4, r1.y
            r1.width = r1.height = cbsize
            rects.append(r1)

        return rects


    def Checked(self, idx, checkbox):
        reactions = self.UserNotifications.get(None, {}).get(self.TopicForIndex(idx), {})
        r = self.checkBoxReactions[checkbox]

        return any(r == d.get('reaction', None) for d in reactions)

    def CheckBoxHitTest(self, pos):
        rect = Rect(0, 0, self.ClientSize.width, self.OnMeasureItem(0))
        rect = rect.AddMargins(self.margins)

        for i, r in enumerate(self.CheckBoxRects(rect)):
            if r.Contains(pos):
                return i

        return -1 # not found

    def TopicForIndex(self, idx):
        return self.NotificationInfo._keys[idx]

    def OnDrawBackground(self, dc, rect, n):
        s = self.IsSelected(n)
        h = self.Hovered

        dc.Brush = Brush(GetSysColor(wx.SYS_COLOUR_HIGHLIGHT) if s else wx.Color(220, 220, 220) if h==n else bgcolors[n%len(bgcolors)])
        dc.Pen   = wx.TRANSPARENT_PEN
        dc.DrawRectangle(*rect)

    def OnMeasureItem(self, n):
        return self.margins.top + self.margins.bottom + self.IconSize

    def UpdateSkin(self):
        ICON_SKINPATH = 'AppDefaults.notificationicons'
        ni = self.NotificationInfo
        appdefaults = skin.get(ICON_SKINPATH)

        all_icons = {}
        for key in appdefaults.keys():
            all_icons[key] = skin.get(ICON_SKINPATH + '.' + key)

        for k in ni:
            iconpath = ni[k].get('notification_icon', None)
            if iconpath is not None:
                all_icons[k] = iconpath

        self.icons = all_icons
    #

    def __leftdown(self, e):
        p = e.Position
        i = self.HitTest(p)

        if i != -1:
            cb_i = self.CheckBoxHitTest(self.ToItemCoords(i, p))
            if cb_i != -1:
                return self.CheckBoxClicked(i, cb_i)

        #effectively disables selection
#        e.Skip()

    checkBoxReactions = [
        'Sound',
        'Popup',
    ]

    def CheckBoxClicked(self, item, checkbox):
        uinfo    = self.UserNotifications
        topic    = self.TopicForIndex(item)
        reaction = self.checkBoxReactions[checkbox]

        if not None in uinfo: uinfo[None] = {}
        reactions = uinfo[None].setdefault(topic, [])

        #
        # remove
        #
        foundOne = False
        for rdict in list(reactions):
            if rdict['reaction'] == reaction:
                foundOne = True
                log.info('removing %r', rdict)
                reactions.remove(rdict)
        #
        # add
        #
        if not foundOne:
            # adding one
            newEntry = self.ReactionEntry(topic, reaction)
            log.info('adding %r', newEntry)
            reactions.append(newEntry)

        import hooks
        hooks.notify('digsby.notifications.changed')

        self.RefreshLine(item)

    def ReactionEntry(self, topic, reaction):
        return {'reaction': reaction}

    def ToItemCoords(self, item, pos):
        return Point(pos.x, pos.y % self.OnMeasureItem(0))

    # NotificationInfo: the information in notificationview.yaml describing
    # possible notification topics

    def SetNotificationInfo(self, notification_info):
        ninfo = type(notification_info)()

        # Filter out items that have "gui: no"
        for key, value in notification_info.iteritems():
            if value.get('gui', True):
                ninfo[key] = value

        self._ninfo = ninfo
        self.SetItemCount(len(self._ninfo))

    def GetNotificationInfo(self):
        return self._ninfo

    NotificationInfo = property(GetNotificationInfo, SetNotificationInfo)

    # UserNotifications: the notifications blob stored in digsbyprofile

    def SetUserNotifications(self, usernots):
        self._usernots = usernots
        self.RefreshAll()

    def GetUserNotifications(self):
        return self._usernots

    UserNotifications = property(GetUserNotifications, SetUserNotifications)



def main():
    from common.notifications import get_notification_info
    from common.notifications import Popup

    userInfo = {None: {'contact.available': [{'reaction': Popup}],
        'contact.away': [{'reaction': Popup}],
        'email.new': [{'reaction': Popup}],
        'error': [{'reaction': Popup}],
        'facebook.alert': [{'reaction': Popup}],
        'filetransfer.request': [{'reaction': Popup}],
        'message.received.background': [{'reaction': Popup}],
        'myspace.alert': [{'reaction': Popup}]}}

    from tests.testapp import testapp
    app = testapp('../../..')

    f = wx.Frame(None, -1, 'notifications gui test')
    p = NotifyPanel(f)
    n = p.NotifyView

    n.NotificationInfo = get_notification_info()
    n.UserNotifications = userInfo

    f.Show()

    app.MainLoop()

if __name__ == '__main__':
    main()
