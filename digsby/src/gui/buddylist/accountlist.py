'''

Buddylist panel for displaying email and social network accounts.

'''
from __future__ import with_statement
import wx
from common.emailaccount import EmailAccount
import common.actions as actions

from gui.textutil import default_font
from common import profile, pref, setpref
from gui.skin import get as skin
from gui.skin.skinobjects import SkinColor
from util.primitives.funcs import Delegate
from gui.uberwidgets.uberwidget import UberWidget
from gui.uberwidgets.umenu import UMenu

from logging import getLogger; log = getLogger('accountlist')

from gui.buddylist.accounttray import should_grey


from gui.toolbox.refreshtimer import refreshtimer

class AccountList(wx.VListBox,UberWidget):
    'Shows a list of active accounts with counts of new items'

    def __init__(self,
                 parent,
                 accts,
                 infobox,
                 skinkey,
                 prefkey = None,
                 onDoubleClick = None, # a callable taking an acct
                 labelCallback = None, # a callable: acct -> unicode
                 ):
        wx.VListBox.__init__(self, parent)
        self.SetSkinKey(skinkey)

        self.prefkey = prefkey
        self.unlocked = pref(self.prefkey + '.unlocked', True)

        self._obs_link = None
        self.infobox = infobox
        infobox.Befriend(self)

        self.accts = accts

        self.willreconaccts= set()

        self.itemheight = 0
        self.UpdateSkin()

        Bind = self.Bind
        Bind(wx.EVT_MOTION,             self.OnMouseMotion)
        Bind(wx.EVT_LEAVE_WINDOW,       self.OnMouseOut)
        Bind(wx.EVT_RIGHT_UP,           self.OnRightUp)
        Bind(wx.EVT_MOUSEWHEEL,         self.OnMouseWheel)
        Bind(wx.EVT_LEFT_DCLICK,        self.OnLeftDblClick)
        Bind(wx.EVT_LEFT_DOWN,          self.OnLeftDown)
        Bind(wx.EVT_LEFT_UP,            self.OnLeftUp)
        Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseLost)

        self.BuildList()

        self.menu = UMenu(self)

        self.OnDoubleClick = Delegate([onDoubleClick] if onDoubleClick is not None else [])
        self.labelCallback = labelCallback

        self.BindObservers()

    def OnClose(self, e = None):
        """
           Unbinds observer when this widget closes
        """
        log.info('OnClose: %r', self)
        self.UnbindObservers()

    def WhenOrderPrefChanged(self, sortorder):
        if self.order != sortorder:
            self.order = sortorder
            active = dict([(acct.id, acct) for acct in self.active])
            self.active = [active[id] for id in sortorder if id in active]
            self.Refresh()

    def WhenUnlockedPrefChanged(self, unlcoked):
        self.unlocked = pref(self.prefkey + '.unlocked', True)

    def BindObservers(self):
        """
            Sets up observers on a list of accounts
        """
        self._obs_link = self.accts.add_list_observer(self.BuildList, self.WhenStateChanged, 'state', 'enabled', 'count','offline_reason', 'alerts', 'alias')
        profile.prefs.link(self.prefkey + '.order', self.WhenOrderPrefChanged, False)
        profile.prefs.link(self.prefkey + '.unlocked', self.WhenUnlockedPrefChanged, False)

    def UnbindObservers(self):
        'Removes observers on a list of accounts'

        if self._obs_link is not None:
            self._obs_link.disconnect()
            self._obs_link = None

    def CalledAfterRefreshLine(self,acct):
        try:
            self.RefreshLine(self.active.index(acct))
        except ValueError:
            self.Refresh()


    def WhenStateChanged(self, acct, attr, old, new):
        'This handles all changes on an account level.'

        #update new item count
        if attr in ('count', 'alerts', 'alias'):
            wx.CallAfter(self.CalledAfterRefreshLine,acct)
        #rebuild list when account is disabled or enabled
        elif attr == 'enabled':
            wx.CallAfter(self.BuildList)
        #Offline reason has changed, set up message
        elif attr == 'state' or attr == 'offline_reason':
            if acct.offline_reason == acct.Reasons.WILL_RECONNECT:
                self.willreconaccts.add(acct)
            else:
                self.willreconaccts.discard(acct)

            if len(self.willreconaccts):
                refreshtimer().Register(self)
            else:
                refreshtimer().UnRegister(self)

            self.Refresh()




    def OnMouseOut(self, event = None):
        """
            Make sure selection gets updated on mouse out
        """
        i = self.Selection
        if i != -1:
            self.RefreshLine(i)

        self.Selection = -1

    def OnMouseWheel(self, e):
        # foward mouse wheel events to the infobox.
        if self.infobox.IsShown():
            self.infobox.on_mousewheel(e)

    def OnMouseMotion(self,event):
        """
            Selection gets update and infobox gets requested on mouse over item
        """

        mp = event.Position
        hit = self.HitTest(mp)
        dragging = event.Dragging()
        selection = self.Selection
        active = self.active

        if self.unlocked and event.LeftIsDown() and dragging and self.HasCapture() and -1 not in (selection, hit) and hit != selection:
            item = active[selection]
            active.pop(selection)
            active.insert(hit, item)

            sortorder = self.order
            sortorder.remove(item.id)
            i = sortorder.index(active[hit-1].id) + 1 if hit > 0 else 0
            sortorder.insert(i, item.id)
            setpref(self.prefkey + '.order', sortorder)

            self.Refresh()

        self.Selection = hit
        self.TryShowInfobox(hit)

    def OnLeftUp(self, event):

        while self.HasCapture():
            self.ReleaseMouse()

        if not self.ClientRect.Contains(event.Position):
            self.OnMouseOut(event)

    def OnMouseLost(self, event):
        if not self.ClientRect.Contains(self.ScreenToClient(wx.GetMousePosition())):
            self.OnMouseOut()

    def OnLeftDown(self,event):
        self.infobox.quickshow=True
        self.TryShowInfobox(self.Selection)


        if not self.HasCapture():
            self.CaptureMouse()

    def TryShowInfobox(self,i):
        if pref('infobox.show', True) and i >= 0:
            p  = self.Parent
            pl = p.ClientToScreen((0, self.Position.y + self.OnMeasureItem(0) * i))
            pr = pl + (p.Size.width, 0)

            self.infobox.Display(pl, pr, self.active[i])

    def OnLeftDblClick(self,event):
        """
            performs the action associated with the list on DOuble Click
        """
        self.OnDoubleClick(self.active[self.Selection])
        self.infobox.Hide()

    def ToggleOrderLock(self):
        self.unlocked = not self.unlocked
        setpref(self.prefkey + '.unlocked', self.unlocked)

    def OnRightUp(self, event):
        """
            Generate and open menu on right click
        """
        if self.Selection >= 0:
            # populate the popup menu with actions
            self.menu.RemoveAllItems()

            acct = self.active[self.Selection]
            if hasattr(getattr(acct, 'menu_actions', None), '__call__'):
                acct.menu_actions(self.menu)
            elif isinstance(acct, EmailAccount):
                #HAX: an ugly hack until Email-specific actions are removed from EmailAccount.
                actions.menu(wx.FindWindowByName('Buddy List'), acct, menu = self.menu, search_bases = False, cls = EmailAccount)
            else:
                actions.menu(wx.FindWindowByName('Buddy List'), acct, menu = self.menu)

            self.menu.AddSep()

#            if self.prefkey is not None:
#                unlockitem = self.menu.AddCheckItem(_('Allow Rearrange'), callback = self.ToggleOrderLock)
#                unlockitem.Check(self.unlocked)

            self.menu.PopupMenu()

    def BuildList(self,*__):
        """
            When the account list changes rebuild the list of items to display.
            Then it recalculates size needs.
        """

        try: self.__i += 1
        except: self.__i = 1

        accts = self.accts

        sortorder = pref(self.prefkey + '.order')
        self.order = sortorder[:]

        if not len(sortorder):
            sortorder = [acct.id for acct in accts]
        elif len(sortorder) != len(accts) or set(acct.id for acct in accts) != set(sortorder):
            for acct in accts:
                if acct.id not in sortorder:
                    i = accts.index(acct)
                    i = sortorder.index(self.accts[i-1].id) + 1 if i > 0 else 0
                    sortorder.insert(i, acct.id)


        sortset = set(sortorder)
        if len(sortorder) != len(sortset):
            cleansortorder = []
            for i in sortorder:
                if i in sortset:
                    cleansortorder.append(i)
                    sortset.remove(i)
            sortorder = cleansortorder


        if self.order != sortorder:
            setpref(self.prefkey + '.order', sortorder)


        active = dict([(acct.id, acct) for acct in accts if acct.enabled])
        self.active = [active[id] for id in sortorder if id in active]

        with self.Frozen():
            self.ItemCount = len(self.active)
            self.Size = self.MinSize = wx.Size(-1, self.ItemCount * self.itemheight)
            self.Top.Layout()
            self.Top.Refresh()

        self.Refresh()

    def UpdateSkin(self):
        """
            The usual
        """
        skinget = lambda s, default: skin('%s.%s' % (self.skinkey, s), default)

        self.padding    = skinget('padding',lambda: wx.Point(3,3))
        self.Font       = skinget('font', default_font)
        self.iconsize   = skinget('iconsize',16)
        self.itemheight = max(self.iconsize,self.Font.LineHeight)+self.padding.y*2

        default_color = SkinColor(wx.Color(225,255,225))
        self.bg       = skinget('backgrounds.normal', default_color)
        self.selbg    = skinget('backgrounds.hover',  default_color)

        self.fontcolor    = skinget('fontcolors.normal',wx.BLACK)
        self.selfontcolor = skinget('fontcolors.hover',wx.BLACK)

        self.MinSize = wx.Size(-1, self.itemheight * self.ItemCount)

    def OnMeasureItem(self, n):
        "Returns the predetermined item height"

        return self.itemheight

    def OnDrawBackground(self, dc, rect, n):
        getattr(self, 'selbg' if self.Selection == n else 'bg').Draw(dc, rect, n)

    def OnDrawItem(self, dc, rect, n):
        'Draw the foreground content of the item.'

        dc.Font = self.Font
        dc.TextForeground = self.selfontcolor if n == self.Selection else self.fontcolor

        acct = self.active[n]
        iconsize=self.iconsize

        if (hasattr(acct, 'count') and acct.count > 0) or not should_grey(acct):
            icon = acct.icon.Resized(iconsize)
        else:
            icon = acct.icon.Greyed.Resized(iconsize)

        pad  = self.padding.x

        dc.DrawBitmap(icon, rect.x + pad, rect.y + self.itemheight / 2 - icon.Height/2, True)

        xoff = iconsize + 2 * pad
        textRect = wx.Rect(rect.x + xoff, rect.y + self.itemheight / 2 - dc.Font.LineHeight/2, rect.width - xoff, dc.Font.LineHeight)
        dc.DrawTruncatedText(self.labelCallback(acct), textRect)

