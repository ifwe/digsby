'''
Popup positioning and animation.
'''


import wx
from wx import Point, RectPS, TOP, LEFT, BOTTOM, GetMousePosition

from gui.toolbox import Monitor, alignment_to_string
from gui.windowfx import move_smoothly
from cgui import fadein
from common import prefprop

from logging import getLogger; log = getLogger('popupstack')

def screenArea(monitor_n):
    display_n = min(Monitor.GetCount() - 1, monitor_n)
    return Monitor.All()[display_n].GetClientArea()

AVOID_MOUSE = False
AVOID_MOUSE_PIXELS = 30

valid_corners = frozenset((
    wx.TOP | wx.LEFT,
    wx.TOP | wx.RIGHT,
    wx.BOTTOM | wx.LEFT,
    wx.BOTTOM | wx.RIGHT
))

class PopupStack(list):
    'A popup stack is in charge of positioning popups for one corner of a display.'

    def __init__(self, monitor, position,
                 padding = None,
                 border  = None):

        self.monitor = monitor

        self.corner  = position
        assert position in valid_corners, position

        if padding is None:
            padding = (0, 10)
        if border is None:
            border = (10, 10)

        self.padding = Point(*padding)
        self.border  = Point(*border)

        self.NextRect     = self.Down if TOP & self.corner else self.Up
        self.OppositeRect = self.Up   if TOP & self.corner else self.Down

    def __repr__(self):
        return '<PopupStack %s monitor %d (%d popups)>' % (alignment_to_string(self.corner), self.monitor, len(self))

    @property
    def ScreenRect(self):
        return screenArea(self.monitor)

    offset = prefprop('notifications.popups.offset', (0,0))

    def Up(self, prevRect, newSize, user_action):
        border, padding = self.border, self.padding

        if prevRect is None:
            if LEFT & self.corner:
                pt = self.ScreenRect.BottomLeft  + (border.x + padding.x + self.offset[0], - border.y - self.offset[1])
            else:
                pt = self.ScreenRect.BottomRight - (newSize.width + border.x + padding.x + self.offset[0], border.y + self.offset[1])
        else:
            pt = prevRect.TopLeft - Point(0, border.y + padding.y)

        r = RectPS(pt - Point(0, newSize.height), newSize)
        if AVOID_MOUSE and not user_action and r.Contains(GetMousePosition()):
            r.y -= r.Bottom - GetMousePosition().y + AVOID_MOUSE_PIXELS

        return r

    def Down(self, prevRect, newSize, user_action):
        border, padding = self.border, self.padding

        if prevRect is None:
            if LEFT & self.corner:
                pt = self.ScreenRect.TopLeft + (border.x + padding.x + self.offset[0], border.y + self.offset[1])
            else:
                pt = self.ScreenRect.TopRight - (newSize.width + border.x + padding.x + self.offset[0], -border.y - self.offset[1])
        else:
            pt = prevRect.BottomLeft + Point(0, border.y + padding.y)

        r = RectPS(pt, newSize)

        if AVOID_MOUSE and not user_action and r.Contains(GetMousePosition()):
            r.y += GetMousePosition().y - r.y + AVOID_MOUSE_PIXELS

        return r

    def InitialPos(self, size):
        return self.NextRect(None, size).Position

    def Add(self, popup):
        assert popup not in self
        self.append(popup)
        popup.OnClose += lambda userClose: self.Remove(popup, user_action = userClose)
        self.DoPositions(popup)
        popup._infader = fadein(popup, 0, popup.opacity_normal, 30)

    def Remove(self, popup, user_action = False):
        try:
            self.remove(popup)
        except ValueError:
            pass
        self.DoPositions(user_action = user_action)

    def DoPositions(self, paging = None, user_action = False):
        prevRect = None

        for popup in self[:]:
            try:
                oldrect = popup.Rect
            except wx.PyDeadObjectError:
                self.remove(popup)
                log.critical('dead Popup object in %r' % self)
                continue

            quick   = False
            desired = popup.DesiredSize

            if popup.Hover or popup.has_focus:
                rect = RectPS(popup.Position, desired)

                # if the popup is in one of the bottom corners and it's
                # expanding, keep the bottom of its rectangle in the same
                # place since that's where the interactable GUI is
                if paging is popup and BOTTOM & self.corner:
                    rect.y -= rect.height - oldrect.height
            else:
                rect = self.NextRect(prevRect, desired, user_action = user_action)

            popup._moved = True

            self.SetPopupRect(popup, rect, quick = paging is popup)
            prevRect = rect

    slidetime = prefprop('notifications.popups.slide_ms', 140)

    def SetPopupRect(self, popup, rect, quick = False):
        t = int(self.slidetime)
        if t == 0: quick = True

        oldrect = popup.Rect

        if quick:
            popup.SetRect(rect)
        else:
            if oldrect.Size != rect.Size:
                popup.SetRect(wx.RectPS(oldrect.Position, rect.Size))

            move_smoothly(popup, rect.Position, time = t)
