'''
Mouseover popup for showing contact information on the buddylist.
'''
from __future__ import with_statement

from util.vec import vector
from util import linkify
from rpc.jsonrpc import JSPythonBridge
import logging

import config
import sys
import hooks
from wx import RectPS, RectS, Point, CallLater, \
    GetMouseState, FindWindowAtPointer, GetMousePosition, Size, PaintDC, AutoBufferedPaintDC, \
    BLACK, GREEN, WHITE, BLUE, RED_PEN #@UnresolvedImport

import warnings
from gui.browser.webkit import WebKitWindow
from gui.toolbox.scrolling import WheelScrollMixin, WheelShiftScrollFastMixin, WheelCtrlScrollFastMixin,\
    FrozenLoopScrollMixin
import wx.webview
from gui.capabilitiesbar import CapabilitiesBar
from contacts.Contact import Contact
from contacts.metacontacts import MetaContact
from common.emailaccount import EmailAccount
from social.network import SocialNetwork
import protocols
from .adapters import AccountCachingIBP, CachingIBP
from .interfaces import ICacheableInfoboxHTMLProvider, IInfoboxHTMLProvider, ICachingInfoboxHTMLProvider

def adapt_cache(obj):
    try:
        return CachingIBP(obj)
    except protocols.AdaptationFailure:
        return AccountCachingIBP(obj)

protocols.declareAdapterForType(ICachingInfoboxHTMLProvider, adapt_cache, SocialNetwork)

from gui import skin
from gui.skin.skinobjects import SkinColor, Margins
from gui.infobox.emailpanels import EmailList, Header
from common import pref, setpref, profile
from gui.buddylist import BuddyList
from gui.textutil import default_font
from util import Storage, Point2HTMLSize
from gui.infobox.errorpanel import ErrorPanel
from gui.windowfx import ApplySmokeAndMirrors #@UnresolvedImport
from common import prefprop
from gui.toolbox import Monitor, GetDoubleClickTime
from gui import imwin
from config import platform
import cgui
from common import protocolmeta
from time import time

from gui.windowfx import move_smoothly, resize_smoothly
from gui.infobox.htmlgeneration import GetInfo, LINK_CSS

from logging import getLogger; log = getLogger('infobox')

import traceback

DEFAULT_INFOBOX_WIDTH = 350
TRAY_TIMER_MS = 500

from threading import currentThread

class InfoboxWebkitWindow(FrozenLoopScrollMixin,
                          WheelShiftScrollFastMixin, WheelCtrlScrollFastMixin,
                          WheelScrollMixin, WebKitWindow):
    pass

class ExpandoPanel(wx.Panel):
    """
        These are the panels in the infobox that represent contacts of a
        metacontact
    """
    def __init__(self, parent, infobox):
        wx.Panel.__init__(self, parent, pos = (-300, -300))
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.SetMinSize(wx.Size(20, 20))

        self.infobox = infobox

        Bind = self.Bind
        Bind(wx.EVT_PAINT, self.OnPaint)
        Bind(wx.EVT_LEFT_UP, self.OnLUp)
        Bind(wx.EVT_LEFT_DCLICK, self.OnDClick)
        Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
        Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)

    def OnMouseEnter(self, event):
        """
            Makes sure the mouse is captured if the cursor is over the panel
        """
        if not self.HasCapture(): self.CaptureMouse()
        self.Refresh(False)

    def OnMouseLeave(self, event):
        "Ensure mouse is released when it has left the panel"

        self.ReleaseAllCapture()
        self.Refresh(False)

    def OnPaint(self, event):
        dc = AutoBufferedPaintDC(self)

        infobox = self.infobox
        contact = infobox.metacontact[infobox.expandopanels.index(self)]
        rect = RectS(self.Size)
        iconsize = 16
        padx = infobox.margins.left #+ infobox.margins.right

        i = 2 if infobox.account == contact else self.HasCapture()

        infobox.contactbg[i].Draw(dc, rect)

        dc.SetFont(infobox.headerfont)
        dc.SetTextForeground(infobox.contactfontcolor[i])

        name    = contact.alias
        servico = contact.serviceicon.Resized(iconsize)
        statico = skin.get("statusicons." + contact.status_orb).ResizedSmaller(iconsize)

        dc.DrawBitmap(servico, 2+padx, 2, True)
        dc.DrawText(name, 21+padx, 2) #18 + (16 - statico.Size.width)//2 -
        dc.DrawBitmap(statico, rect.width - (padx + (16-statico.Width)//2) - statico.Width, rect.height//2- statico.Height//2)


    def OnDClick(self, event):
        infobox = self.infobox
        contact = infobox.metacontact[infobox.expandopanels.index(self)]

        infobox.Hide()
        imwin.begin_conversation(contact)

    def OnLUp(self, event):
        "Set contact in infobox if clicked"

        infobox = self.infobox

        contact = infobox.metacontact[infobox.expandopanels.index(self)]

        if self.HasCapture() and not contact is infobox.account:
            infobox.SelectContact(contact)
            infobox.cpanel.Refresh(False)

class InfoBoxShowingTimer(wx.Timer):
    """
        Timer for delayed showing of the infobox
    """
    def __init__(self, infobox):
        self.infobox = infobox
        wx.Timer.__init__(self)

    def Start(self, contact):
        self.contact = contact
        wx.Timer.Start(self, pref('infobox.show_delay', 1000), True)

    def Notify(self):
        i = self.infobox
        if i is None or wx.IsDestroyed(i):
            print >>sys.stderr, 'Infobox is dead but still getting notified!'
            return
        if i.FriendlyTouch():
            i.ShowOnScreen()
            i.InfoSync()
            i.quickshow = True

class InfoBoxHidingTimer(wx.Timer):
    """
        Hides the infobox when the timer is up, disables other timers
    """
    def __init__(self, infobox):
        self.infobox = infobox
        wx.Timer.__init__(self)

    def Notify(self):
        i = self.infobox
        if i is None or wx.IsDestroyed(i):
            return

        i.mouseouttimer.Stop()
        i.showingtimer.Stop()
        i.quickshow = False
        i.Hide()

class InfoBoxTrayTimer(wx.Timer):
    "When summonned by the tray icon"

    def __init__(self, infobox):
        wx.Timer.__init__(self)
        self.infobox = infobox

    def Notify(self):
        try: mp = GetMousePosition()
        except Exception: return

        i = self.infobox
        if i is None or wx.IsDestroyed(i):
            return

        infobox_rect = i.Rect.Inflate(30, 30)

        if not infobox_rect.Contains(mp) and not cgui.GetTrayRect().Contains(mp):
            i.Hide()
            self.Stop()



class InfoBoxMouseOutTimer(wx.Timer):
    'This is used to detect when the mouse leaves the infobox.'

    def __init__(self, infobox):
        self.infobox=infobox
        wx.Timer.__init__(self)
        self.hider = InfoBoxHidingTimer(infobox)
        self.noneweredown = False

    def Start(self):
        wx.Timer.Start(self, 200)
        self.delayhide = False

    def Notify(self):
        try: mp = GetMousePosition()
        except: return

        ms          = GetMouseState()
        button_down = ms.LeftDown() or ms.RightDown() or ms.MiddleDown()

        infobox = self.infobox
        infobox_rect = infobox.Rect

        inside   = infobox_rect.Contains(mp)
        ftouch   = infobox.FriendlyTouch(mp)

        # Decide to delayhide or not, yes if mouse is inside the infobox
        # no if mouse is in a friendly
        if inside:   self.delayhide = True
        elif ftouch: self.delayhide = False

        # If mouse is not over any object that should keep the infobox open start hider
        hider = self.hider
        if not (inside or ftouch or infobox.capbar.cbar.overflowmenu.IsShown() or infobox.capbar.cto.menu.IsShown() or infobox.capbar.cfrom.menu.IsShown()) and self.noneweredown:
            # If a mouse button is down, close immediately
            if button_down:
                hider.Start(1, True)

            # otherwise with the delay specified in prefs
            if not hider.IsRunning():
                wap = wx.FindWindowAtPoint(mp)
                if wap is not None:
                    inancestor = infobox.Parent.Top is wap.Top and wap.Top is not wap
                else:
                    inancestor = False

                hider.Start(pref('infobox.hide_delay', 1000) if self.delayhide or inancestor else 1, True)

        # otherwise stop the hiding process if started
        else:
            self.noneweredown = False
            if hider.IsRunning():
                hider.Stop()

        self.noneweredown = not button_down


class InfoBox(wx.Frame):
    """
        A Box of Information
        ...
        Well, that didn't help much did it

        This is a window that displays information on whatever you're currently
        moused over on the buddy list.  It shows details on Contacts, MetaContacts
        Emails, and Social Networks.  It is also used for accounts on the
        system tray when clicked.
    """

    animation_time     = prefprop('infobox.animation.time', 200)
    animation_interval = prefprop('infobox.animation.interval', 10)
    animation_method   = prefprop('infobox.animation.method', 1)
    animate            = prefprop('infobox.animate', False)
    right_of_list      = prefprop('infobox.right_of_list', True)
    max_angle_of_entry = prefprop('infobox.max_angle_of_entry', 60)
    min_angle_of_entry = prefprop('infobox.min_angle_of_entry', 30)
    pause_time         = prefprop('infobox.pause_time', 250)
    width              = prefprop('infobox.width', DEFAULT_INFOBOX_WIDTH)

    def __dtor__(self):
        for attr in ('mouseouttimer', 'showingtimer', 'hidingtimer', 'traytimer'):
            obj = getattr(self, attr, None)
            if obj is not None:
                obj.infobox = None
                obj.Stop()

    def __init__(self, parent):
        style = wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP | wx.NO_BORDER

        # On Mac, FRAME_TOOL_WINDOW windows are not visible when the app is inactive.
        if config.platform == 'win':
            style |= wx.FRAME_TOOL_WINDOW

        wx.Frame.__init__(self, parent, -1, '', style = style )

        self.friends = set()

        #When displayed should the infobox fade in or be shown instantly
        self.quickshow=False

        #this is where the metacontacts stored if there is one
        self.metacontact=None
        #this is the Contact, EmailAccount, or SocialNetwork selected
        self.account          = None
        self._doubleclickhide = False

        #list of panels for MetaContact's Contacts
        self.expandopanels=[]

        #Various timers for the infobox's showing and hiding delays
        self.mouseouttimer = InfoBoxMouseOutTimer(self)
        self.showingtimer  = InfoBoxShowingTimer(self)
        self.hidingtimer   = None
        self.traytimer     = InfoBoxTrayTimer(self)

        self.timers = [self.mouseouttimer, self.showingtimer, self.hidingtimer]

        self.animationtimer = None

        self.htmlcacher = construct_html_cacher()

        #position left and position right options
        self.pl = wx.Point(0, 0)
        self.pr = wx.Point(0, 0)

        #Force to corner for systemtray usage
        self.fromTray=False
        self.shouldShow = False

        self.Show(False)

        panel = self.panel = wx.Panel(self, pos = (-400, -400))
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.UpdateSkin()

        self.content=wx.BoxSizer(wx.VERTICAL)

        #Margin stuff, replaceable with a margins object?
        sizer = panel.Sizer = wx.GridBagSizer()
        sizer.SetEmptyCellSize(wx.Size(0, 0))
        sizer.Add(self.content, (1, 1), flag = wx.EXPAND)
        sizer.Add(wx.Size(self.framesize.left, self.framesize.top), (0, 0))
        sizer.Add(wx.Size(self.framesize.right, self.framesize.bottom), (2, 2))
        sizer.AddGrowableCol(1, 1)
        sizer.AddGrowableRow(1, 1)

        # hook actions up to capabilities bar buttons
        caps = self.capbar = CapabilitiesBar(self.panel, lambda: self.account, True, True)

        # each of these buttons opens an IM window with the contact in the specified mode.
        for b in ('info', 'im', 'email', 'sms'):
            caps.GetButton(b).Bind(wx.EVT_BUTTON,
                lambda e, b=b: (self.Hide(), wx.CallAfter(self.account.imwin_mode, b)))

        def show_prefs_notifications():
            import gui.pref.prefsdialog
            gui.pref.prefsdialog.show('notifications')

        caps.OnSendFiles     += lambda *a: (self.Hide(), self.account.send_file())
        caps.OnSendFolder    += lambda *a: (self.Hide(), self.account.send_folder())
        caps.OnViewPastChats += lambda *a: (self.Hide(), self.account.view_past_chats())
        caps.OnAlert         += lambda *a: (self.Hide(), show_prefs_notifications())

#-------------------------------------------------------
#HAX: Do this right
        #CallAfter(caps.bmultichat.Show,False)
        wx.CallAfter(caps.ShowToFrom, False)
        wx.CallAfter(caps.ShowCapabilities, pref('infobox.showcapabilities', True))

#-----------------------------------------------------------

        self.content.Add(self.capbar, 0, wx.EXPAND)

        #add the email header
        self.eheader = Header(panel)
        self.content.Add(self.eheader, 0, wx.EXPAND)
        self.eheader.Show(False)

        #add the content panel
        self.cpanel = wx.Panel(panel)
        #self.cpanel.SetBackgroundColour(wx.WHITE)
        self.cpanel.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.cpanel.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.content.Add(self.cpanel, 1, wx.EXPAND)

        #add the email list
        self.elist = EmailList(panel)
        self.content.Add(self.elist, 1, wx.EXPAND)
        self.elist.Show(False)

        #add the error panel
        self.errorpanel = ErrorPanel(panel)
        self.content.Add(self.errorpanel, 1, wx.EXPAND)
        self.errorpanel.Show(False)

        panel.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        panel.Bind(wx.EVT_PAINT, self.OnPaint)
        panel.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        panel.SetSize(wx.Size(DEFAULT_INFOBOX_WIDTH, DEFAULT_INFOBOX_WIDTH))

        #add profile box
        self.profilebox = self.construct_webview()
        self.account_webviews  = {None: self.profilebox}
        self.account_jsbridges = {None: JSPythonBridge(self.profilebox)}

        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self.Bind(wx.EVT_CLOSE, self.__onclose)

        wx.CallAfter(self.DoSizeMagic)

    def OnKeyDown(self, e):
        # hack Ctrl+C to copy
        if e.KeyCode == ord('C') and e.GetModifiers() == wx.MOD_CMD:
            self.profilebox.Copy()
        else:
            e.Skip()

    def construct_webview(self):
        webview = InfoboxWebkitWindow(self.cpanel, style=wx.WANTS_CHARS) # WANTS_CHARS means webkit will receive arrow keys, enter, etc
        webview.hosted = False

        # HACK: see HACK note in main.on_proxy_info_changed
        from main import set_did_create_webview
        set_did_create_webview()

        self.setup_webview(webview)
        self.cpanel.Sizer.Add(webview, 1, wx.EXPAND)
        return webview

    def setup_webview(self, webview):
        b = webview.Bind
        b(wx.EVT_KEY_DOWN, self.OnKeyDown)
        b(wx.webview.EVT_WEBVIEW_BEFORE_LOAD, self.OnBeforeLoad)
        b(wx.webview.EVT_WEBVIEW_LOAD, self.OnHTMLLoad)
        b(wx.EVT_MOUSEWHEEL, self.on_mousewheel)

        from gui.browser.webkit import setup_webview_logging
        jslog = getLogger('infobox_js')
        import gui.skin
        setup_webview_logging(webview, jslog, logbasedir=gui.skin.resourcedir())

    def __onclose(self, e):
        # alt+f4 should just hide the infobox, not destroy it
        self.Hide()

    def _on_destroy(self, e):
        e.Skip()
        if e.EventObject is self:
            for t in self.timers:
                t.Stop()

    def on_mousewheel(self, e):
#        e.Skip()

        # hack to forward mouse events to the email list
        if self.elist.IsShown():
            return self.elist.OnMouseWheel(e)
        elif self.profilebox.IsShown():
            return self.profilebox._on_mousewheel(e)

    def do_focus(self):
        for ctrl in (self.profilebox, self.elist, self.cpanel):
            if ctrl.IsShown():
                self.ReallyRaise()
                ctrl.SetFocusFromKbd()
                break

    def UpdateSkin(self):
        s = skin.get
#        self.border  = 3
        self.framesize = s('infobox.framesize', lambda: Margins([0, 0, 0, 0]))
        self.padding = s('infobox.padding', lambda: Point(2, 2))
        self.margins = wx.Rect(*s('infobox.margins', lambda: [4, 4, 4, 4]))

        self.headerfont = s('infobox.fonts.header', default_font)
        self.headerfc   = s('infobox.fontcolors.header', BLACK)
        self.headerhoverfc = s('infobox.fontcolors.contacthover', BLACK)
        self.headerselfc = s('infobox.fontcolors.contactselected', BLACK)

        titlefont  = skin.get('infobox.fonts.title', default_font)
        majorfont  = skin.get('infobox.fonts.major', default_font)
        minorfont  = skin.get('infobox.fonts.minor', default_font)
        linkfont   = skin.get('infobox.fonts.link',  default_font)


        h = self.htmlfonts = Storage()

#-------------------------------------------------------------------------------
#       Code for TagFont function
#----------------------------------------
        h.header   = self.headerfont
        h.title    = titlefont
        h.major    = majorfont
        h.minor    = minorfont
        h.link     = linkfont

        h.headerfont = self.headerfont.FaceName
        h.titlefont  = titlefont.FaceName
        h.majorfont  = majorfont.FaceName
        h.minorfont  = minorfont.FaceName
        h.linkfont   = linkfont.FaceName

        h.headersize = Point2HTMLSize(self.headerfont.PointSize)
        h.titlesize  = Point2HTMLSize(titlefont.PointSize)
        h.majorsize  = Point2HTMLSize(majorfont.PointSize)
        h.minorsize  = Point2HTMLSize(minorfont.PointSize)
        h.linksize   = Point2HTMLSize(linkfont.PointSize)

        h.headerfc = self.headerfc.GetAsString(wx.C2S_HTML_SYNTAX)
        h.titlefc  = s('infobox.fontcolors.title', BLACK).GetAsString(wx.C2S_HTML_SYNTAX)
        h.majorfc  = s('infobox.fontcolors.major', BLACK).GetAsString(wx.C2S_HTML_SYNTAX)
        h.minorfc  = s('infobox.fontcolors.minor', lambda: wx.Color(128, 128, 128)).GetAsString(wx.C2S_HTML_SYNTAX)
        h.linkfc   = s('infobox.fontcolors.link', BLUE).GetAsString(wx.C2S_HTML_SYNTAX)
#-------------------------------------------------------------------------------

        self.bg        = s('infobox.frame', lambda: SkinColor(BLACK))

        self.barskin   = s('capabilitiesbar', None)

        self.contactbg = [s('infobox.backgrounds.contact', lambda: SkinColor(wx.Colour(128, 128, 128))),
                          s('infobox.backgrounds.contacthover', lambda: SkinColor(GREEN)),
                          s('infobox.backgrounds.contactselected', lambda: SkinColor(WHITE))]

        self.contactfontcolor=[s('infobox.fontcolors.contact', BLACK),
                               s('infobox.fontcolors.contacthover', BLACK),
                               s('infobox.fontcolors.contactselected', BLACK)]
        s = self.panel.Sizer
        if s:
            s.Detach(1)
            s.Detach(1)
            s.Add(wx.Size(self.framesize.left, self.framesize.top), (0, 0))
            s.Add(wx.Size(self.framesize.right, self.framesize.bottom), (2, 2))
        if hasattr(self, 'capbar') and hasattr(self, 'cpanel'):
            sizer = self.content
            sizer.Detach(self.capbar)
            sizer.Detach(self.cpanel)
            sizer.Add(self.capbar, 0, wx.EXPAND)
            sizer.Add(self.cpanel, 1, wx.EXPAND)

        self.htmlcacher.clear()

    def OnPaint(self, event):
        self.bg.Draw(PaintDC(self.panel), RectS(self.panel.Size))

    def OnHTMLLoad(self, e):
        e.Skip()
        if e.GetState() == wx.webview.WEBVIEW_LOAD_ONLOAD_HANDLED:
            if not self.should_use_maxheight:
                wx.CallAfter(self.DoSizeMagic)

    def DoSizeMagic(self):
        "Determines the size for the infobox, based on what's shown."

        self.last_do_size_magic = time()
        width = self.width

        # How much space is filled by panels if shown
        filled = sum(panel.Size.height for panel in self.expandopanels)

        # How much space is filled by the capabilities bar if shown
        if self.capbar.Shown:
            filled += self.capbar.Size.height

        # How much space is filled by the header if shown
        if self.eheader.Shown:
            filled += self.eheader.Size.height

        # calculate the max height in pixels based off of the percent max height of the screen from prefs
        # TODO: this isn't correct when the infobox isn't shown from the tray (#3568)
        maxheight = Monitor.GetFromWindow(wx.FindWindowByName('Buddy List')).ClientArea.height * pref('infobox.ratio_to_screen', 0.75) #@UndefinedVariable
        use_maxheight = self.should_use_maxheight

        # Get the desired height of the dynamically sized object displayed
        if self.elist.Shown:
            content = self.elist
            desired = content.GetFullHeight()
        elif self.cpanel.Shown:
            content = self.profilebox

            if use_maxheight:
                desired = maxheight
                #this really should be json.dumps, but it's only an int.
                js = "try {setInfoboxDesiredHeight(%d);} catch (err){}" % desired
                content.RunScript(js)
            else:
                js = "document.getElementById('content').clientHeight;"
                desired = content.RunScript(js)
                if desired in (None, ''):
                    log.error("No HTML element with ID 'content' in infobox")
                    return
                desired = int(desired) + self.margins.top + self.margins.bottom #+ 2*self.padding.y

            js = 'document.body.style.overflow = "auto"'
            content.RunScript(js)


        else:
            content = self.errorpanel
            desired = content.MinSize.height

        # determine the height the infobox is actually going to be
        if self.should_use_maxheight:
            # some accounts just always take 75%
            allotted = maxheight
        else:
            allotted = min(desired + filled, maxheight)

        # sets the content size to be less that the alloted size but not enough to show partial items
        contentsize = content.SkimIt(allotted-filled) if isinstance(content, EmailList) and allotted == maxheight else allotted - filled
        content.SetMinSize(wx.Size(width, contentsize))

        sz = Size(width + self.framesize.left + self.framesize.right,
                  contentsize + filled + self.framesize.top + self.framesize.bottom)

        # animate or just set the infobox to the new size
        if getattr(self, '_resizingto', None) != sz and pref('infobox.animation.resizing', False):
            resize_smoothly(self, sz)
            self._resizingto = sz
        else:
            if not self.fromTray:
                self.Size = sz

        self.panel.SetSize(sz)
        wx.CallAfter(self.panel.Layout)
        wx.CallAfter(self.cpanel.Layout)

        if hasattr(self, 'bg') and isinstance(self.bg, cgui.SplitImage4):
            ApplySmokeAndMirrors(self, self.bg.GetBitmap(sz))
        else:
            ApplySmokeAndMirrors(self)

        if self.fromTray:
            self.RepositionTray(sz)

    def DelayedHide(self):
        """
            This starts a cancelable timer that will close the infobox in
            1 second if not interupted
        """
        if not self.hidingtimer:
            self.hidingtimer = CallLater(1000, self.DoDelayedHide)

    def DoDelayedHide(self):
        """
            Second half of a delayed hide, called by the timer when it's up.
            Hides the infobox if the mouse isn't on the rect
        """
        self.hidingtimer = None

        if not self.Rect.Contains(GetMousePosition()):
            self.Hide()

    def Hide(self):
        """
            Hides the infobox immediately, stopping the hiding and showing timers
            if running
        """

        if self.hidingtimer:
            self.hidingtimer.Stop()
            self.hidingtimer = None

        if self.showingtimer.IsRunning():
            self.showingtimer.Stop()

        if self.traytimer.IsRunning():
            self.traytimer.Stop()

        self.Show(False)
        self.infobox_app_hiding()

    def DoubleclickHide(self):
        'A special temporary hide for one buddy.'

        self._doubleclickhide = True
        self.Hide()

    def InvalidateDoubleclickHide(self):
        'Invalidate any special hide requested by "ActivatedHide"'

        self._doubleclickhide = False

    def DrawCrap(self, c1, c2, mp):
        """
            Code used for debugging, left in because it's kinda cool
            draws lines from the mouse pointer to the coreners of the infobox.
            Happens when the pref infobox.tracelines is true
        """

        from math import tan, radians

        DX=abs(c1.x-mp.x)
        LA = self.min_angle_of_entry
        HA = self.max_angle_of_entry

#                print 'DX',DX

#                print 'min and max angles',LA,HA

        minDY=int(abs(tan(radians(LA))*DX))
        maxDY=int(abs(tan(radians(HA))*DX))

#                print 'min and max dy',minDY,maxDY

#                print 'delta y c1 and c2',abs(c1.y-mp.y),abs(c2.y-mp.y)

        DY1=min(max(abs(c1.y-mp.y), minDY), maxDY)
        DY2=min(max(abs(c2.y-mp.y), minDY), maxDY)

#                print 'delta ys',DY1,DY2

        AP1 = Point(c1.x, mp.y-DY1)
        AP2 = Point(c1.x, mp.y+DY2)

        sdc=wx.ScreenDC()
        sdc.SetBrush(wx.Brush(wx.Color(0, 255, 0, 125)))
        sdc.SetPen(wx.Pen(wx.Color(0, 0, 255, 255)))

        sdc.DrawPolygon((AP1, AP2, mp))

        sdc.Pen=RED_PEN
        sdc.DrawLinePoint(mp, c1)
#                sdc.Pen=wx.GREEN_PEN
        sdc.DrawLinePoint(mp, c2)
#                sdc.Pen=wx.BLACK_DASHED_PEN
#                sdc.DrawLinePoint(mp,(c1.x,(c2.y-c1.y)//2+c1.y))
#                sdc.Pen=wx.Pen(wx.ColorRGB((0,0,255)))
#                sdc.DrawLinePoint(lp,mp)

    def StateChanged(self, *a):
        wx.CallAfter(self._StateChanged, *a)

    def _StateChanged(self, *a):
        """
            This is the callback for when the state changes in the current
            account for EmailAccounts and Social Networks
        """

        did_infosync = False
        account = self.account

        # determine if the account is online and what type of account it is
        online   = account.state in (account.Statuses.ONLINE, account.Statuses.CHECKING)

        # remove an account specific webview if it has one, and the account is offline
        if not online and account is not None:
            self.remove_webview(account)

        issocnet = isinstance(account, SocialNetwork)
        isemail  = isinstance(account, EmailAccount)

        #capbar is only shown on contact based accounts
        self.capbar.Show(False)

        #the content panel is shown by online SocialNetworks
        self.cpanel.Show(issocnet and online)
        #Header is shown, regardless of state
        self.eheader.SetAccount(account)
        self.eheader.Show(True)

        #if the account is an online EmailAccount, then the list is shown
        if isemail and online:
            self.elist.SetAccount(account)
        else:
            self.elist.Show(False)

        if issocnet and online and account.dirty:
            #____log.info('InfoSync due to state changed in %s, active account is %s', obj, account)
            self.InfoSync()
            did_infosync = True

        # If the account is not online, it tries to get a reason message
        # if there is not one, just is Offline, or None if online
        active = account.state == account.Statuses.OFFLINE and account.offline_reason == account.Reasons.WILL_RECONNECT
        if active:
            message = lambda: profile.account_manager.state_desc(account)
        else:
            message = profile.account_manager.state_desc(account) or 'Offline' if not online else None

        error_link = account.error_link()
        if error_link is None:
            # If failed to get a link, just set the panel to the message
            # Hides itself if the message is None
            self.errorpanel.Error(message)
        else:
            link, cb = error_link
            self.errorpanel.Error(message, link, cb)

        return did_infosync

    @property
    def BuddyListItem(self):
        return self.metacontact if self.metacontact else self.account

    def SelectNext(self):
        mc = self.metacontact
        if mc:
            i = mc.index(self.account) + 1
            l = len(mc)
            if i >= l:
                i -= l
            self.SelectContact(mc[i])


        for panel in self.expandopanels:
            panel.Refresh()

    def SelectLast(self):
        mc = self.metacontact
        if mc:
            i = mc.index(self.account) - 1
            self.SelectContact(mc[i])


        for panel in self.expandopanels:
            panel.Refresh()

    def MetaContactObserver(self, obj, attr, old, new):
        wx.CallAfter(self._MetaContactObserver, obj, attr, old, new)

    def _MetaContactObserver(self, obj, attr, old, new):
        if wx.IsDestroyed(self):
            warnings.warn('Infobox is dead but is still getting notified from MetaContactOberver')
            return

        if not self.account in self.metacontact or not self.Shown:
            try:
                self.account = self.metacontact.first_online
            except AttributeError:

                err = ''.join(['The obj: '            , str(obj),
                               '\nThe attr: '         , attr,
                               '\nold -> new: '       , str(old), '->', str(new),
                               '\n\nThe Metacontact: ', str(self.metacontact)])
                log.error(err)

        self.Repanelmater()
        self.Reposition()


    def ContactObserver(self, obj, attr, old, new):
        wx.CallAfter(self._ContactObserver, obj, attr, old, new)

    def _ContactObserver(self, obj, attr, old, new):
        #____log.info('InfoSyncing on contact, ContactObserver called with (%s, %s, %s, %s)', old, attr,  obj, new)
        self.InfoSync()

        for panel in self.expandopanels:
            panel.Refresh()

    def Display(self, pl, pr, caller, force_change=False):
        '''
            Show the infobox

            pl: point left
            pr: point right
            caller: contact, metacontact, or account
        '''

        if self.fromTray:
            self.Hide()
            self.fromTray = False

        #stop the hiding timer if going
        self.hidingtimer, ht = None, getattr(self, 'hidingtimer', None)
        if ht is not None:
            ht.Stop()

        if self._doubleclickhide and caller is self.BuddyListItem:
            # _doubleclickhide is true after a doubleclick--don't show for that buddy
            return

        # if the position options are new or the caller isn't the same
        if not (pl == self.pl and pr == self.pr and (caller is self.metacontact or caller is self.account)):

            self.pausedover, po_timer = None, getattr(self, 'pausedover', None)
            if po_timer is not None:
                po_timer.Stop()

            mp     = GetMousePosition()
            rect   = self.Rect
            onleft = rect.x < mp.x

            #If infobox is shown and not set to be forced
            if self.Shown and not (force_change):

                #figure out the delta of mouse movement
                lp = getattr(self, 'LastMousePoint', mp)
                dp = mp - lp

                lmd = getattr(self, 'LastMouseDirection', [False, False])
                d   = self.LastMouseDirection = ((dp.x > 0 if dp.x else lmd[0]),
                                                 (dp.y > 0 if dp.y else lmd[1]))
                c1 = rect.Position
                c2 = c1 + wx.Point(0, rect.height)
                if onleft:
                    c1.x += rect.width
                    c2.x += rect.width

                #See DrawCrap
                if pref('infobox.tracelines', False): self.DrawCrap(c1, c2, mp)

                #if there is a delta on the x axis
                if d[0] ^ onleft:
                    #this block of code determines the angle of mouse movment to
                    #   determine if the user is moving the mouse to the infobox or away
                    c = c2 if d[1] else c1
                    am = (vector(*lp) - vector(*mp)).angle
                    ac = max(min((vector(*lp) - vector(*c)).angle, self.max_angle_of_entry), self.min_angle_of_entry)
                    if am < ac and mp.y > c1.y and mp.y < c2.y:
                        self.LastMousePoint = mp + ((1, 0) if onleft else (-1, 0))
                        self.pausedover = CallLater(self.pause_time, lambda *__: (self.Display(pl, pr, caller, force_change=True) if self.FriendlyTouch(mp) else None))
                        return

            #Saves mouse position for reference next time
            self.LastMousePoint = mp + wx.Point(*((1, 0) if onleft else (-1, 0)))

            #sets the left and right positions
            self.pl = pl
            self.pr = pr

            self.InfoConnect(caller)


            self.Reposition()

        elif not self.Shown:
            self.StartShow()

        if self.panel.IsFrozen():
            self.panel.Thaw()

    def ShowFromTray(self, pt, account):
        self.fromTray = True
        if not self.Shown:
            self.shouldShow = True


        self.hidingtimer, ht = None, getattr(self, 'hidingtimer', None)
        if ht is not None:
            ht.Stop()

        self.pr = self.pl = pt
        self.InfoConnect(account)

    def RepositionTray(self, size):
        pos = self.pr - Point(*size) + Point(1, 1)
        r   = wx.RectPS(wx.Point(*pos), wx.Size(*size))
        screenrect = Monitor.GetFromRect(r).ClientArea

        # on windows, when the task bar is autohidden, it isn't automatically
        # subtracted from ClientArea for us--so do it manually
        if platform == 'win':
            get_autohide = getattr(cgui, 'GetTaskBarAutoHide', None)
            if get_autohide is not None and get_autohide():
                region = wx.Region(screenrect)
                if region.SubtractRect(cgui.GetTaskbarRect()):
                    screenrect = region.GetBox()

        pos = screenrect.Clamp(r, wx.ALL).Position

        if self.animationtimer:
            self.animationtimer.stop()
            self.animationtimer = None

        self.SetRect(wx.RectPS(pos, size))
        self.traytimer.Start(TRAY_TIMER_MS)
        self._moving_to = pos

        if not self.Shown and self.shouldShow:
            self.shouldShow = False
            self.ShowOnScreen()

    def InfoConnect(self, account):
        #if the last account was an EmailAccount or SocialNetworks
        #   clear the errorpanel and disconnect the observers

        last_dosize = getattr(self, 'last_do_size_magic', 0)

        if isinstance(self.account, SocialNetwork):
            self.errorpanel.Error()
            self.account.unobserve_count(self.InfoSync)
            self.account.remove_observer(self.StateChanged, 'state')

        elif isinstance(self.account, EmailAccount):
            self.errorpanel.Error()
            self.account.remove_observer(self.StateChanged, 'state')
        elif isinstance(self.account, Contact):
            if self.metacontact:
                # remove any previous list observer
                mco, self.metacontact_observer = getattr(self, 'metacontact_observer', None), None
                if mco is not None:
                    mco.disconnect()
                else:
                    log.warning("unobserving a MetaContact, but didn't have a metacontact_observer")
            else:
                self.account.remove_observer(self.ContactObserver, 'status', 'status_message', 'idle', 'icon')

        try:
            self._unbound_cbs.clear()
        except AttributeError:
            pass


        did_infosync = False
        showing_feed = False

        #if the account type is a contact or metacontact
        if isinstance(account, (Contact, MetaContact)):
            self.eheader.Show(False)
            self.elist.Show(False)
            self.capbar.Show(True)
            self.cpanel.Show(True)

            #set appropriate values for metacontact and selected contact
            if isinstance(account, (MetaContact)):
                metacontact = account
                contact = account.first_online
            else:
                metacontact = []
                contact = account


            #if infobox is not shown or is a different metacontact or contact than last time
            if not self.IsShown() or metacontact != self.metacontact or (contact is not self.account and ((contact is not metacontact.first_online) if metacontact else True)):
                #set the account to the contact and set the metacontact
                self.metacontact = metacontact
                self.account = contact

            if metacontact:
                self.metacontact_observer = metacontact.add_list_observer(self.MetaContactObserver,self.ContactObserver, 'status', 'status_message', 'idle', 'icon') #TODO: resource for jabber
            else:
                contact.add_observer(self.ContactObserver, 'status', 'status_message', 'idle', 'icon')

            # if there is an account selcted
            if self.account is not None:
                # set up block/unblock command in the dropdown
                caps = self.capbar
                if isinstance(self.account, MetaContact):
                    buddies = self.account
                    name = buddies.alias
                else:
                    buddies = [self.account]
                    name = self.account.name

                if any(b.blocked for b in buddies):
                    content = _('Unblock %s')
                else:
                    content = _('Block %s')

                caps.iblock.content = [content % name]

        # if the account is a EmailAccount set the account and state observer
        elif isinstance(account, EmailAccount):
            showing_feed = True
            self.metacontact  = []
            self.account      = account

            self.account.add_observer(self.StateChanged, 'state')
            self._StateChanged()

        # if the account is a SocialNetwork set the account and state observer
        elif isinstance(account, SocialNetwork):
            showing_feed = True
            self.metacontact  = []
            self.account      = account
            self.account.observe_count(self.InfoSync)
            self.account.add_observer(self.StateChanged, 'state')
            did_infosync = self._StateChanged()

        if showing_feed: self.maybe_notify_stats()

        self.Repanelmater(not did_infosync)

        if last_dosize == getattr(self, 'last_do_size_magic', -1):
            # if our calls to InfoSync did not result in a DoSizeMagic, then do it now
            self.DoSizeMagic()

    def notify_stats(self):
        self.maybe_notify_twitter()
        hooks.notify('digsby.statistics.infobox.shown', self.account)
        self.showed_with_contact = False

    def maybe_notify_twitter(self):
        '''
        use a timer to only notify the twitter infobox stat AFTER it has been open
        for more than the double click time, so that we don't count double clicks
        opening the main feed window.
        '''
        if getattr(self.account, 'protocol', None) != 'twitter':
            return

        def later():
            if self.IsShown():
                hooks.notify('digsby.statistics.twitter.infobox.shown')

        try:
            timer = self._dclick_timer
        except AttributeError:
            timer = self._dclick_timer = wx.PyTimer(later)
        else:
            timer.StartOneShot(GetDoubleClickTime())

    def maybe_notify_stats(self):
        # If the infobox was originally Shown with a Contact, but is now
        # switching to a social network or email account.,
        if self.IsShown() and getattr(self, 'showed_with_contact', False):
            self.notify_stats()

    def ShowOnScreen(self):
        '''
        Shows the infobox.

        (Includes some special code to keep the infobox on top of other windows.)
        '''

        if self.ShowNoActivate(True):
            if not isinstance(self.account, Contact):
                self.notify_stats()
            else:
                self.showed_with_contact = True

        if config.platform == 'win':
            show_on_top(self) # make sure the infobox is always on top

    def OnSize(self, event):
        'Runs Repostion and refreshes if the infobox gets resized.'

        event.Skip()

        if self.pl and self.pr and not self.fromTray:
            self.Reposition()

        self.Refresh()

    def Reposition(self):
        """
            Moves the infobox, and decides how to do it
        """
        pl = self.pl
        pr = self.pr
        size = self.Size


        #decide which is first pl or pr, and set p1 and p2 aproprietly
        #   if the info box fits at p1, more it there, otherwise p2

        primaryPoint  = pr if self.right_of_list else (pl[0] - self.Size.width, pl[1])
        primaryRect = RectPS(wx.Point(*primaryPoint), wx.Size(*size))
        secondaryPoint  = (pl[0] - size.width, pl[1]) if self.right_of_list else pr

        screenrect = Monitor.GetFromWindow(self.Parent.Top).ClientArea #@UndefinedVariable
        offscreen  = (primaryRect.right > screenrect.right) if self.right_of_list else (primaryRect.left < screenrect.left)

        pos = secondaryPoint if offscreen else primaryPoint

        direction = wx.TOP|wx.BOTTOM

        r   = wx.RectPS(wx.Point(*pos), wx.Size(*size))
        screenrect = Monitor.GetFromRect(r).ClientArea #@UndefinedVariable
        pos = screenrect.Clamp(r, direction).Position
        #decide to animate or move to new position
        if self.animate and self.Shown and pos.x == self.Position.x:
            if self.animation_method == 2:
                if getattr(self, '_moving_to', None) != pos:
                    self.animationtimer = move_smoothly(self, pos, time = self.animation_time,
                                                        interval = self.animation_interval)
            else:
                self.animationtimer = self.SlideTo(pos)
        else:
            if self.animationtimer:
                self.animationtimer.stop()
                self.animationtimer = None
            self.SetPosition(pos)
        self._moving_to = pos

        if not self.Shown:
            self.StartShow()

    def StartShow(self):
        '''
        Figures out how to show the infobox and sets up the mouseout timer if needed
        '''

        if self.quickshow:
            self.ShowOnScreen()
        elif not self.showingtimer.IsRunning() or self.account is not self.showingtimer.contact:
            self.showingtimer.Start(self.account)

        if not self.mouseouttimer.IsRunning():
            self.mouseouttimer.Start()


    def on_synctimer(self):
        t = self.synctimer
        t.Stop()
        if t.needs_sync:
            t.needs_sync = False
            self.InfoSync()

    @property
    def should_use_maxheight(self):
        # check that self.account.protocol is a string--this means that
        # self.account is an account and not a buddy.
        return self.account is not None and \
               isinstance(self.account.protocol, basestring) and \
               account_info(self.account, 'infobox', 'maxheight', default=False)


    def get_webview_key(self, account):
        if account_info(account, 'infobox', 'hosted', default=False):
            key = 'hosted'
        elif account_info(account, 'infobox', 'own_webview', default=False):
            key = account
        else:
            key = None
        return key

    def set_active_webview(self, account):
        '''
        If account.infobox_own_webview is True, then a new WebView object is
        constructed for that account and stored in self.account_webviews. After
        that, this method will reuse that webview for the account.

        That webview becomes the active webview, is Shown, and set to
        self.profilebox.
        '''
        key = self.get_webview_key(account)

        account_key = get_account_key(account)
        self.active_account_key = account_key

        try:
            webview = self.account_webviews[key]
        except KeyError:
            webview = self.account_webviews[key] = self.construct_webview()
            self.account_jsbridges[key] = bridge = JSPythonBridge(webview)
            if key == 'hosted':
                webview.hosted = True
                from .infoboxapp import init_host
                init_host(bridge, protocol=account.protocol)

        if key == 'hosted':
            def infobox_json_handler(*a, **k):
                # add special D.rpc method "infobox_hide" for hiding the infobox window.
                # TODO: dynamic dispatch and delegate this

                if len(a) and hasattr(a[0], 'get'):
                    method = a[0].get('method', None)
                else:
                    method = None

                if method == 'infobox_hide':
                    return self.DoubleclickHide()
                elif method is not None:
                    if hooks.any('infobox.jsonrpc.' + method, account_key, a[0]):
                        return

                return account.json(*a, **k)

            #this only needs to be done once, not sure where to check right now.
            self.account_jsbridges[key].register_specifier(account_key, infobox_json_handler)

        if self.profilebox is not webview:
            self.infobox_app_hiding()
            self.profilebox.Hide()
            self.profilebox = webview
            self.profilebox.Show()

        return key

    def infobox_app_hiding(self):
        if getattr(self.profilebox, 'hosted', False):
            self.profilebox.RunScript('if (callOnHide) callOnHide();', immediate=True)
        else:
            # when swapping between webviews, or when the infobox hides, if the webview is an "old style"
            # account, just scroll to the top
            self.profilebox.RunScript('window.scrollTo(0, 0);', immediate=True)

    def remove_webview(self, account):
        'Destroys an account specific webview.'
        webview = self.account_webviews.pop(account, None)
        self.account_jsbridges.pop(account, None)
        if webview is not None:
            webview.Destroy()

    def get_content(self, account):
        return self.htmlcacher.GetGeneratedProfile(account, self.htmlfonts)

    def InfoSync(self, *a):
        """Applies capabilities and sets the profilebox to a stripped version of
        what FillInProfile returns, then DoSizeMagic."""

        if not wx.IsMainThread():
            raise AssertionError('InfoSync must be called on the main thread')

        current_key = getattr(self, 'active_account_key', '')
        account_key = get_account_key(self.account)

        if self.IsShown() and \
            account_key is not None and \
            account_key == current_key and \
            not hasattr(self.account, '_current_tab'): # skipping InfoSync is not compatible with accounts with tabs

            # do not immediately infosync--we don't want to replace the currently shown content
            log.info('Skipping InfoSync because content is open')
            self.synctimer.Stop()
            return

        # Maintain a timer to throttle down this method if it is called a lot
        if not hasattr(self, 'synctimer'):
            self.synctimer = wx.PyTimer(self.on_synctimer)
            self.synctimer.needs_sync = False

        # If the timer is already running, we have run too recently--
        # mark it to trigger an InfoSync later.
        if self.synctimer.IsRunning():
            self.synctimer.needs_sync = True
            return

        cpanel = self.cpanel

        with self.Frozen():
            if cpanel.IsShown():
                if self.capbar.Shown:
                    self.capbar.ApplyCaps(self.account)

                skipped_sethtml = self.set_content(self.account)
                if skipped_sethtml or self.should_use_maxheight:
                    self.DoSizeMagic()
            else:
                self.DoSizeMagic()

        self.synctimer.StartOneShot(300)

    def set_content(self, account):
        key = self.set_active_webview(account)
        pb = self.profilebox

        if key == 'hosted':
            from .infoboxapp import set_hosted_content
            set_hosted_content(pb, account)
            return False

        try:
            pfile = self.get_content(self.account)
        except Exception:
            traceback.print_exc()
            pfile = u'<html><body style="text-align: center; margin: {self.padding.x}px {self.padding.y}px;"><div id="content"><span>{message}</span></div></body></html>'
            pfile = pfile.format(self=self, message = _(u'Error generating content').encode('xml'))

        if getattr(pb, '_page', None) != pfile:
            pb._page = pfile
            pb.GetPage = lambda: pb._page

            # If we set content while the user is scrolling, the window locks up. Avoid this
            # by manually releasing the capture the scrollbar gets
            while pb.HasCapture(): pb.ReleaseMouse()

            pb.SetHTML(pfile)
            skipped_sethtml = False
        else:
            skipped_sethtml = True

        return skipped_sethtml

    def Repanelmater(self, infosync = True):
        """
        This generates and remove the contact panels for a metacontact as
        needed. Then it calls InfoSync if infosync is True.
        """
        panelsneeded = len(self.metacontact)
        exp = self.expandopanels
        sz  = self.cpanel.Sizer

        if panelsneeded>0:
            while len(exp) < panelsneeded:
                panel = ExpandoPanel(self.cpanel, self)
                exp.insert(0, panel)
                sz.Insert(0, panel, 0, wx.EXPAND)
            while len(exp) > panelsneeded:
                panel = exp[0]
                panel.Show(False)
                exp.remove(panel)

                sz.Detach(panel)
                panel.Destroy()
        else:
            for panel in exp[:]:
                panel.Show(False)
                exp.remove(panel)
                sz.Detach(panel)
                panel.Destroy()

        self.cpanel.Refresh()

        if infosync:
            self.InfoSync()

    def SelectContact(self, contact):
        """
        When a new contact is selected, account is set to that contact and
        InfoSync is called to get the new profile.
        """
        self.account = contact
        self.InfoSync()

    def OnBeforeLoad(self, event):
        type = event.GetNavigationType()
        if type == wx.webview.WEBVIEW_NAV_LINK_CLICKED:
            event.Cancel()
            self.OnLinkClicked(event)

    def OnLinkClicked(self, event):
        """
            This is for when a link is clicked in the profile box
        """
        #get the href infor of the link object
        url=event.GetURL()

        if url.startswith('file:///'):
            url = url[8:]

#        should_not_hide = False
        #if it's just a profile anchor, the toggle infobox.showprofile and InfoSync
        if url =="profile":
            setpref('infobox.showprofile', not pref('infobox.showprofile'))
            self.InfoSync()
            return
        #if starts with ^_^ the rest of the string represents a function in
        #   account with / used to separate arguments
        elif url.decode('url')[:3]=="^_^":
            url = url.decode('url')
            url = url[3:].split('/')
            fname, args = url.pop(0), url
#            try:
#                should_not_hide =
            getattr(self.account, fname)(*args)
#            except Exception, e:
#                print_exc()
        # otherwise assume it's a link and open in default browser
        else:
            wx.CallAfter(wx.LaunchDefaultBrowser, url)

        #Hide the infobox, depending on pref
#        if pref('infobox.hide_on_click', True):
#            if not should_not_hide: self.Hide()





    def Befriend(self, friend):
        """
            Register a GUI element as a friend of the infobox
            The infobox does not close if the mouse is over a friend
        """

        self.friends.add(friend)

    def Defriend(self, friend):
        """
            Unregister as a friend
        """

        self.friends.discard(friend)

    def FriendlyTouch(self, mp = None):
        """
            Checks friends to see if the mouse is over them
            True if the mouse is over one and the inobox should not close
            False if the infobox should close
        """
        windowatpointer = FindWindowAtPointer()

        for friend in self.friends:
            if friend and windowatpointer is friend:
                if isinstance(friend, BuddyList) and \
                   not friend.ClientRect.Contains(friend.Parent.ScreenToClient(mp or GetMousePosition())) and \
                   GetMouseState().LeftDown():
                    return False
                else:
                    return True
        return False

def construct_html_cacher():
    #Load up the yaml used to build infoboxes for SocialNetworks
    htmlcacher = HtmlCacher()
    htmlcacher.load_format('res/infobox.yaml')

    # Let accounts generate and cache infobox "ahead of time" via a hook
    def on_cache_data(account, html):
        htmlcacher._cache[account] = html

    import hooks
    hooks.register('infobox.cache', on_cache_data)

    return htmlcacher

class HtmlCacher(object):
    def __init__(self):
        self._cache = {}
    def clear(self):
        self._cache.clear()
    def GetGeneratedProfile(self, acct, htmlfonts):
        """
        Decides where to get the profile from, depending on account type and
        protocol, and returns the profile
        """
        ibp = None
        try:
            ibp = ICachingInfoboxHTMLProvider(acct)
        except protocols.AdaptationFailure:
            try:
                ibp = IInfoboxHTMLProvider(acct)
            except protocols.AdaptationFailure:
                pass
        if ibp is not None:
            return ibp.get_html(htmlfonts, self.make_format)

        #Otherwise, generate
        if isinstance(acct, EmailAccount):
            print >> sys.stderr, 'WARNING: FillInProfile called with an email account'
        else:
            try:
                import time
                a = time.clock()
                info = GetInfo(acct, pref('infobox.showprofile', False))
                b = time.clock()
                acct.last_generate = b -a
                return info
            except Exception:
                traceback.print_exc()
                return ''

    def make_format(self, htmlfonts, cachekey, obj=None, data=None):
        """
            If acct is digsby, facebook, or myspace call memo_format with the
            acct, otherwise will fail assertion
        """

        #TODO: This strikes me as silly...
        if isinstance(cachekey, tuple):
            acct = cachekey[0]
        else:
            acct = cachekey
        if acct.service not in ('digsby', 'facebook', 'twitter'):
            warnings.warn('Don\'t know how to make an infobox for %r' % acct)
            return u'<html><body><div id="content">%s</div></body></html>' % _('No additional information')
        return self.memo_format(htmlfonts, cachekey)

    def memo_format(self, htmlfonts, cachekey):
        """Calls format with the format, acct, and htmlfonts."""

#        if not hasattr(self, 'memo_formats'):
#            from collections import defaultdict
#            self.memo_formats = defaultdict(dict)
#        if acct.service == 'facebook' and False:
#            if acct not in self.memo_formats or self.memo_formats[acct]['time'] != acct.last_update:
#                self.memo_formats[acct]['time'] = acct.last_update
#                self.memo_formats[acct]['val']  = format(self.format[acct.service], acct)
#            return self.memo_formats[acct]['val']
#        else:
        if isinstance(cachekey, tuple):
            acct = cachekey[0]
            return format(self.format[acct.service][cachekey[1]], acct, htmlfonts)
        else:
            acct = cachekey
            return format(self.format[acct.service], acct, htmlfonts)

    def load_format(self, fname):
        """
            Load the YAML for the socialnetworks
        """
        import syck

        self._format_fname = fname
        try:
            with open(fname) as f:
                self.format = dict(syck.load(f))
        except:
            self.format = {}
            traceback.print_exc()

    def reload_format(self):
        self.load_format(self._format_fname)
        self.clear()

from copy import deepcopy as copy
from util.primitives.strings import curly
from util.primitives.funcs import get

#TODO: move this back to text util
def TagFont(string, fonttype, fonts):
    font = fonts[fonttype]
    color = fonts['%sfc'%fonttype]
    tag = u''.join(['<span style="font-family: %(facename)s; font-size: %(size)ipt; color: %(color)s;">' %
                        {'facename': font.FaceName,
                         'size': font.PointSize,
                         'color': color},
                    '<b>' if font.Weight == wx.BOLD else '',
                    '<i>' if font.Style == wx.ITALIC else '',
                    '<u>' if font.Underlined else '',
                    string if isinstance(string, unicode) else string.decode('utf-8'),
                    '</u>' if font.Underlined else '',
                    '</i>' if font.Style == wx.ITALIC else '',
                    '</b>' if font.Weight == wx.BOLD else '',
                    '</span>'])
    return tag

def skinimagetag(key):
    '''
    Returns an <img width="x" height="y" src="url" /> tag for a skin key.
    '''

    try:
        img = skin.get(key)
        url = img.path.url()
        width, height = img.Width, img.Height
    except Exception:
        traceback.print_exc()
        return ''

    return '<img width="%d" height="%d" src="%s" />' % (width, height, url)

def format(fmt, obj, htmlfonts, data=None):
    #TODO: Comment this, I'll let Mike do that - Aaron

    if data is None:
        data = []
        return_str = True
    else:
        return_str = False

    mysentinel = Sentinel()

    sget = lambda o, k: get(o, k, mysentinel)

    mydata = []
    mydata_append = mydata.append

    mydata_append("""\
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    </head>
    <style>
        td{
            vertical-align: top;
        }
        tr{
            background: white;
        }
        table{
            table-layout: fixed;
        }
    """ + skin.get_css() + LINK_CSS + '</style>')

    order = get(fmt, 'order', fmt.keys())

    from htmlgeneration import separatorsocial

    curlylocals = copy(fmt)
    curlylocals.update(
        fonts = htmlfonts,
        TagFont = TagFont,
        separator = lambda *a,**k: separatorsocial(),
        skinimagetag = skinimagetag)

    for key in order:
        fmtval = sget(fmt, key)
        objval = sget(obj, key)

        if not objval and get(fmtval, 'hide_empty', False):
            continue

        if mysentinel in (fmtval, objval):
            continue

        elif isinstance(objval, list):
            assert isinstance(fmtval, dict)


            hdr = curly(get(fmtval, 'header', ''), source = curlylocals)
            sep = curly(get(fmtval, 'separator', ''), source = curlylocals)
            ftr = curly(get(fmtval, 'footer', ''), source = curlylocals)

            mydata.append(hdr)

            if not objval:
                curlylocals['obj'] = obj

                val = get(fmtval, 'none', '')

                mydata_append(curly(val, source=curlylocals))
            else:
                for thing in objval:
                    type_d = get(fmtval, type(thing).__name__, {})
                    if not type_d: continue

                    mydata_append(sep)

                    mydata_append(make_icon_str(get(type_d, 'icon', '')))
                    curlylocals['obj'] = thing
                    mesgstr = get(type_d, 'message', '')

                    mydata_append(curly(mesgstr, source=curlylocals))

                mydata_append(sep)

            mydata_append(ftr)

        elif isinstance(fmtval, dict):
            format(fmtval, objval, htmlfonts, mydata)
        else:
            assert isinstance(fmtval, basestring), fmtval
            if not objval:
                continue

            curlylocals['obj'] = obj
            mydata_append(curly(fmtval, source=curlylocals))

    if (len(mydata) - 1) == 0:
        curlylocals['obj'] = obj
        mydata_append(curly(get(fmt, 'none', ''), source=curlylocals))

    mydata_append("</html>")

    mydata = make_header(fmt, curlylocals) + mydata + make_footer(fmt, curlylocals)

    data.extend(mydata)

    if return_str:
        return ''.join(data)
    else:
        return data


def make_icon_str(s):
    #TODO: Comment this, I'll let Mike do that - Aaron
    if not s:
        return ''
    assert s.startswith('skin:')

    s = s[5:]
    sent = object()
    assert skin.get(s, lambda: sent) is not sent, s
    return ('<wxp module="gui.infobox.htmlbitmaps"'
            'class="BitmapFromSkin" width ="99%%" height="-1">'
            '<param name="key" value="%s"></wxp>' % s)

def make_header(fmt, obj):
    """
        Do curly for the header information
    """
    return [curly(get(fmt, k, ''), source = obj) for k in ('header', 'separator')]

def make_footer(fmt, obj):
    """
        Do curly for the footer information
    """
    return [curly(get(fmt, k, ''), source = obj) for k in ('separator', 'footer')]

if 'wxMSW' in wx.PlatformInfo:
    # import some windows functions and constants to keep the infobox floating
    # above other windows (see the ShowOnScreen method below)
    from gui.native.win.winconstants import HWND_TOPMOST, SWP_NOACTIVATE, SWP_NOMOVE, SWP_NOSIZE, SWP_SHOWWINDOW
    WINDOWPOS_FLAGS = SWP_NOACTIVATE | SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW

    from ctypes import windll
    SetWindowPos = windll.user32.SetWindowPos

    def show_on_top(win):
        SetWindowPos(win.Handle, HWND_TOPMOST, 0, 0, 0, 0, WINDOWPOS_FLAGS)

import gui.input
gui.input.add_class_context(_('InfoBox'), 'InfoBox', cls = InfoBox)

def account_info(obj, *path, **k):
    default = k.pop('default', None)
    protocol = getattr(obj, 'protocol', None)
    ret = default

    if isinstance(protocol, basestring) and \
        protocol in protocolmeta.protocols:

        ret = protocolmeta.protocols[protocol]
        while path:
            path0 = path[0]
            path=path[1:]
            if path:
                ret = ret.get(path0, {})
            else:
                ret = ret.get(path0, default)

    return ret

def get_account_key(account):
    """Returns the string key used by infobox to hash accounts when
    swapping them."""

    try:
        if isinstance(account.protocol, basestring):
            return u'%s_%s' % (account.protocol, account.username)
        else:
            return None #explicit is good.
    except AttributeError:
        return None

