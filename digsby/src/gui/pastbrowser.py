'''
View past chats
'''
from __future__ import with_statement
from gui.uberwidgets.umenu import UMenu
import wx
from gui import skin
from gui.uberwidgets.PrefPanel import PrefPanel
from gui.uberwidgets.UberCombo import UberCombo
from gui.uberwidgets.simplemenu import SimpleMenuItem
from gui.uberwidgets.UberButton import UberButton
from gui.toolbox import persist_window_pos, snap_pref, update_tooltip
from gui.browser.webkit import WebKitWindow
from cgui import SimplePanel

from util.primitives.mapping import Storage
from digsby_chatlogs.interfaces import IAliasProvider
from common import profile
#from protocols import AdaptationFailure #need to fix package names to get to this
from common import logger

import logging; log = logging.getLogger('pastbrowser')

from wx import ALL, TOP, BOTTOM, LEFT, \
               EXPAND, \
               ALIGN_CENTER_VERTICAL, ALIGN_LEFT, ALIGN_RIGHT, \
               VERTICAL, HORIZONTAL, \
               Color, BoxSizer, Brush, Rect
from gui.toolbox.scrolling import WheelScrollCtrlZoomMixin, \
                                            WheelShiftScrollFastMixin,\
    ScrollWinMixin, FrozenLoopScrollMixin

TOPLESS = ALL & ~TOP

BUTTON_SKIN = 'AppDefaults.PastButton'

from wx import DateTimeFromDMY

from wx.calendar import CAL_SUNDAY_FIRST, CAL_SEQUENTIAL_MONTH_SELECTION, CAL_SHOW_HOLIDAYS, \
                        EVT_CALENDAR_MONTH, EVT_CALENDAR_YEAR, EVT_CALENDAR_SEL_CHANGED, \
                        CalendarCtrl, CalendarDateAttr

SUBHTML = """
$('.buddy').each(function(){
    var bname = %s;
    var balias = %s;
    if ($(this).html() == bname) {
        $(this).html(balias);
        $(this).attr('title', bname);
    }
});"""

wx.DateTime.__hash__ = lambda dt: hash(dt.GetTicks())

def logpath_for_date(buddy, date):
    year  = '%d'   % int(date.GetYear())
    month = '%02d' % (date.GetMonth() + 1)
    day   = '%02d' % int(date.GetDay())

    return buddy.dir / ''.join([year, '-', month, '-', day, '.html'])


def _group_chat_icon():
    return skin.get('actionsbar.icons.roomlist')

def MakeAccountItems():
    logdir = logger.get_default_logging_dir()

    protodirs = logdir.dirs()

    accts = {}
    for protodir in protodirs:
        accts[protodir.name] = [dir.name for dir in protodir.dirs()]

    items = []
    for proto in sorted(accts):
        try:
            protoicon = skin.get('serviceicons.'+proto,None).ResizedSmaller(16)
        except Exception:
            continue

        for acct in accts[proto]:
            items.append(SimpleMenuItem([protoicon,acct], id = {'logdir':logdir,
                                                                'proto':proto,
                                                                'acct': acct}))

    # group chat at bottom
    icon = _group_chat_icon().Resized(16)
    items.append(SimpleMenuItem([icon, _('Group Chats')], id = {
        'proto': 'group',
    }))

    return items

def GetGroupChats():
    return list(profile.logger.walk_group_chats())

def GetBuddies(id):
    acctdir = id['logdir'] / id['proto'] / id['acct']
    buddies = []
    aliases = IAliasProvider(profile())
    for bdir in acctdir.dirs():
        try:
            name, service = bdir.name.rsplit('_', 1)
            serviceicon = skin.get('serviceicons.'+service,None).ResizedSmaller(16)
        except Exception:
            continue
        buddies.append(Storage(icon = serviceicon,
                               name = name,
                               alias = aliases.get_alias(name.lower(), service, acctdir.parent.name) or name,
                               protocol = acctdir.parent.name,
                               service = service,
                               dir = bdir))

    buddies.sort(key=lambda s: s.alias.lower())

    return buddies

def GetDates(logdir):
    dates = []
    append = dates.append

    for logfile in logdir.files():
        datestring = logfile.name

        try:
            y, m, d = datestring[:datestring.rfind('.')].split('-')
            y, m, d = int(y), int(m)-1, int(d)
        except Exception:
            pass # ignore non-logfiles...
        else:
            append(DateTimeFromDMY(d, m, y))

    return sorted(dates)



bgcolors = [
    wx.Color(239, 239, 239),
    wx.Color(255, 255, 255),
]

hovbgcolor = wx.Color(220, 220, 220)

def SelectAccountByDir(acctdir,combo):
    for item in combo:
        id = item.id
        if acctdir.lower() == (id['logdir'] / id['proto'] / id['acct']).lower():
            combo.SetSelection(combo.GetIndex(item))
            return True

    return False

class GroupChatRenderer(object):
    def get_icon(self, chat):
        return (skin.get('serviceicons.' + chat['service'], None) or _group_chat_icon()).ResizedSmaller(16)

    def get_label(self, chat):
        time = chat['time'].strftime('%I:%M %p')
        roomname = chat.get('roomname', None)
        if roomname:
            return '%s - %s' % (time, roomname)
        else:
            return time

    get_tooltip = get_label

class BuddyRenderer(object):
    def get_icon(self, buddy):
        return buddy.icon

    def get_label(self, buddy):
        return buddy.alias

    def get_tooltip(self, buddy):
        return buddy.name


class ListOBuddies(wx.VListBox):
    def __init__(self,parent):
        wx.VListBox.__init__(self,parent,-1)

        self.buddies = []

        self.Hovered = -1

        self.SetItemCount(0)

        self.itemheight = max(self.Font.Height, 16)+10

        self.date = None

        Bind = self.Bind
        Bind(wx.EVT_MOTION, self.OnMotion)

    def OnMotion(self,event):
        rect = self.ClientRect
        wap = wx.FindWindowAtPointer()
        mp = event.Position
        hit = self.HitTest(mp)

        if not rect.Contains(mp) or not wap == self:
            while self.HasCapture():
                self.ReleaseMouse()

            self.Hovered = -1
            self.SetToolTip(None)
            self.Refresh()
            return

        elif not self.HasCapture():
            self.CaptureMouse()

        self.Hovered = hit

        # buddy screenname tooltips
        tooltip = self.renderer.get_tooltip(self.buddies[hit]) if hit != -1 else None
        update_tooltip(self, tooltip)

        self.Refresh()


    def OnDrawBackground(self,dc,rect,n):
        if self.Selection == n:
            dc.Brush = Brush(wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))

            #wx.VListBox.OnDrawBackground(self,dc,rect,n)
            #return
        else:
            dc.Brush = Brush(hovbgcolor if self.Hovered == n else bgcolors[n % len(bgcolors)])
        dc.Pen = wx.TRANSPARENT_PEN
        dc.DrawRectangleRect(rect)

    def OnDrawItem(self, dc, rect, n):

        dc.Font=self.Font
        dc.TextForeground = wx.WHITE if self.Selection==n else wx.BLACK


        x = rect.x + 3
        y = rect.y + rect.height//2 - 8

        item = self.buddies[n]
        dc.DrawBitmap(self.renderer.get_icon(item),x,y,True)

        textrect = Rect(x + 16 + 3, rect.y, rect.Width - x - 38, rect.Height)

        dc.DrawLabel(self.renderer.get_label(item), textrect, ALIGN_CENTER_VERTICAL|ALIGN_LEFT)

    def OnMeasureItem(self,n):
        return self.itemheight

    def SetList(self, buddies, renderer):
        self.buddies = buddies
        self.renderer = renderer

        self.SetItemCount(len(self.buddies))

        if self.ItemCount:
            self.SetSelection(0)

        wx.CallAfter(self.Refresh)

    @property
    def SelectedBuddy(self):
        return self.buddies[self.Selection]

    SelectedItem = SelectedBuddy

    def SelectConversation(self, convo):
        for i, b in enumerate(self.buddies):
            if b['file'] == profile.logger.get_path_for_chat(convo):
                return self.SetSelection(i)

    def SelectBuddy(self, service, name):

        found = -1
        for i, buddy in enumerate(self.buddies):
            if buddy.name == name and buddy.service == service:
                found = i
                break

        self.Selection = found

        if found != -1:
            self.ProcessEvent(wx.CommandEvent(wx.wxEVT_COMMAND_LISTBOX_SELECTED))
            self.Refresh()
            return True
        else:
            self.Refresh()
            return False

class FindBar(wx.Panel):
    def __init__(self, parent, viewer):
        wx.Panel.__init__(self, parent)


        self.viewer = viewer

        # construct
        find_label = wx.StaticText(self, -1, _('Find'))
        self.TextControl = find_input = wx.TextCtrl(self, -1, size = (180, -1), style = wx.TE_PROCESS_ENTER)

        nextbutton = self.nextbutton = UberButton(self, label = _('Next'), skin = 'AppDefaults.PastButton')
        prevbutton = self.prevbutton = UberButton(self, label = _('Prev'), skin = 'AppDefaults.PastButton')

        # layout
        sz = self.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        sz.AddMany([(find_label, 0, TOP | BOTTOM | LEFT | ALIGN_CENTER_VERTICAL | ALIGN_RIGHT, 6),
                    (find_input, 0, TOP | BOTTOM | LEFT | ALIGN_CENTER_VERTICAL , 6),
                    (nextbutton, 0, TOP | BOTTOM | LEFT | ALIGN_CENTER_VERTICAL | EXPAND , 6),
                    (prevbutton, 0, TOP | BOTTOM | LEFT | ALIGN_CENTER_VERTICAL | EXPAND , 6)])

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        Bind = self.Bind
        Bind(wx.EVT_PAINT, self.OnPaint)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        fiBind = find_input.Bind
        fiBind(wx.EVT_TEXT,     self.OnFindText)
        fiBind(wx.EVT_KEY_DOWN, self.OnFindKey)

        nextbutton.Bind(wx.EVT_BUTTON, self.OnFindText)
        prevbutton.Bind(wx.EVT_BUTTON, lambda e: self.OnFindText(e,False))

        self.EnableFindButtons('')

    def OnFindKey(self, e):
        c = e.KeyCode
        if c in (wx.WXK_RETURN, wx.WXK_F3) or (c == ord('G') and e.GetModifiers() in (wx.MOD_CMD,wx.MOD_CMD+wx.MOD_SHIFT)):
            self.OnFindText(forward = not e.ShiftDown())
            self.TextControl.SetFocus()
        else:
            e.Skip()


    def OnFindText(self, e = None, forward = True):
        value = self.TextControl.Value
        self.EnableFindButtons(value)
        self.viewer.FindString(self.TextControl.Value,
                               forward,
                               False,
                               True,
                               True)

    def EnableFindButtons(self, textctrl_value):
        buttons_enabled = bool(textctrl_value)

        self.nextbutton.Enable(buttons_enabled)
        self.prevbutton.Enable(buttons_enabled)


    def OnPaint(self,event):
        rect = wx.RectS(self.ClientSize)

        dc = wx.AutoBufferedPaintDC(self)

        dc.Brush = wx.WHITE_BRUSH
        dc.Pen = wx.Pen(wx.Color(213,213,213))

        dc.DrawRectangleRect(rect)


class PastBrowserWebkitWindow(FrozenLoopScrollMixin,
                              ScrollWinMixin,
                              WheelShiftScrollFastMixin,
                              WheelScrollCtrlZoomMixin,
                              WebKitWindow):
    pass

class PastBrowserPanel(SimplePanel):
    '''
    Holds the various sections of the past chat browser UI
    '''

    def __init__(self,parent):
        SimplePanel.__init__(self, parent, wx.FULL_REPAINT_ON_RESIZE)

        self.BackgroundColour = wx.WHITE

        self.Sizer = wx.BoxSizer(HORIZONTAL)
        sz = wx.BoxSizer(HORIZONTAL)

        self.Sizer.Add(sz,1,EXPAND|ALL,3)

        leftcol = wx.BoxSizer(VERTICAL)

        acctcombo = self.acctcombo = UberCombo(self, value='',skinkey='AppDefaults.PrefCombo')
        acctcont = PrefPanel(self,acctcombo,_('Account'))


        leftcol.Add(acctcont,0,EXPAND|ALL,3)

        buddylist = self.buddylist = ListOBuddies(self)
        self.buddies_panel = buddycont = PrefPanel(self, buddylist, _('Buddy'))
        leftcol.Add(buddycont, 1, EXPAND | TOPLESS, 3)

        style = wx.NO_BORDER | CAL_SUNDAY_FIRST | CAL_SEQUENTIAL_MONTH_SELECTION | CAL_SHOW_HOLIDAYS
        cal = self.cal = CalendarCtrl(self, -1, wx.DateTime.Now(), wx.DefaultPosition, wx.DefaultSize, style)

        cal.SetForegroundColour(wx.Color(160, 160, 160))
        cal.SetHolidayColours(wx.BLACK, wx.WHITE)
        cal.SetHeaderColours(Color(160, 160, 160), Color(239, 239, 239))

        calcont = PrefPanel(self,cal,_('Date'))
        leftcol.Add(calcont, 0, EXPAND | TOPLESS, 3)

        sz.Add(leftcol, 0, EXPAND)

        viewpanel = wx.Panel(self)

        viewer = self.viewer = PastBrowserWebkitWindow(viewpanel)
#        viewer.SetMouseWheelZooms(True)
        finder = self.finder = FindBar(viewpanel,viewer)

        menu = UMenu(viewer)
        menu.AddItem(_('Copy'),  id = wx.ID_COPY,  callback = lambda *a: viewer.Copy())

        viewer.BindWheel(self)
        viewer.BindScrollWin(self)
        viewer.Bind(wx.EVT_CONTEXT_MENU,
                    lambda e: (menu.GetItemById(wx.ID_COPY).Enable(viewer.CanCopy()),
                               menu.PopupMenu(event = e)))

        viewer.Bind(wx.EVT_KEY_DOWN,self.OnKeyDown)
        finder.TextControl.Bind(wx.EVT_KEY_DOWN,self.OnKeyDown)

        nav  = BoxSizer(wx.HORIZONTAL)

        prev = self.prev = UberButton(viewpanel, label = '<-', skin = BUTTON_SKIN)
        next = self.next = UberButton(viewpanel, label = '->', skin = BUTTON_SKIN)

        datelabel = wx.StaticText(viewpanel, -1, style = wx.ALIGN_CENTER| wx.ST_NO_AUTORESIZE)
        datelabel.SetMinSize((140, -1))


        prev.Bind(wx.EVT_BUTTON, lambda e: self.Flip(-1))
        next.Bind(wx.EVT_BUTTON, lambda e: self.Flip( 1))

        nav.AddStretchSpacer(1)
        nav.AddMany([(prev, 0, wx.EXPAND | wx.ALIGN_CENTER),
                     (datelabel, 0, wx.EXPAND | wx.ALIGN_CENTER),
                     (next, 0, wx.EXPAND | wx.ALIGN_CENTER)])
        nav.AddStretchSpacer(1)


        viewpanel.Sizer = wx.BoxSizer(wx.VERTICAL)
        viewpanel.Sizer.AddMany([ (nav,    0, EXPAND),
                                  (viewer, 1, EXPAND),
                                  (finder, 0, EXPAND) ])

        sz.Add(PrefPanel(self, viewpanel, _('Conversation Log')), 1, EXPAND | ALL, 3)

        Bind = self.Bind
        Bind(wx.EVT_PAINT, self.OnPaint)

        def OnAcct(*a):
            '''
            Handle selection of a new account from the Account drop down
            '''
            if self.GroupChatsSelected():
                from collections import defaultdict
                self.groupchats = defaultdict(list)
                for g in GetGroupChats():
                    d = g['time']
                    key = DateTimeFromDMY(d.day, d.month-1, d.year)
                    self.groupchats[key].append(g)

                #dates = sorted((g['date'], g) for g in
                self.dates = sorted(self.groupchats.keys())
                UpdateCal()
                self.buddies_panel.SetTitle(_('Chats'))
            else:
                buddylist.SetList(GetBuddies(acctcombo.Value.id), BuddyRenderer())
                OnBuddy()
                self.buddies_panel.SetTitle(_('Buddy'))

        def OnBuddy(*a):
            '''
            Handels selection of a buddy from the buddy pannel
            '''

            if not self.GroupChatsSelected():
                self.dates = GetDates(buddylist.SelectedBuddy.dir)
                UpdateCal()
            else:
                ViewLogForFile(buddylist.SelectedItem['file'], do_aliases=False)

        def UpdateCal():
            '''
            Switches the date to the last date conversed with the selected budy
            '''
            self.next.Enable(True)
            self.prev.Enable(True)
            if self.dates:
                self.cal.Date = self.dates[-1]

            self.cal.Enable(True)
            OnCalChange()

        def OnCalChange(*a):
            '''
            Update the Calendar UI to a new date
            '''
            caldate = cal.Date

            currentyear   = caldate.GetYear()
            currentmonth  = caldate.GetMonth()
            relevantdates = frozenset(date.GetDay() for date in self.dates
                                      if date.GetYear() == currentyear and
                                      date.GetMonth() == currentmonth and date.GetDay())
            SetHoliday, SetAttr = cal.SetHoliday, cal.SetAttr

            for i in xrange(1, 32):
                if i in relevantdates:
                    SetHoliday(i)
                else:
                    SetAttr(i, CalendarDateAttr(Color(160,160,160)))


            OnDayChange()

        self.OnCalChange = OnCalChange

        def ViewLogForDay(date):
            '''
            Load the log file for the specified date for the currently selected buddy
            '''
            logpath = logpath_for_date(buddylist.SelectedBuddy, date)
            ViewLogForFile(logpath)

        def ViewLogForFile(logpath, do_aliases=True):
            '''
            Update the log viewer with the file specified
            '''
            with viewer.Frozen():
                viewer.SetPageSource(logpath.text('utf-8', 'replace'), logpath.url())
                viewer.RunScript('window.scroll(0, 0);')

                if do_aliases:
                    substitue_aliases()

                import hooks
                hooks.notify('digsby.statistics.logviewer.log_viewed')

        def substitue_aliases():
            '''
            Swap out buddy names with their allies
            '''
            import gui
            with open(gui.skin.resourcedir() / 'html' / 'jquery-1.3.2.js', 'rb') as f:
                viewer.RunScript(f.read())
            buddy = buddylist.SelectedBuddy
            aliases = IAliasProvider(profile())
            import simplejson as json
            names = set(json.loads(viewer.RunScript("var foo = []; $('.buddy').each(function(){foo.push($(this).html())}); JSON.stringify(foo);")))
            for name in names:
                alias = aliases.get_alias(name, buddy.service, buddy.protocol) or name
                viewer.RunScript(SUBHTML % (json.dumps(name), json.dumps(alias)))

        def OnDayChange(*a):
            '''
            Show the log for the day selected in the clander
            '''
            date = cal.Date
            self.date = date

            datelabel.SetLabel(date.FormatDate())

            if cal.GetAttr(date.GetDay()).IsHoliday():
                if self.GroupChatsSelected():
                    chats = sorted(self.groupchats[date], key=lambda g: g['time'], reverse=True)
                    buddylist.SetList(chats, GroupChatRenderer())
                    if chats:
                        ViewLogForFile(chats[0]['file'], do_aliases=False)
                else:
                    ViewLogForDay(date)
            else:
                year  = str(date.GetYear())
                month = date.GetMonth()
                month = wx.DateTime.GetMonthName(int(month))
                day   = str(date.GetDay())

                specific_day_string = _('{month}, {day}, {year}').format(month=month, day=day, year=year)

                if self.GroupChatsSelected():
                    msg = _("There are no chat logs for {specific_day_string}.").format(specific_day_string=specific_day_string)
                else:
                    msg = _("There are no chat logs for {specific_day_string} with {name}.").format(specific_day_string=specific_day_string, name=buddylist.SelectedBuddy.name)

                viewer.SetPageSource(msg, 'file:///C:/')

            viewer.SetFocus()


            wx.CallAfter(cal.Refresh)
        self.OnDayChange = OnDayChange

        acctcombo.SetCallbacks(value = OnAcct)
        buddylist.Bind(wx.EVT_LISTBOX, OnBuddy)

        cBind = cal.Bind
        cBind(EVT_CALENDAR_YEAR, OnCalChange)
        cBind(EVT_CALENDAR_MONTH, OnCalChange)
        cBind(EVT_CALENDAR_SEL_CHANGED, OnDayChange)

        acctcombo.SetItems(MakeAccountItems(), 0)

    def GroupChatsSelected(self):
        obj = self.acctcombo.Value.id
        return obj['proto'] == 'group'

    def OnKeyDown(self,event):

        KeyCode = event.KeyCode

        if KeyCode == wx.WXK_PAGEDOWN:
            self.viewer.ScrollPages(1)
        elif KeyCode == wx.WXK_PAGEUP:
            self.viewer.ScrollPages(-1)
        elif KeyCode == ord('C') and event.Modifiers == wx.MOD_CONTROL:
            # do not remove until webkit key handling is fixed
            self.viewer.Copy()
        else:
            event.Skip()


    def Flip(self, delta):
        dates = self.dates
        date  = self.date

        try:
            foundIndex = dates.index(date) + delta
        except ValueError:
            alldates = [DateTimeFromDMY(1, 1, 1900)] + dates + [DateTimeFromDMY(20, 10, 3000)]
            foundIndex = len(dates) - 1
            for i in xrange(1, len(alldates)):
                if date.IsStrictlyBetween(alldates[i-1], alldates[i]):
                    foundIndex = i-2 if delta < 0 else i
                    break

        foundIndex = max(0, min(len(dates) - 1, foundIndex))

        self.cal.SetDate(dates[foundIndex])
        self.OnCalChange()

    def OnPaint(self,event):
        rect     = wx.RectS(self.Size)
        dc       = wx.PaintDC(self)
        dc.Brush = wx.WHITE_BRUSH
        dc.Pen   = wx.TRANSPARENT_PEN

        dc.DrawRectangleRect(rect)

    def OpenBuddyHistory(self, acctdir, acct, name, service):

        if not SelectAccountByDir(acctdir, self.acctcombo):
            self.next.Enable(False)
            self.prev.Enable(False)
            self.cal.Enable(False)
            return self.NoHistory(name, service, acct)



        def AfterOpenBuddyHistory():
            if not self.buddylist.SelectBuddy(service, name):
                self.next.Enable(False)
                self.prev.Enable(False)
                self.cal.Enable(False)
                return self.NoHistory(name, service, acct)

            self.next.Enable(True)
            self.prev.Enable(True)
            self.cal.Enable(True)
            self.Flip(1)

        wx.CallAfter(AfterOpenBuddyHistory)

    def OpenConversation(self, convo):
        if not convo.ischat:
            wx.CallAfter(convo.Buddy.view_past_chats, convo.protocol.account)

        self.acctcombo.SetSelection(self.acctcombo.GetCount()-1)

        @wx.CallAfter
        def after():
            self.buddylist.SelectConversation(convo)

    def NoHistory(self, name, service, acct):
        self.viewer.SetPageSource(_("There is no chat history for {name} on {service} with {acct}.").format(
            name=name,
            service=service,
            acct=acct),'file:///C:/')
        self.viewer.SetFocus()


class PastBrowser(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, _('Past Chat Browser'), name = 'Past Chat Browser')
        self.SetFrameIcon(skin.get('appdefaults.taskbaricon'))

        sz = self.Sizer = wx.BoxSizer(VERTICAL)
        self.pastbrowser = PastBrowserPanel(self)
        sz.Add(self.pastbrowser, 1, EXPAND)

        persist_window_pos(self, defaultPos = wx.Point(150, 150), defaultSize = wx.Size(700, 500))
        snap_pref(self)

    @classmethod
    def MakeOrShow(cls):
        win = cls.RaiseExisting()

        if win is None:
            win = cls()
            wx.CallAfter(win.Show)

        return win

    @classmethod
    def MakeOrShowAndSelect(cls, buddydir):
        acctdir      = buddydir.parent
        acct         = acctdir.name
        name,service = buddydir.name.rsplit('_',1)

        win = cls.MakeOrShow()
        win.pastbrowser.OpenBuddyHistory(acctdir, acct, name, service)

    @classmethod
    def MakeOrShowAndSelectConvo(cls, convo):
        win = cls.MakeOrShow()
        win.pastbrowser.OpenConversation(convo)

if __name__=='__main__':

    from tests.testapp import testapp
    a = testapp(username = 'aaron')

    from path import path

    dir = path('C:\\Users\\Aaron\\Documents\\Digsby Logs\\aaron\\digsby\\aaron@digsby.org\\mike@digsby.org_digsby')
    PastBrowser.MakeOrShowAndSelect(dir)

#    f = PastBrowser()
#    f.Show()
    a.MainLoop()
