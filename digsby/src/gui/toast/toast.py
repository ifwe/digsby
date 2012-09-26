'''
Popup notification windows.

The Popup class looks for special optional keyword arguments to "fire" (see
common/notifications.py) which are passed to its constructor and control its
behavior:

    input    Must be a callable. If given, an input box at the bottom of the
             popup will be shown for entering text. On an enter keypress,
             the "input" callable will be called with two arguments:

             1) the input, a string
             2) a dictionary of all keyword arguments given to Popup's
                constructor

    pages    Must be a string. If given, the Popup expects another argument
             keyed by the value of this option. This other option must then
             be a sequence of objects which will be shown "paginated" and the
             user can flip through them with buttons shown at the bottom of
             the popup.

    onclick  Must be a callable.* If given, the mouse cursor will become a
             "hand" when over any area of the Popup that isn't a button or a
             text control. If this area is clicked, onclick will be called with
             the current "Item".

             *Can also be a string URL. If so, clicking the popup will launch the
             default browser with the given URL.

    onclose  Callable, called when the Popup disappears.

    position If given must be one of the following strings:

             'lowerright', 'upperright', 'upperleft', 'lowerleft'

             The Popup will show in the specified corner, regardless of the
             user's preferences.

'''
from __future__ import with_statement

import wx, sys, traceback
import hooks
from wx import Size, StockCursor, CURSOR_HAND, \
    CURSOR_DEFAULT, CallLater, Point, \
    BG_STYLE_CUSTOM, Bitmap
from wx import VERTICAL, HORIZONTAL, EXPAND, TOP, LEFT, RIGHT, BOTTOM, ALIGN_CENTER_VERTICAL
from wx import BoxSizer as wxBoxSizer, FindWindowAtPointer

from operator import attrgetter

from util.primitives.error_handling import try_this, traceguard
from util.primitives.funcs import Delegate
from util.primitives.mapping import Storage as S
from util.primitives.strings import curly

from gui import skin
from gui.textutil import default_font, TruncateText, VisualCharacterLimit
from gui.skin.skinobjects import Margins
from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.cleartext import ClearText as statictext
from gui.uberwidgets import UberWidget
from gui.toast import PopupStack
from cgui import BorderedFrame, fadeout

from gui.validators import LengthLimit

from common import pref, prefprop

from logging import getLogger; log = getLogger('popup'); info = log.info

log_debug = log.debug

position_map = dict(upperright = TOP    | RIGHT,
                    upperleft  = TOP    | LEFT,
                    lowerleft  = BOTTOM | LEFT,
                    lowerright = BOTTOM | RIGHT)

# how long it takes a popup to fade if the mouse is over it.
LONG_FADE_TIME_MS = 60 * 1000

def get_popups():
    'Returns a sequence of all visible popups.'

    popups = []
    append = popups.append

    for monitor in Popup.Stacks.values():
        for stack in monitor.values():
            for popup in stack:
                append(popup)

    return popups

def cancel_id(id):
    for popup in get_popups():
        if getattr(popup, 'popupid', sentinel) == id:
            with traceguard:
                popup.cancel()

    log.info('Cancelled all popups with id of %r', id)

def cancel_all():
    for popup in get_popups():
        popup.cancel()

def popup(**options):
    'Displays a Popup window using keyword args as options.'

    if sys.DEV:
        log.debug_s('Got popup request with options: %s', repr(options)[:80])

    initial_setup()

    if not options.get('always_show', False):
        import gui.native.helpers as helpers
        if not pref('notifications.enable_popup', True) or \
            (pref('fullscreen.disable_popups', default = True, type = bool) and
             helpers.FullscreenApp()):
            return

    transform_popup_options(options)

    # If options has a popupid and there is a showing popup with the same
    # id, then don't create a new one--call update_contents on it with
    # the new options instead.
    popupid = options.get('popupid', None)
    if popupid is not None:
        for p in get_popups():
            if p and p.popupid == popupid and not p.InputMode:
                p.update_contents(options)
                return p

    hooks.notify('popup.pre', options)
    p = Popup(None, options = options)

    if sys.DEV:
        log.debug_s('Displaying a popup that had options: %r', repr(options)[:80])

    p.Display()
    return p

# Disable on windows 2000 (where popups cause the GUI to freeze)
from config import platformName
if platformName == 'win':
    import platform
    if 'Windows-2000' in platform.platform() or platform.release() == '2000':

        # replace popup() function with a no-op
        globals().update(popup = lambda **options: None)
    PopupBase = BorderedFrame
else:
    PopupBase = wx.Frame
    PopupBase.GetAlpha = lambda s: 255

class PopupItem(object):
    'The data for one page of a popup.'

    _blacklist = ['header','major','minor','icon','buttons','input',
                  'onclick','page_noun','position','sticky','time',
                  'popupid','merge_onclick','contents', '_options']

    _copyattrs = ('header', 'major', 'minor', 'icon', 'buttons', 'input', 'onclick', 'target')

    def __repr__(self):
        return '<PopupItem %s>' % ' - '.join(repr(i) for i in (self.header, self.major, self.minor))

    def __init__(self, options):
        self._options = options

        get = options.get

        for attr in self._copyattrs:
            setattr(self, attr, get(attr, None))

        if 'pages' in options:
            self.page_noun = get('pages')[:-1]
            self._blacklist.append(self.page_noun)

            item = options[self.page_noun]
            setattr(self, self.page_noun, item)

            # icon may come from item
            if hasattr(item, 'icon'):
                setattr(self, 'icon', item.icon)
        else:
            self.page_noun = None

        self._apply_options()

    def get_icon(self, refresh_cb=None):
        if hasattr(self.icon, 'lazy_load'):
            try:
                return self.icon.lazy_load(refresh_cb)
            except Exception:
                traceback.print_exc()
                return None

        return self.icon

    def get_icon_badge(self):
        return getattr(self, 'icon_badge', None)

    def _apply_options(self, options=None, all=False):

        if options is not None:
            self._options = options

        for k, v in self._options.iteritems():
            if all or k not in self._blacklist:
                setattr(self, k, v)

    @property
    def _max_lines(self):
        return getattr(self, 'max_lines', self.pref_max_lines)

    pref_max_lines = prefprop('notifications.popups.max_lines', 2)

    @property
    def contents(self):
        if self.page_noun is None:
            return None
        else:
            return self._options.get(self.page_noun)

class PopupItemList(list):
    '''
    Holds the series of PopupItems shown by a popup with pages.
    '''

    paged_originally = False
    def __init__(self, options):
        if options is None:
            return

        if 'pages' in options and options['pages'] in options:
            self.paged_originally = True
            items = options[options['pages']]

            for item in items:
                new = options.copy()
                new[new['pages'][:-1]] = item

                self.append(PopupItem(new))
        else:
            self.append(PopupItem(options))

    def get_icon_and_preload_adjacent(self, n, refresh_cb=None):
        '''
        Retreives the icon for page n. Also makes a request for icons at pages
        n-1 and n+1, so that if they are lazy, they will hopefully be preloaded
        by the time the user flips to them.
        '''

        icon  = self[n].get_icon(refresh_cb)

        # preload next and previous icons when paging through items
        before = (n - 1) % len(self)
        after  = (n + 1) % len(self)
        for m in set([n, before, after]) - set([n]):
            self[m].get_icon(None)

        return icon


class PopupHoverMixin(object):

    def __init__(self):
        self._hover = None
        self._hover_check_enabled = True
        self._in_check_mouse = False
        self.hover_timer = wx.PyTimer(self.CheckMouse)

        self.Bind(wx.EVT_MOTION,       self.OnMotion)
        self.Bind(wx.EVT_ENTER_WINDOW, self.CheckMouse)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.CheckMouse)

    def OnMotion(self, e):
        e.Skip()
        self.Hover = True

    def CheckMouse(self, e = None):
        # strange thread stacks are showing that this method can recurse...
        # guard against that.
        if self._in_check_mouse or wx.IsDestroyed(self):
            return

        self._in_check_mouse = True
        try:
            if self._hover_check_enabled:
                win = FindWindowAtPointer()
                self.Hover = win is not None and (win.Top is self or getattr(win.Top, 'Parent', None) is self)
        finally:
            self._in_check_mouse = False

    def SetHover(self, val):
        if val == self._hover: return
        if wx.IsDestroyed(self): return
        if not self._hover_check_enabled: return

        if val:
            self.hover_timer.Start(200, False)
            self.OnEnter()
        else:
            self.hover_timer.Stop()
            self.OnLeave()

        self._hover = val

    def DisableHoverTracking(self):
        self._hover_check_enabled = False
        self.hover_timer.Stop()

    Hover = property(attrgetter('_hover'), SetHover)

class Popup(PopupBase, UberWidget, PopupHoverMixin):
    'Implements a popup notification window.'

    duration = prefprop('notifications.popups.duration', 4000)
    location = prefprop('notifications.popups.location', 'lowerright')
    monitor  = prefprop('notifications.popups.monitor',  1)

    added_hotkey = False
    last_input = None
    shared_hover = False  # used to keep all paged popups in view when mousing over one of them
    popup_icon_badge_size = 16

    def __init__(self, parent, options = None, skinkey = 'popup'):
        self.skinkey = skinkey
        self.UpdateSkin(first = True)
        if platformName == 'win':
            BorderedFrame.__init__(self, parent, self.Backgrounds.Normal, self.Backgrounds.Border,
                               self.margins, wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR | wx.FRAME_TOOL_WINDOW)
            self.ControlParent = self
        else:
            wx.Frame.__init__(self, parent, style=wx.FRAME_SHAPED | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR)
            self.ControlParent = wx.Panel(self, -1)
            self.alphaBorder = None

        self.ControlParent.ChildPaints = Delegate()
        self.OnClose = Delegate()

        # TODO: See if we need BG_STYLE_TRANSPARENT to work on GTK too
        if platformName == 'mac':
            self.SetBackgroundStyle(wx.BG_STYLE_TRANSPARENT)
        else:
            self.SetBackgroundStyle(BG_STYLE_CUSTOM)

        # Setup skinning options
        self._options = options
        get = self._options.get

        self.position      = get('position',      None)
        self.sticky        = get('sticky',        False)
        self.time          = get('time',          self.duration)
        self.popupid       = get('popupid',       None)
        self.merge_onclick = get('merge_onclick', True)

        self.current_page = 0
        self.page_items = PopupItemList(options)
        self.num_pages = len(self.page_items)

        self.has_focus = False

        self.construct()   # build common elements
        self.paginate()    # build page controls
        self.layout()      # layout controls in sizers
        self.size()        # size the overall window

        if self.Item.onclick:
            # use a hand cursor when the popup is clickable
            self.ControlParent.SetCursor(StockCursor(CURSOR_HAND))

        self.bind_events() # register event handlers

        self.fade_timer = wx.PyTimer(self.DoFade)
        self.long_fade_timer = wx.PyTimer(self.DoLongFade)

        PopupHoverMixin.__init__(self)
        self.CheckMouse()

        if not Popup.added_hotkey:
            # temporarily removed from release until we have keyboard shortcuts GUI
            if getattr(sys, 'DEV', False) and hasattr(wx.App, 'AddGlobalHotkey'):
                wx.GetApp().AddGlobalHotkey(((wx.MOD_CMD|wx.MOD_ALT), ord('q')), Popup.focus_next_popup_input)
                wx.GetApp().AddGlobalHotkey((wx.MOD_CMD| wx.MOD_ALT, wx.WXK_LEFT), lambda e: Popup.recent_popup_flip_page(-1))
                wx.GetApp().AddGlobalHotkey((wx.MOD_CMD| wx.MOD_ALT, wx.WXK_RIGHT), lambda e: Popup.recent_popup_flip_page(1))
            Popup.added_hotkey = True

        if not hasattr(Popup, 'shared_hover_timer'):
            Popup.shared_hover_timer = wx.PyTimer(Popup.on_shared_hover_timer)

    def OnEnter(self, e=None):
        self._did_enter = True
        self.fade_timer.Stop()

        if getattr(self, 'fade', None) is not None:
            self.fade.Stop(False)
            self.fade = None

        self.SetTransparent(self.opacity_hover)
        Popup.shared_hover = True
        Popup.shared_hover_timer.Start(500, False)

    def OnLeave(self):
        self.SetTransparent(self.opacity_normal)
        self.fade_timer.StartOneShot(self.time)

        if not getattr(self, '_did_enter', False): return

        self.stop_shared_hover()

    @classmethod
    def stop_shared_hover(cls):
        # Set shared hover flag to False, and start the fade timers of all
        # popups who stay visible because of it.
        notify = [p for p in get_popups() if p.SharedHover]
        cls.shared_hover = False
        for p in notify:
            p.fade_timer.Start()

    @classmethod
    def on_shared_hover_timer(cls):
        if not isinstance(getattr(wx.FindWindowAtPointer(), 'Top', None), cls):
            cls.shared_hover_timer.Stop()
            cls.stop_shared_hover()

    @property
    def opacity_normal(self):
        return opacity_to_byte(pref('notifications.popups.opacity.normal', default=100, type=int))

    @property
    def opacity_hover(self):
        return opacity_to_byte(pref('notifications.popups.opacity.hover', default=100, type=int))

    def DoFade(self, *e):
        '''
        Called by a timer when it might be time for this popup to fade away.
        '''

        if wx.IsDestroyed(self) or not self.ShouldFade or self.Hover:
            return

        self._FadeNow()

    def _FadeNow(self):
        if not wx.IsDestroyed(self) and getattr(self, 'fade', None) is None:
            self.fade = fadeout(self, self.GetAlpha(), 0, 8, self.HideAndDestroy)

    def DoLongFade(self):
        '''
        Called by a timer when it might be time for this popup to fade away,
        even if the mouse is over it.
        '''
        if not pref('notifications.popups.enable_long_fade', default = True, type = bool):
            return

        if self.has_focus or self.sticky:
            # has_focus is True when this popup has an input field that has
            # focus right now--we never want to fade away in that situation,
            # so just restart the timer.
            self.start_long_fade_timer()
        else:
            self._FadeNow()

    def start_long_fade_timer(self):
        '''
        Starts the timer that fades away the popup even when the mouse is over
        it.
        '''
        self.long_fade_timer.Start(LONG_FADE_TIME_MS, True)

    def reset_long_fade_timers(self):
        '''
        Resets all "long fade" timers for popups that have SharedHover == True,
        always including this one.
        '''
        for p in get_popups():
            if p.SharedHover:
                p.start_long_fade_timer()

        self.start_long_fade_timer()

    def Display(self):
        from common import profile

        if profile:
            self.Stack.Add(self)
        else:
            log.info('Not showing popup %r because profile is not available.', self)

    def cancel(self):
        if not wx.IsDestroyed(self):
            wx.CallAfter(self.HideAndDestroy)

    def UpdateSkin(self, first = False):
        root = s = self.skin = skin.get(self.skinkey)

        fonts, colors = s.fonts, s.fontcolors
        if hasattr(self, 'header_txt'):
            h, m, i = self.header_txt, getattr(self, 'major_txt', None), self.minor_txt

            h.Font          = fonts.title
            h.ForegroundColour = colors.title
            if m is not None:
                m.Font = fonts.major
                m.ForegroundColour = colors.major
            i.Font = fonts.minor
            i.ForegroundColour = colors.minor

        if hasattr(self, 'page_txt'):
            self.page_txt.SetFont(fonts.minor)
            self.page_txt.SetFontColor(colors.minor)

        buttonskin = self.skin.buttonskin

        self.padding = s.get('padding', lambda: Point())
        self.margins = s.get('margins', lambda: Margins())

        self.Backgrounds = S()
        self.Backgrounds.Border = root['background']

        marginskey = 'background_%sx%sx%sx%s' % tuple(self.margins)

        try:
            normal = root[marginskey]
        except KeyError:
            log.info('copying %r' % root['background'])
            normal = root[marginskey] = root['background'].copy(*self.margins)

        self.Backgrounds.Normal = normal

        if not first:
            for child in [c for c in self.ControlParent.Children
                          if isinstance(c, UberButton)]:
                child.SetSkinKey(buttonskin)

            self.layout()


    def bind_events(self):
        self.BBind(TIMER = self.DoFade)
        self.ControlParent.BBind(PAINT            = self.OnPaint,
                                 ERASE_BACKGROUND = lambda e: None,
                                 ENTER_WINDOW     = self.OnEnter,
                                 LEFT_DOWN        = self.OnClick,
                                 MIDDLE_UP        = self.OnRightClick,
                                 RIGHT_UP         = self.OnRightClick,
                                 MOTION           = self.OnMotion,
                                 MOUSEWHEEL       = self.OnMouseWheel,
                                 KEY_DOWN         = self.OnKeyDown,
                                 )

        if self is not self.ControlParent:
            self.Bind(wx.EVT_PAINT, self.OnBGPaint)

        if self.alphaBorder:
            # forward mouse wheel events from the border to the popup
            self.alphaBorder.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)

        for stext in (c for c in self.ControlParent.Children if isinstance(c, statictext)):
            stext.BBind(LEFT_DOWN      = self.OnClick,
                        MIDDLE_UP      = self.OnRightClick,
                        RIGHT_UP       = self.OnRightClick)

    def SetRect(self, rect):
        if self is self.ControlParent:
            BorderedFrame.SetRect(self, rect)
        else:
            self.bmp_rect = (rect.width, rect.height)
            bmp = self.Backgrounds.Normal.GetBitmap(self.bmp_rect)
            self.bmp_region = wx.RegionFromBitmap(bmp)
            self.SetShape(self.bmp_region)
            self.Move((rect.x, rect.y))

    def OnBGPaint(self, e):
        dc = wx.AutoBufferedPaintDC(e.EventObject)
        self.Backgrounds.Normal.Draw(dc, (0, 0, self.Rect.width, self.Rect.height))

    def OnKeyDown(self, e):
        if e.KeyCode == wx.WXK_ESCAPE and e.Modifiers == 0:
            self.HideAndDestroy()
        else:
            e.Skip()

    def OnMouseWheel(self, e = None):
        e.Skip()

        if self.InputShown: # do not flip pages during input mode
            return

        # TODO: Figure out this stupid API and make it nicer.
        import math
        wheel_rotation = e.WheelRotation
        pages = int(math.copysign(1, wheel_rotation))
        reverse = pref('notifications.popups.reverse_scroll', type=bool, default=True)
        self.flip_page((reverse and -1 or 1)*pages) # scrolling down progresses through pages, increasing the number

    def OnRightClick(self, e = None):
        self.MarkAsRead()

        # Fade out quickly, then call HideAndDestroy
        self._destroy_fade = fadeout(self, self.GetAlpha(), 0, 75, lambda: self.HideAndDestroy(userClose = True))

    def HideAndDestroy(self, e = None, userClose = False):
        '''Destroys the popup.'''

        if wx.IsDestroyed(self):
            return

        self.DisableHoverTracking()
        self.Hide()

        if userClose:
            userclose = self._options.get('onuserclose', None)
            if userclose is not None:
                with traceguard:
                    userclose()

        close = self._options.get('onclose', None)
        if close is not None:
            with traceguard:
                close()

        self.OnClose(userClose = userClose)
        self.fade_timer.Stop()
        self.long_fade_timer.Stop()

        # HACK: there are wx.CallAfter callbacks that occur after HideAndDestroy
        # that need access to page_items, so do this 1 second later.
        def delete_attrs():
            try:
                del self._options
            except AttributeError:
                pass
            try:
                del self.page_items
            except AttributeError:
                pass
        wx.CallLater(1000, delete_attrs)

        wx.CallAfter(self.Destroy)

    def OnMotion(self, e):
        e.Skip()

        self.reset_long_fade_timers()

        cursor = StockCursor(CURSOR_HAND if self.Item.onclick else CURSOR_DEFAULT)
        self.ControlParent.SetCursor(cursor)

    def RefreshIcon(self):
        if not wx.IsDestroyed(self):
            self.ControlParent.RefreshRect(self.IconRect)

    @property
    def IconRect(self):
        return (0,  0, self.skin.iconsize, self.skin.iconsize)

    def OnPaint(self, e):
        'Paints the popup.'

        dc = wx.AutoBufferedPaintDC(e.EventObject)

        if platformName == 'win':
            BorderedFrame.PaintBackground(self, dc)

        icon = self.icon
        if icon:
            # If the PopupItem has an icon, draw i.t
            iconsize = self.skin.iconsize
            if (icon.Width, icon.Height) != iconsize:
                icon = icon.PIL.Resized(iconsize).WXB
            dc.DrawBitmap(icon, 0, 0, True)

            # If the PopupItem has an icon_badge, draw it in the lower right hand corner.
            badge = self.icon_badge
            if badge:
                badge = badge.ResizedSmaller(self.skin.iconbadgesize)
                bsize = badge.Size

                dc.DrawBitmap(badge, iconsize - bsize.width, iconsize - bsize.height, True)

        self.draw_popup_badge(dc)
        self.ControlParent.ChildPaints(dc)

    @property
    def PopupBadge(self):
        return self.Item._options.get('badge', None)

    def draw_popup_badge(self, dc):
        popup_badge = self.PopupBadge
        if popup_badge is not None:
            popup_badge = popup_badge.PIL.Resized(self.popup_icon_badge_size).WXB
            r = self.ControlParent.ClientRect
            x, y = r.Right - self.popup_icon_badge_size, r.Top
            import config
            if config.platform == 'win':
                alpha = chr(140)
                dc.DrawBitmap(popup_badge, x, y, True, alpha)
            else:
                dc.DrawBitmap(popup_badge, x, y, True)

    def OnClick(self, e):
        # Hackishly avoid event mixups when clicking buttons.
        for child in [c for c in self.ControlParent.Children if isinstance(c, UberButton)]:
            if child.Rect.Contains(e.Position):
                return e.Skip()

        # shift click causes sticky. TODO: document and make visual indications for this.
        if wx.GetKeyState(wx.WXK_SHIFT):
            self.sticky = True
            return

        self.MarkAsRead()

        # an "onclick" key in the options dictionary should be a callback or a string URL
        onclick = getattr(self.Item, 'onclick', None)
        if onclick is None:
            return e.Skip()

        # Don't hide the popup if it has multiple pages
        should_hide = len(self.page_items) < 2 and not self.Item.buttons

        if should_hide:
            self.Hide()

        if not self.InputMode and hasattr(self, 'input'):
            # If we have an input box, but we're not in the temporary input mode,
            # it's value becomes the argument to the onclick handler.
            contents = self.input.Value
        else:
            # Otherwise it's just the active item.
            contents = self.Item.contents

        # This call later is the only way I found to ensure the popup is
        # hidden before a potentially long running callback (like spawning
        # Firefox) is finished.
        CallLater(30, handle_popup_onclick, onclick, contents)

        if should_hide:
            self.HideAndDestroy()

    @property
    def Item(self):
        return self.page_items[self.current_page]

    def MarkAsRead(self):
        item = self.Item
        mark_as_read = getattr(item, 'mark_as_read', None)
        if mark_as_read is not None:
            with traceguard:
                mark_as_read(item)

    @property
    def icon(self):
        icon = self.page_items.get_icon_and_preload_adjacent(self.current_page, self.RefreshIcon)

        if not isinstance(icon, Bitmap):
            return skin.get('BuddiesPanel.BuddyIcons.NoIcon').Resized(self.skin.iconsize)
        else:
            return icon

    @property
    def icon_badge(self):
        badge = self.page_items[self.current_page].get_icon_badge()
        if isinstance(badge, Bitmap):
            return badge

    @property
    def ShouldFade(self):
        return (not self.has_focus and
                not self.sticky and
                not self.SharedHover and
                not self.InputMode)

    @property
    def SharedHover(self):
        return len(self.page_items) > 1 and Popup.shared_hover

    def size(self, keep_pos = False):
        self.DesiredSize = Size(self.skin.width,
                                max(self.BestSize.height, self.skin.iconsize))

        if keep_pos: self.Stack.DoPositions(self) # keeps baseline at the same position
        else:        self.Stack.DoPositions()

    Stacks = {}

    @classmethod
    def focus_next_popup_input(cls, *a):
        'sets focus into the next popup input area'
        currentFocus = wx.Window.FindFocus()

        inputs = filter(None, (getattr(p, 'input', None) for p in get_popups()))
        if not inputs: return

        try:
            i = inputs.index(currentFocus)
        except ValueError:
            i = -1

        newFocus = inputs[(i + 1) % len(inputs)]
        newFocus.ReallyRaise()
        newFocus.SetFocus()

    @classmethod
    def recent_popup_flip_page(cls, delta):
        popups = get_popups()
        if popups:
            return popups[0].flip_page(delta)

    @property
    def Stack(self):
        monitor, position = self.monitor, self.ScreenPosition

        try:
            mon = Popup.Stacks[monitor]
        except KeyError:
            mon = Popup.Stacks[monitor] = {}

        try:
            stack = mon[position]
        except KeyError:

            if self.ControlParent is self:
                frameSize = self.margins
            else:
                frameSize = Margins()
            stack = mon[position] = PopupStack(monitor, position_map[position],
                                               border  = (frameSize.left, frameSize.top))

        return stack

    #
    # page methods
    #

    def paginate(self):
        self.construct_page_controls()
        self._update_page_controls()

    def _construct_button(self, label, callback=None, disables_buttons=False, enabled=True):
        def cb(*a, **k):
            val = callback(*a, **k)
            if disables_buttons:
                self.Item._buttons_disabled = True
                self.construct_buttons([], layout=True)
            return val

        button = UberButton(self.ControlParent, label=label, skin=self.skin.buttonskin, onclick=cb,
                          pos=(-20000, -20000))
        button.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
        if not enabled:
            button.Enable(False)
        return button

    def construct_page_controls(self):
        buttonskin = self.skin.buttonskin
        self.next_button = self._construct_button('>', lambda: self.flip_page(1))
        self.prev_button = self._construct_button('<', lambda: self.flip_page(-1))

        self.page_txt = statictext(self.ControlParent,'')#TODO: Not yet supported in ClearText: style = wx.ALIGN_CENTER_VERTICAL,

        self.page_txt.Font = self.skin.fonts.minor or default_font()
        self.page_txt.FontColor = self.skin.fontcolors.minor or wx.BLACK
        self.textctrls.append(self.page_txt)

    def flip_page(self, delta):
        self.reset_long_fade_timers()

        if self.num_pages == 0 and self.current_page != 0:
            self.current_page = 0
            self._update_page_controls()
            return

        self.MarkAsRead()
        old = self.current_page
        self.current_page += delta
        self.current_page %= self.num_pages

        #self.current_page = min(max(0, self.current_page), self.num_pages-1)
        if self.current_page != old:
            self._update_page_controls()
            self.MarkAsRead()

            if callable(self.Item.buttons):
                self.construct_buttons(self.Item.buttons, layout=True)

        self.size(keep_pos = True)


    def _update_page_controls(self):
        with self.FrozenQuick():
            self.update_for_page(self.current_page)
            self.update_page_buttons()

    def update_page_buttons(self):
        ctrls = (self.next_button, self.prev_button, self.page_txt)

        def update_spacers(show_buttons):
            if hasattr(self, 'button_spacer'):
                if show_buttons:
                    proportion = 0 if self.page_items.paged_originally else 1
                else:
                    proportion = 0

                self.button_spacer.SetProportion(proportion)
            if hasattr(self, 'prev_next_spacer'):
                self.prev_next_spacer.SetProportion(0 if show_buttons else 1)

        if self.num_pages == 1:
            # No pages? Don't show page buttons.
            for c in ctrls: c.Hide()
            update_spacers(True)
        else:
            pg = self.current_page
            self.page_txt.Label = '%d/%d' % (pg+1, self.num_pages)

            for c in ctrls: c.Show()
            update_spacers(False)

    def update_for_page(self, n):
        'Updates GUI elements for the nth page.'

        item = self.page_items[n]


        self.Header = curly(unicode(item.header or ''), source = item._options)
        #log.debug_s('Header %r curly\'d into %r (options were: %r)', item.header, self.Header, item._options)
        self.Major  = curly(unicode(item.major or ''),  source = item._options)
        #log.debug_s('Major %r curly\'d into %r (options were: %r)', item.major, self.Major, item._options)
        self.Minor  = curly(unicode(item.minor or ''),  source = item._options)
        #log.debug_s('Minor %r curly\'d into %r (options were: %r)', item.minor, self.Minor, item._options)

    def update_contents(self, options):
        method = options.get('update', 'append')
        self.sticky |= options.get('sticky', False)

        with self.FrozenQuick():
            getattr(self, 'update_contents_%s' % method, self.update_contents_unknown)(options)

        self.size(True)

        self.OnEnter()
        self.MaybeStartTimer()

    def MaybeStartTimer(self):
        if not self.Hover: self.fade_timer.StartOneShot(self.time)

    def update_contents_unknown(self, options):
        log.error('Got unknown update method (%s) in options %r for popup %r',
                  options.get('update', '<Key Missing>'), options, self)

    def update_contents_replace(self, options):
        self.Item._apply_options(options, all=True)
        self._update_page_controls()

    def update_contents_paged(self, options):
        self.page_items.extend(PopupItemList(options))
        self.num_pages  = len(self.page_items)
        self._update_page_controls()
        self.prev_button.Parent.Layout()

    def update_contents_append(self, options):
        major = options.get('major', None)
        minor = options.get('minor', None)

        # the "merge_onclick" option, if False, will cause any onclick callbacks
        # to no longer be in effect for this popup.
        merge_onclick = options.get('merge_onclick', True) and self.merge_onclick
        if not merge_onclick:
            self.Item.onclick = None

        log_debug('Updating contents of popup (appending)')
        log.debug_s('old header=%r, major=%r, minor=%r', self.Header, self.Major, self.Minor)

        with self.FrozenQuick():
            if major:

                height      = self.DesiredSize.height # this calls StaticText.Wrap

                if self.Minor.strip():
                    self.Minor += '\n'+'\n'.join(filter(None, [self.Major,curly(major, source=options)]))
                    self.Major  = ''
                else:
                    self.Major += '\n' + curly(major, source=options)

                self._adjust_label(self.major_txt, height)

            if minor:
                height      = self.DesiredSize.height # this calls StaticText.Wrap
                if self.Major.strip():
                    self.Major += '\n'+'\n'.join(filter(None, [self.Minor,curly(minor, source=options)]))
                    self.Minor  = ''
                else:
                    self.Minor += '\n' + curly(minor, source=options)

                self._adjust_label(self.minor_txt, height)


        log.debug_s('new header=%r, major=%r, minor=%r', self.Header, self.Major, self.Minor)

    def _adjust_label(self, ctrl, startheight):
        lines = ctrl.Label.split('\n')
        olen  = len(lines)
        lines = lines[-self.Item._max_lines:]

        if olen != len(lines):
            ctrl.Label = '\n'.join(lines)


    def construct(self):
        self.textctrls = []
        cp, fonts, colors = self.ControlParent, self.skin.fonts, self.skin.fontcolors

        self.header_txt = statictext(cp, '')
        self.header_txt.Font = fonts.title or default_font()
        self.header_txt.FontColor = colors.title or wx.BLACK

        self.major_txt  = statictext(cp, '')
        self.major_txt.Font = fonts.major or default_font()
        self.major_txt.FontColor = colors.major or wx.BLACK

        self.textctrls.append(self.major_txt)

        self.minor_txt  = statictext(cp,'')
        self.minor_txt.Font = fonts.minor or default_font()
        self.minor_txt.FontColor = colors.minor or wx.BLACK

        self.textctrls.extend([self.header_txt, self.minor_txt])

        self.construct_buttons(self.Item.buttons)
        self.construct_input(self.Item.input)

    def construct_input(self, callback,
            hide_on_enter=True,
            initial_value=u'',
            char_limit=None,
            spellcheck=False,
            spellcheck_regexes=None):

        if not callback:
            return

        style = wx.TE_PROCESS_ENTER | wx.BORDER_SIMPLE
        if char_limit is not None:
            style |= wx.TE_RICH2

        if spellcheck:
            from gui.spellchecktextctrlmixin import SpellCheckedTextCtrl
            input_clz = SpellCheckedTextCtrl
        else:
            input_clz = wx.TextCtrl

        input = self.input = input_clz(self.ControlParent, -1, initial_value, style = style, pos=(-20000, -20000),
                                       validator=LengthLimit(20480))

        if spellcheck and spellcheck_regexes is not None:
            for r in spellcheck_regexes:
                input.AddRegexIgnore(r)

        input.SetCursor(wx.StockCursor(wx.CURSOR_IBEAM))
        if hasattr(input, 'SetDefaultColors'):
            input.SetDefaultColors(wx.BLACK, wx.WHITE)

        def losefocus(e):
            self.has_focus = False
            self.fade_timer.StartRepeating(self.time)

        def onEnter(e):
            value, options = self.input.Value, self.Item._options

            # if we've got a character limit and there are too many characters
            # enter does nothing
            if char_limit is not None and len(value) > char_limit:
                return

            result = None
            with traceguard: result = callback(value, options)

            log.info('input callback is %r', result)

            if result is not None:
                input.ChangeValue('')
                self.update_contents(dict(update = 'append',
                                          minor = result))

                self.has_focus = False
                self.fade_timer.StartRepeating(self.time)
            elif hide_on_enter:
                self.HideAndDestroy()

        def onText(e):
            e.Skip()
            if e.String:
                self.has_focus = True
                self.OnEnter()

            # TODO: use this to keep text visible when deleting text
            # ctypes.windll.user32.SendMessageW(hwnd, EM_SETSCROLLPOS, 0, byref(pt))

        def onKeyDown(e):
            c = e.KeyCode
            if c == wx.WXK_ESCAPE:
                if self.InputMode:
                    self.leave_input_mode()
                else:
                    self.HideAndDestroy(userClose = True)
            elif c in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                onEnter(e)
            else:
                e.Skip()

        b = input.Bind
        b(wx.EVT_TEXT,       onText)
        b(wx.EVT_TEXT_ENTER, onEnter)
        b(wx.EVT_KEY_DOWN,   onKeyDown)
        b(wx.EVT_SET_FOCUS,  lambda e: (e.Skip(), setattr(self, 'has_focus', True)))
        b(wx.EVT_KILL_FOCUS, losefocus)

        # if there's a character limit, highlight text that is over the
        # limit with a red background
        if char_limit is not None:
            VisualCharacterLimit(input, char_limit)

    def _get_button_list(self, item, buttons):
        '''
        returns a sequence of (label, callback, enabled) describing buttons for the given popup item.

        "enabled" is optional and defaults to True.
        '''

        # buttons can be callable, or an ordered dict
        if getattr(item, '_buttons_disabled', False):
            buttons = []
        elif callable(buttons):
            try:
                buttons = buttons(item)
            except Exception:
                traceback.print_exc()
                buttons = []

        if hasattr(buttons, 'items'):
            buttons = buttons.items()

        return buttons

    def construct_buttons(self, buttons, layout=False):
        # If this is a popup with buttons, create them here.

        buttons = self._get_button_list(self.Item, buttons)

        # destroy old buttons, if we have them and they are different.
        if hasattr(self, 'buttons'):
            if self.buttons_data == buttons:
                return # just return if buttons are the same

            self._destroy_buttons()

        self.buttons = []
        self.buttons_data = buttons
        if not layout and not buttons: return

        #for label, callback in buttons:
        for tup in buttons:
            try:
                label, callback, enabled = tup
            except ValueError:
                label, callback = tup
                enabled = True

            # if the provided callback has a callable attribute "input_cb,"
            # then construct a text box and pass the resulting input to the
            # callback later
            input_cb = getattr(callback, 'input_cb', None)
            disables_buttons = False
            if hasattr(input_cb, '__call__'):
                # TODO: abstract this mess into a reusable class, or maybe a set
                # of hooks?
                def cb(cb = input_cb, callback=callback):
                    self.MarkAsRead()
                    get_value = getattr(callback, 'get_value', None)
                    if hasattr(get_value, '__call__'):
                        initial_value = get_value(self.Item._options)
                    else:
                        initial_value = u''
                    if hasattr(callback, 'spellcheck_regexes'):
                        regexes = callback.spellcheck_regexes()
                    else:
                        regexes = None
                    self.input_mode(cb,
                            getattr(callback, 'close_button', False),
                            initial_value,
                            getattr(callback, 'char_limit', None),
                            spellcheck = getattr(callback, 'spellcheck', False),
                            spellcheck_regexes = regexes)
            else:
                if not callable(callback):
                    label, callback = callback, lambda _label=label: getattr(self.Item.target, _label)()

                disables_buttons = getattr(callback, 'disables_buttons', False)
                def cb(cb = callback, disables_buttons=disables_buttons):
                    self.MarkAsRead()
                    if getattr(cb, 'takes_popup_control', False):
                        wx.CallAfter(cb, self.Item, self.Control)
                    elif getattr(cb, 'takes_popup_item', False):
                        wx.CallAfter(cb, self.Item)
                    else:
                        wx.CallAfter(cb)
                    if not disables_buttons and not getattr(cb, 'takes_popup_control', False):
                        self.HideAndDestroy()

            self.buttons.append(self._construct_button(label, cb, disables_buttons, enabled))

        if layout:
            self.LayoutButtons(self.buttons)

    @property
    def Control(self):
        try:
            return self._controller
        except AttributeError:
            self._controller = S(update_buttons=lambda: wx.CallAfter(self.refresh_buttons))
            return self._controller

    def refresh_buttons(self):
        self.construct_buttons(self.Item.buttons, layout=True)
        self.ControlParent.Layout()

    def _destroy_buttons(self):
        for button in self.buttons:
            self.button_sizer.Detach(button)
            button.Destroy()

    def layout(self):
        s = self.skin
        padding, iconsize = s.padding, s.iconsize

        # FIXME: This annoyance is brought to you by the people who make a TLW with a single child
        # expand that child to fill the TLW's space. We need to do this to allow for the margins.
        if self.ControlParent is not self:
            self.Sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.Sizer.Add(self.ControlParent, 1, wx.EXPAND | wx.ALL, 36)

        self.ControlParent.Sizer = marginsizer = wxBoxSizer(HORIZONTAL)

        self.main_sizer = sz = wxBoxSizer(VERTICAL)

        s = wxBoxSizer(HORIZONTAL)
        s.AddSpacer(iconsize)

        v = wxBoxSizer(VERTICAL)

        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        header_sizer.Add(self.header_txt, 1, EXPAND)
        header_sizer.AddSpacer((36, 1)) # for popup badge

        v.Add(header_sizer, 0, EXPAND | BOTTOM, padding.y)

        if hasattr(self, 'major_txt'):
            v.Add(self.major_txt,  0, EXPAND | BOTTOM, padding.y)
        v.Add(self.minor_txt,  0, EXPAND | BOTTOM, padding.y)
        s.Add(v, 1, wx.EXPAND)

        sz.Add(s, 1, EXPAND | LEFT, padding.x)

        self.button_sizer = wx.BoxSizer(HORIZONTAL)

        #if self.Item.buttons:
        # Build a horizontal sizer contaning each "action" button
        buttons = self.buttons
        button_sizer = self.button_sizer
        self.button_left_space = button_sizer.Add((self.skin.iconsize-padding.x, 1))
        self.button_spacer = button_sizer.AddStretchSpacer(1)
        self.button_index = 2
        self.under_buttons_space = sz.Add((0, padding.y))
        self.LayoutButtons(buttons, layoutNow=False)

        sz.Add(self.button_sizer, 0, EXPAND | LEFT, padding.x)

        self._page_buttons_position = len(sz.GetChildren())
        self.layout_prev_next()
        self.update_page_buttons()

        if hasattr(self, 'input'):
            sz.AddSpacer(padding.y)
            sz.Add(self.input, 0, EXPAND)

        marginsizer.Add(sz, 1, EXPAND)

        # FIXME: Way too much space is being allocated under Mac, this squeezes multi-page
        # controls but it's better than the alternative until we find a fix.
        if self.ControlParent is not self:
            self.Fit()

    def LayoutButtons(self, buttons, layoutNow=True):
        pad_x = self.skin.padding.x

        index = self.button_index

        for b in buttons:
            self.button_sizer.Insert(index, b, 0, EXPAND | LEFT, pad_x)
            index += 1

        self.under_buttons_space.Show(len(buttons) > 0)

        if layoutNow:
            self.button_sizer.Layout()

    def layout_prev_next(self):
        'Adds next and previous buttons, and "5/6" StaticText to a sizer.'

        xpadding = self.skin.padding.x

        h = self.button_sizer
        self.prev_next_spacer = h.AddStretchSpacer(1)
        # <
        h.Add(self.prev_button, 0, ALIGN_CENTER_VERTICAL | EXPAND | RIGHT, xpadding)

        # 5/6
        vv = wxBoxSizer(VERTICAL)
        vv.AddStretchSpacer(1)
        vv.Add(self.page_txt, 0, EXPAND)
        vv.AddStretchSpacer(1)

        h.Add(vv, 0, ALIGN_CENTER_VERTICAL | EXPAND)
        # >
        h.Add(self.next_button, 0, ALIGN_CENTER_VERTICAL | EXPAND | LEFT, xpadding)
        return h

    def ShowButtons(self, show):
        self.main_sizer.Show(self.button_sizer, show, True)

    @property
    def InputShown(self):
        '''returns True if this popup is showing an input text control.'''

        input = getattr(self, 'input', None)
        return input is not None and input.IsShown()

    @property
    def InputMode(self):
        '''returns True if the popup is in a temporary "input mode" state where
        the text ctrl will go away if the user clicks the X button'''

        return getattr(self, '_input_mode', False)

    def input_mode(self, cb, close_button, initial_value=u'', char_limit=None, spellcheck=False, spellcheck_regexes=None):
        with self.Frozen():
            self.ShowButtons(False)

            def on_close_input(*a):
                self._input_mode = False
                del self.leave_input_mode
                self.has_focus = False
                with self.Frozen():
                    self.main_sizer.Detach(self.input_sizer)
                    self.input_sizer.Detach(self.input)
                    if close_button:
                        self.input_sizer.Detach(self.close_input)
                        wx.CallAfter(self.close_input.Destroy)
                        del self.close_input
                    wx.CallAfter(self.input.Destroy)
                    del self.input
                    self.ShowButtons(True)
                    self.update_page_buttons()
                    self.Layout()

            self.leave_input_mode = on_close_input

            def callback(text, options):
                on_close_input()
                if getattr(cb, 'takes_popup_control', False):
                    wx.CallAfter(cb, self.Item, self.Control, text, options)
                elif getattr(cb, 'takes_popup_item', False):
                    wx.CallAfter(cb, self.Item, text, options)
                else:
                    wx.CallAfter(cb, text, options)

            # if initial_value is a tuple, assume (initial_value_string, cursor_position)
            if not isinstance(initial_value, basestring):
                initial_value, cursor_pos = initial_value
            else:
                cursor_pos = None

            assert isinstance(initial_value, basestring)
            assert cursor_pos is None or isinstance(cursor_pos, int)

            self._input_mode = True
            self.construct_input(callback, hide_on_enter=False, initial_value=initial_value,
                                 char_limit=char_limit, spellcheck=spellcheck,
                                 spellcheck_regexes=spellcheck_regexes)
            self.input.SetInsertionPoint(self.input.LastPosition if cursor_pos is None else cursor_pos)
            self.input.SetFocus()
            self.input_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.input_sizer.Add(self.input, 1, wx.EXPAND)
            if close_button:
                self.close_input = self._construct_button('X', on_close_input)
                self.input_sizer.Add(self.close_input, 0, wx.EXPAND)

            self.main_sizer.Add(self.input_sizer, 0, wx.EXPAND)
            self.Layout()

    def __repr__(self):
        return '<Popup %s>' % try_this(lambda: self.Header, id(self))

    #
    # wx properties
    #

    def SetHeader(self, header):
        header = TruncateText(header, self.HeaderWrapWidth, self.header_txt.Font)
        self.header_txt.Label = header
        self.header_txt.Show(bool(header))

    def GetHeader(self):
        return self.header_txt.Label

    def SetMajor(self, msg):
        t = self.major_txt
        t.Label = msg
        t.Wrap(self.WrapWidth, self.Item._max_lines)
        t.Show(bool(msg))

    def GetMajor(self):
        return self.major_txt.Label

    def SetMinor(self, msg):
        t = self.minor_txt
        t.Label = msg
        t.Wrap(self.WrapWidth, self.Item._max_lines)
        t.Show(bool(msg))

    def GetMinor(self):
        return self.minor_txt.Label

    def GetPaged(self):
        return bool(self.page_items)

    @property
    def WrapWidth(self):
        return self.skin.width - self.skin.iconsize - self.padding.x

    @property
    def HeaderWrapWidth(self):
        'Width to truncate header text at.'

        badge_padding = (self.popup_icon_badge_size - 2) if self.PopupBadge is not None else 0
        return self.WrapWidth - badge_padding

    @property
    def ScreenPosition(self):
        return self.position or self.location

    Header = property(GetHeader, SetHeader)
    Major = property(GetMajor, SetMajor)
    Minor = property(GetMinor, SetMinor)
    Paged = property(GetPaged)

def transform_popup_options(info):
    '''Do some preprocessing on incoming Popup args.'''

    from gui import skin
    icon = info.get('icon')

    if icon is None:
        # Look up buddy icons if there's 'buddy' but no 'icon'
        buddy = info.get('buddy')
        if buddy is not None:
            from gui.buddylist.renderers import get_buddy_icon

            # Also round their corners if the skin specifies it.
            round_size = try_this(lambda: int(skin.get('Popups.IconRounded', 2)), 2)
            info['icon'] = get_buddy_icon(buddy, size = skin.get('Popups.Iconsize', 32), round_size = round_size)

    elif isinstance(icon, basestring) and icon.startswith('skin:'):
        # If icon is specified as skin:dotted.path.to.skin.resource do the
        # lookup here
        with traceguard:
            info['icon'] = skin.get(icon[5:], None)

    if pref('notifications.popups.scan_urls', type = bool, default = False) and info.get('onclick', None) is None:
        from util import net
        url = None

        text = info.get('minor', None) or info.get('major', None) or info.get('header', None)
        links = net.find_links(text)
        if links and len(links) == 1:
            url = links[0]

        if url is not None:
            info['onclick'] = url

def opacity_to_byte(val):
    '''Map a number from 0-100 to 0-255, returning 255 if it's not a number.'''

    try:
        int(val)
    except ValueError:
        return 255
    else:
        return int(min(100, max(0, val)) / 100.0 * 255)

launch_browser = wx.LaunchDefaultBrowser

def handle_popup_onclick(onclick, contents):
    # onclick may be a string
    if isinstance(onclick, basestring) and onclick:
        launch_browser(onclick)
    else:
        # or a callable
        res = onclick(contents)

        # if the callable returns a string, interpret it as a URL
        if isinstance(res, basestring) and res:
            launch_browser(res)

_did_initial_setup = False

def initial_setup():
    global _did_initial_setup
    if _did_initial_setup:
        return

    _did_initial_setup = True

    # until problems with changing popup skins on the fly are resolved, cancel
    # all popups before a skin change.
    hooks.register('skin.set.pre', lambda skin, variant: cancel_all())

