'''
Buddy-list specific functionality.
'''
from __future__ import with_statement
from __future__ import division
from gui.toolbox.scrolling import WheelScrollMixin

DEFAULT_FIND_TIMEOUTMS = 1500
IDLE_UPDATE_SECS = 30

EXPANSION_STATE_KEY = 'collapsedgroups'
EXPANSION_SAVE_TIME_SECS = 4

NEED_HELP_LINK = 'http://wiki.digsby.com/doku.php?id=gettingstarted#adding_your_accounts'

import sys
import config
import wx
from wx import Rect
import actionIDs
from wx import StockCursor, CURSOR_HAND, CURSOR_ARROW

from gui.contactdialogs import MetaContactDialog
from gui.treelist import TreeList, TreeListModel
from gui.uberwidgets.umenu import UMenu
from gui.textutil import default_font
from contacts.buddylistsort import SpecialGroup

from gui import skin
from gui.skin.skinobjects import SkinColor
from contacts import DGroup, Contact, MetaContact
from traceback import print_exc

GroupTypes = (DGroup, )

from common import profile, prefprop, pref
from util import callsback, Storage as S, traceguard, delayed_call, default_timer, try_this

from collections import defaultdict

from logging import getLogger
log = getLogger('buddylist'); info = log.info

# keys that cause the IM window to open
activate_keys = set([wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER])

class BuddyListBase(TreeList):
    'Base buddy list class.'

    def __init__(self, parent, model, keyhandler = None):
        TreeList.__init__(self, parent, model, keyhandler = keyhandler)
        self.last_pair = (-1, -1)
        self.hilite = None # Where the mouse is dragging.

        self.SetDrawCallback(self.cskin_drawcallback)
        self.SetPaintCallback(self.PostPaint)

    def cskin_drawcallback(self, dc, rect, n):
        self.OnDrawBackground(dc, Rect(*rect), n)
        self.OnDrawItem(dc, Rect(*rect), n)
        self.OnDrawSeparator(dc, Rect(*rect), n)

    def OnDrawSeparator( self, dc, rect, n ):
        'Draws visual feedback when dragging.'

        bar, box = self.dragimgs.bar, self.dragimgs.box

        hilite = getattr(self, 'hilite')
        if hilite:
            area, i, drop_to = hilite
            s = bar.Size

#            print "area: %s, n: %d, i: %d, (drop_to): %r" % (area, n, i, drop_to)

            if area == 'below_group' and self.model.is_expanded(i):
                if n == i + len(drop_to):
                    bar.Draw(dc, Rect(rect.X, rect.Bottom - s.height / 2 + 1, rect.Width, s.height))
                return
            elif area == 'below_group':
                area = 'below'

            if n == i:
                if area == 'box':
                    box.Draw(dc, rect, n)
                elif area == 'above':
                    bar.Draw(dc, Rect(rect.X, rect.Y - s.height / 2,      rect.Width, s.height))
                elif area == 'below':
                    bar.Draw(dc, Rect(rect.X, rect.Bottom - s.height / 2 + 1, rect.Width, s.height))
            elif n == i + 1:
                if area == 'below':
                    bar.Draw(dc, Rect(rect.X, rect.Y - s.height / 2,      rect.Width, s.height))
            elif n == i - 1:
                if area == 'above':
                    bar.Draw(dc, Rect(rect.X, rect.Bottom - s.height / 2 + 1, rect.Width, s.height))

class BuddyList(WheelScrollMixin, BuddyListBase):
    'Main buddy list control.'

    # The amount of space given to "borders" between buddy list elements during
    # drag and drop.
    def __init__(self, parent, infobox, collapsed = None, keyhandler = None):
        # load expanded groups
        try:    collapsed = eval(profile.localprefs[EXPANSION_STATE_KEY])
        except: collapsed = [u'OfflineGroup_Offline'] # TODO: actually run expanded_id on the offline group to obtain this string

        self.dragResult = wx.DragMove
        self.infobox_scrollers = set()

        # an empty group forms the root of the hierarchy
        model = TreeListModel( collapsed = collapsed )

        # store idle indices for a periodical refresh
        self.idle_indices = []
        self.idle_timer = wx.PyTimer(self.refresh_idle_buddies)

        # save expansion after EXPANSION_SAVE_TIME seconds
        def save_expansion(): profile.localprefs[EXPANSION_STATE_KEY] = repr(list(model.collapsed))
        profile.PreDisconnectHooks.append(save_expansion)
        model.expansion_state_changed += delayed_call(save_expansion, EXPANSION_SAVE_TIME_SECS)
        model.expansion_state_changed += lambda: self.renderers_cache.clear()

        from jabber.JabberContact import JabberContact
        model.donotexpand += [MetaContact, JabberContact]

        super(BuddyList, self).__init__(parent, model)

        Bind = self.Bind
        Bind(wx.EVT_MOTION, self.motion)
        Bind(wx.EVT_ENTER_WINDOW, self.enter_window)
        Bind(wx.EVT_LEAVE_WINDOW, self.leave_window)
        Bind(wx.EVT_MIDDLE_UP, self.on_middle_up)
        self.BindWheel(self)
        Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        Bind(wx.EVT_KEY_DOWN, self.__onkey)

        if keyhandler is not None:
            Bind(wx.EVT_CHAR, keyhandler)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.update_renderers()

        self.dragging_obj = None
        self.shownbuddies = defaultdict(list)

        with traceguard:
            self.SetDropTarget(BuddyListDropTarget(self))

        # On Mac OS X, we don't get mouse moved events when the
        # window is inactive or not focused, so poll the mouse state
        # whenever we enter the window
        self.mouse_tracker = None
        if config.platform == 'mac':
            self.mouse_tracker = wx.PyTimer(self.motion)

        blist  = profile.blist

        # Observe changes to the buddylist structure.
        blist.add_observer(self.on_blist_update)

        self.infobox = infobox
        infobox.Befriend(self)

        top_bind = self.Top.Bind
        top_bind(wx.EVT_SHOW,     self.on_frame_show_or_iconized)
        top_bind(wx.EVT_ICONIZE,  self.on_frame_show_or_iconized)

    def on_frame_show_or_iconized(self, e):
        # Since this control is the only observer of the sorter, we can
        # add a hack that disables sorting when the buddylist isn't shown.
        #
        # When you bring the buddylist back, a sort will happen.
        e.Skip()
        frame = self.Top

        def later():
            visible = frame.IsShown() and not frame.IsIconized()
            profile.blist.set_sort_paused(not visible)

        # allow adjacent iconize/show to catch up
        wx.CallLater(50, later)

    @property
    def context_menu(self):
        try:
            return self._context_menu
        except AttributeError:
            self._context_menu = UMenu(self, _('BuddyList Popup'))
            return self._context_menu

    def on_blist_update(self, blist, *a):
        if not self: return
        self.set_root(blist.view)

    showing_idle = prefprop('buddylist.layout.extra_info')

    def PostPaint(self, dc):
        self.paint_add_link(dc)

        # reset the idle timer when painting
        if self.showing_idle in ('both', 'idle'):
            self.idle_timer.Start(IDLE_UPDATE_SECS * 1000)

        profile.blist.set_sort_paused(False)

        if not getattr(self, '_did_startup_time', False):
            self._did_startup_time = True
            import sys
            from time import clock
            sys._startup_time = clock()

            if getattr(getattr(sys, 'opts', None), 'measure') == 'startup':
                print 'startup time', sys._startup_time
                import os
                os._exit(0)

    def refresh_idle_buddies(self):
        for i in self.idle_indices:
            self.RefreshLine(i)

    def paint_add_link(self, dc):
        if len(self.model) == 0:
            amgr = profile.account_manager

            if amgr.accounts_loaded and len(amgr.accounts) == 0:
                try:
                    f = skin.get('BuddiesPanel.Fonts.AddAccountsLink', default_font)
                    f.SetUnderlined(True)

                    dc.SetTextForeground(skin.get('BuddiesPanel.FontColors.AddAccountsLink', wx.BLUE))
                except Exception:
                    print_exc()
                    f = self.Font

                dc.SetFont(f)

                # Center an "Add Accounts" link in the client area.
                s = _('Add Accounts')

                w, h = dc.GetTextExtent(s)

                # position the link 1/4 down the list
                r = self.ClientRect
                r.Height = r.Height / 2
                x, y = r.HCenterW(w), r.VCenterH(h)

                dc.DrawText(s, x, y)
                self._linkrect = wx.Rect(x, y, w, h)

                # Draw a "Need Help?" link as well.
                help_string = _('Need Help?')
                w, new_height = dc.GetTextExtent(help_string)
                x, y = r.HCenterW(w), y + h * 1.5
                dc.DrawText(help_string, x, y)
                self._helplinkrect = wx.Rect(x, y, w, h)
                return

        try:
            del self._linkrect
            del self._helplinkrect
        except AttributeError: pass

    def set_root(self, root):
        return TreeList.set_root(self, root)

    def rename_selected(self):
        obj = self.SelectedItem
        if obj is not None:
            # check the action precondition
            if obj.rename_gui.action_allowed(obj):
                obj.rename_gui()

    def __onkey(self, e):
        c = e.KeyCode

        if c == wx.WXK_SPACE:
            self.RotateContact(not e.ShiftDown())
        elif c == wx.WXK_F2:
            self.rename_selected()
        elif c == wx.WXK_DELETE:
            self.delete_blist_item(self.SelectedItem)
        elif c in activate_keys:
            self.on_doubleclick()
        elif c == wx.WXK_HOME:
            self.SetSelection(0) if len(self.model) else None
        elif c == wx.WXK_END:
            self.SetSelection(len(self.model)-1) if len(self.model) else None
        else:
            e.Skip(True)

    def UpdateSkin(self):
        self.dragimgs = S(bar = skin.get('BuddiesPanel.Dragimages.Bar'), #TODO: stretch?
                          box = skin.get('BuddiesPanel.Dragimages.Box'))

        for renderer in self.renderers.itervalues():
            renderer.UpdateSkin()

        bg = skin.get('BuddiesPanel.Backgrounds.List', lambda: SkinColor(wx.WHITE))
        self.SetBackground(bg)

        self.RefreshAll()

    def update_renderers(self):
        import gui.buddylist.renderers as r

        self.UpdateSkin()

        contact_renderer = r.ContactCellRenderer(self)
        group_renderer   = r.GroupCellRenderer(self)
        search_renderer  = r.SearchCellRenderer(self)

        self.renderers.update(dict(Group          = group_renderer,
                                   DGroup         = group_renderer,
                                   SortGroup      = group_renderer,
                                   JabberContact  = contact_renderer,
                                   Contact        = contact_renderer,
                                   JabberResource = contact_renderer,
                                   YahooContact   = contact_renderer,
                                   MetaContact    = r.MetaContactCellRenderer(self),
                                   SearchEntry    = search_renderer,
                                   SearchOptionsEntry = r.SearchCellOptionsRenderer(self),
                                   SearchWebGroup = group_renderer))

    def dragon_allowed(self, i):
        'Is dragging on to the ith buddy allowed.'

        dragging = self.dragging_obj
        target = self.model[i]


        if isinstance(target, SpecialGroup):
            return False

        if isinstance(dragging, GroupTypes):
            return False

        from digsby import iswidget
        if iswidget(target):
            return False


        return True

    def on_middle_up(self, e):
        self.RotateContact(not e.ShiftDown())

    def RotateContact(self,forward = True):
        ib = self.infobox
        if forward:
            ib.SelectNext()
        else:
            ib.SelectLast()


    def _on_mousewheel(self, e):
        if e.RightIsDown():
            self._menu_ok = False
            ib = self.infobox
            rot = e.WheelRotation
            if rot < 0:
                ib.SelectNext()
            elif rot > 0:
                ib.SelectLast()
        else:
            # forward the mousewheel event to the infobox
            win = wx.FindWindowAtPointer()
            if isinstance(win, tuple(self.infobox_scrollers)):
                self.infobox.on_mousewheel(e)
            else:
                super(BuddyList, self)._on_mousewheel(e)

    def on_right_down(self, e):
        i = self.HitTest(e.Position)
        self.SetSelection(i)
        e.Skip()

    def on_context_menu(self, e):
        # ensure the selection is underneath the mouse cursor
        self.context_menu_event_selection(e)

        menu = self.context_menu
        menu.RemoveAllItems()

        i = self.GetSelection()

        if i != -1:
            obj = self.model[i]
            if hasattr(obj, '_disallow_actions'):
                return

            # The mouse is over a group or buddy
            import common.actions as actions
            actions.menu(self, self.model[i], self.context_menu)
        else:
            # The mouse is over an empty space in the buddylist
            #
            # Only show "Add Group" if you are connected to an IM account (other than Digsby)
            # OR if you have the "digsby.allow_add" preference set.
            if not any(x.allow_contact_add for x in profile.account_manager.connected_accounts):
                return

            from gui.protocols import add_group
            menu.AddItem(_('&Add Group'), callback = add_group)

        menu.PopupMenu()

    def context_menu_event_selection(self, e):
        # EVT_CONTEXT_MENU has .Position == (-1, -1) when caused by the keyboard
        # if that's not the case, and the mouse is over an item that isn't
        # selected, select it.
        if e and e.Position != (-1, -1):
            # watch out! EVT_RIGHT_DOWN's event.Position is in client coordinates
            # but EVT_CONTEXT_MENU gets screen coordinates (at least on windows)
            self.SetSelection(self.HitTest(self.ScreenToClient(e.Position)))

    def open_convo_with_selected( self ):
        'Opens a conversation window with the buddy currently selected.'

        i = self.GetSelection()
        if i != -1:
            obj = self.model[i]
            if self.can_chat(obj):
                chat_with(obj)
                self.infobox.DoubleclickHide()
                return True
            elif hasattr(obj, 'activate'):
                with traceguard:
                    obj.activate()
                return True

    def enter_window(self, e):
        if self.mouse_tracker:
            self.mouse_tracker.Start(10)

    def leave_window(self, e):
        if self.mouse_tracker:
            self.mouse_tracker.Stop()
        e.Skip()
        self.infobox.InvalidateDoubleclickHide()

    def can_chat(self, obj):
        return isinstance(obj, (Contact, MetaContact))

    def on_doubleclick(self, e = None):
        if not self.open_convo_with_selected():
            TreeList.on_doubleclick( self, e )

    activate_selected_item = on_doubleclick

    def expand_all(self):
        with self.save_selection():
            model = self.model
            isexp = model.is_expanded

            for i, obj in enumerate(model):
                if isinstance(obj, GroupTypes) and not isexp(i):
                    model.expand(obj)
                    return self.expand_all()

    def collapse_all(self):
        with self.save_selection():
            model = self.model
            isexp = model.is_expanded

            for i, obj in enumerate(model):
                if isinstance(obj, GroupTypes) and isexp(i):
                    model.collapse(obj)
                    return self.collapse_all()

    def on_left_down(self, e):
        self.drag_point = e.Position

        try:
            linkrect = self._linkrect
            helprect = self._helplinkrect
        except AttributeError:
            pass
        else:
            if linkrect.Contains(e.Position):
                import gui.pref.prefsdialog
                gui.pref.prefsdialog.show('accounts')
            elif helprect.Contains(e.Position):
                wx.LaunchDefaultBrowser(NEED_HELP_LINK)

        i = self.HitTest((e.GetX(), e.GetY()))

        if i == -1:
            self.SetSelection(-1)
            return e.Skip(True)

        if self.model.expandable(self[i]) and e.GetX() < 15:
            # If we're clicking a Group expander triangle, toggle the group
            # expansion but do not select.
            self.toggle_expand(self[i])
        else:
            self.SetSelection(i)
            e.Skip(True)

            self.infobox.quickshow=True
            self.infobox_hittest(e.Position)

    def motion( self, e=None ):
        'Invoked on mouse motion over the buddy list.'
        pos = None
        if e:
            e.Skip(True)
            pos = e.Position
        else:
            pos = self.Parent.ScreenToClient(wx.GetMousePosition())

        try:
            linkrect = self._linkrect
            helprect = self._helplinkrect
        except AttributeError:
            pass
        else:
            # If the cursor is over a custom drawn link show a hand
            if any(r.Contains(pos) for r in (linkrect, helprect)):
                self.SetCursor(StockCursor(CURSOR_HAND))
            else:
                self.SetCursor(StockCursor(CURSOR_ARROW))


        # Drag "distance" must be at least ten pixels
        if e and hasattr(self, 'drag_point') and e.LeftIsDown() and e.Dragging() \
            and _dist2(e.GetPosition(), self.drag_point) > 100:

            i = self.GetSelection()
            if i != -1 and i < len( self.model ):
                data = self.make_drag_data( self.model[i] )

                ds = BuddyListDropSource( self )
                ds.SetData( data )
                unused_result = ds.DoDragDrop( wx.Drag_AllowMove )
                self.hilite = None
                self.Refresh()
                self.dragging = False
        elif e and not e.LeftIsDown() and hasattr(self, 'drag_point'):
            del self.drag_point

        else:
            self.infobox_hittest(pos)

    show_infobox = prefprop('infobox.show')

    def infobox_hittest(self,pos):
        i = self.HitTest(pos)

        if i != -1:
            obj = self[i]
            if not isinstance(obj, GroupTypes):
                if self.show_infobox and isinstance(obj, (Contact, MetaContact)):
                    p  = self.Parent
                    pl = p.ClientToScreen(wx.Point(0, self.Position.y + self.GetItemY(i)))
                    pr = pl + wx.Point(p.Size.width, 0)
                    return self.infobox.Display(pl, pr, obj)

        # hide infobox when over search entries, or empty space
        self._hide_infobox()

    def _hide_infobox(self):
        if self.infobox.Shown:
            self.infobox.DelayedHide()
        else:
            self.infobox.Hide()


    def make_drag_data( self, blist_item ):
        data = wx.DataObjectComposite()

        import contacts.contactsdnd as contactsdnd
        contactsdnd.add_to_dataobject(data, blist_item)

        self.dragging_obj = blist_item
        return data

    def on_drop_buddylistitem( self, clist_obj ):
        if not getattr(self, 'hilite', None):
            return

        # hilite is a tuple of (area, index)
        area, _i, drop_to = self.hilite

        if area == 'below_group':
            area = 'below'

        if area == 'disallow': return
#        if self.model[i] is clist_obj: return # early exit for dropping to same

        from gui.searchgui import SearchEntry

        if isinstance(clist_obj, Contact):
            return self.on_drop_contact(clist_obj, area, drop_to)
        elif isinstance(clist_obj, MetaContact):
            return self.on_drop_metacontact(clist_obj, area, drop_to)
        elif isinstance(clist_obj, GroupTypes):
            return self.on_drop_dgroup(clist_obj, area, drop_to)
        elif isinstance(clist_obj, SearchEntry):
            return self.on_drop_search(clist_obj, area, drop_to)
        self.hilite = None

    def on_drop_dgroup(self, group, area, togroup):
        assert isinstance(togroup, GroupTypes),"dragging above or below something that isn't a group"
        assert area in ('above', 'below')
        profile.blist.rearrange_group(group, area, togroup)

    def on_drop_metacontact(self, clist_obj, area, drop_to):
        if isinstance(drop_to, GroupTypes):
            return self.on_drop_metacontact_dgroup(clist_obj, area, drop_to)
        elif isinstance(drop_to, MetaContact):
            return self.on_drop_metacontact_metacontact(clist_obj, area, drop_to)
        elif isinstance(drop_to, Contact):
            return self.on_drop_metacontact_contact(clist_obj, area, drop_to)

    def on_drop_metacontact_dgroup(self, clist_obj, area, drop_to):
        assert area in ('box', 'below')
        assert isinstance(clist_obj, MetaContact)
        blist = profile.blist
        if area == 'below':
            position = blist.DROP_BEGINNING
        else:
            position = blist.DROP_END
        blist.rearrange(clist_obj, area, drop_to, position)
        if not in_same_group(clist_obj, drop_to):
            clist_obj.move_to_group(drop_to.name)

    def do_relative_metacontact(self, clist_obj, area, drop_to):
        drop_group = self.model.parent_of(drop_to)
        profile.blist.rearrange(clist_obj, area, drop_group, drop_to)
        if not in_same_group(clist_obj, drop_group):
            clist_obj.move_to_group(drop_group.name)

    def on_drop_search(self, entry, area, drop_to):
        'rearrange search web items'
        from common.search import searches
        from common import setpref
        entry = entry.searchengine.dict()
        drop_to = drop_to.searchengine.dict()
        engines = [s.dict() for s in searches[:]]

        i = engines.index(entry)
        j = engines.index(drop_to) + (1 if area == 'below' else 0)

        if j > i: j -= 1

        if i != len(engines):
            engines.pop(i)
        engines.insert(j, entry)

        setpref('search.external', engines)

    def on_drop_metacontact_metacontact(self, clist_obj, area, drop_to):
        assert area in ('above', 'box', 'below')
        if area == 'box':
            contacts = list(drop_to) + list(clist_obj)
            diag = MetaContactDialog(self, contacts, metacontact = drop_to, title = _('Merge Contacts'),
                                     order = None)
            try:
                diag.Prompt(ondone = lambda *a, **k: clist_obj.explode(ask = False))
            finally:
                diag.Destroy()
        else:
            self.do_relative_metacontact(clist_obj, area, drop_to)

    def on_drop_metacontact_contact(self, clist_obj, area, drop_to):
        assert area in ('above', 'box', 'below')
        if area == 'box':
            contacts = [drop_to] + list(clist_obj)
            diag = MetaContactDialog(self, contacts, metacontact = clist_obj, title = _('Merge Contacts'),
                                     order = None)
            drop_group = self.model.parent_of(drop_to)
            def morelater(*a, **k):
                profile.blist.rearrange(clist_obj, 'above', drop_group, drop_to)
                if not in_same_group(clist_obj, drop_group):
                    clist_obj.move_to_group(drop_group.name)
            try:
                diag.Prompt(ondone = morelater)
            finally:
                diag.Destroy()
        else:
            self.do_relative_metacontact(clist_obj, area, drop_to)

    def delete_blist_item(self, item):

        if isinstance(item, Contact):
            from gui.protocols import remove_contact
            remove_contact(item, item.remove)
        elif isinstance(item, MetaContact):
            item.explode()
        elif isinstance(item, GroupTypes):
            from gui.protocols import remove_group
            remove_group(item, item.delete)

    def on_drop_contact(self, clist_obj, area, drop_to):
        if isinstance(drop_to, GroupTypes):
            return self.on_drop_contact_dgroup(clist_obj, area, drop_to)
        elif isinstance(drop_to, MetaContact):
            return self.on_drop_contact_metacontact(clist_obj, area, drop_to)
        elif isinstance(drop_to, Contact):
            return self.on_drop_contact_contact(clist_obj, area, drop_to)

    def on_drop_contact_dgroup(self, clist_obj, area, drop_to):
        assert area in ('box', 'below')
        assert isinstance(clist_obj, Contact)
        blist = profile.blist
        if area == 'below':
            position = blist.DROP_BEGINNING
        else:
            position = blist.DROP_END
        success = lambda *a: blist.rearrange(clist_obj, area, drop_to, position)
        if clist_obj not in drop_to:
            @callsback
            def do_move(result = None, callback = None):
                clist_obj.move_to_group(drop_to.name, callback = callback)
            do_move(success=success)
        else:
            success()

    def do_relative_contact(self, clist_obj, area, drop_to):
        drop_group = self.model.parent_of(drop_to)
        blist = profile.blist
        success = lambda *a: blist.rearrange(clist_obj, area, drop_group, drop_to)
        if clist_obj not in drop_group:
            @callsback
            def do_move(result = None, callback = None):
                clist_obj.move_to_group(drop_group.name, callback = callback)
            do_move(success=success)
        else:
            success()

    def on_drop_contact_metacontact(self, clist_obj, area, drop_to):
        assert area in ('above', 'box', 'below')
        if area == 'box':
            diag = MetaContactDialog.add_contact(self, drop_to, clist_obj, -1)
            diag.Prompt(ondone = lambda *a: None)
            diag.Destroy()
        else:
            self.do_relative_contact(clist_obj, area, drop_to)

    def on_drop_contact_contact(self, clist_obj, area, drop_to):
        assert area in ('above', 'box', 'below')
        if area == 'box':
            order = ('__meta__', 'above', self.model.parent_of(drop_to), drop_to)
            diag = MetaContactDialog(self, [drop_to, clist_obj], order = order )
            diag.Prompt(ondone = lambda *a: None)
            diag.Destroy()
        else:
            self.do_relative_contact(clist_obj, area, drop_to)

    def get_feedback(self, clientPt):
        # Percent will be the percentage of vertical space the cursor has
        # passed over the item it's on.
        i, percent = self.hit_test_ex( clientPt )
        dragging   = self.dragging_obj
        drop_to    = self.model[i]
        if i == -1:
            # We must be dragging off into the "void" below the
            # buddylist: put it below the last item.
            i = len(self.model)-1
            percent = 1
            parent_percent = ('foo', 1)
        else:
            parent_percent = self.hit_test_parent( clientPt )

        from .buddylistrules import target, feedback
        new_to, position = target(self.model, dragging, drop_to, i, percent, parent_percent)
        feedback_result =  feedback(self.model, dragging, new_to, position)
        return new_to, feedback_result

    def GiveFeedback(self, effect, dragsource):
        'Logic for drawing drag and drop indication marks.'

        mousepos = wx.GetMousePosition()
        clientPt = self.ScreenToClient( mousepos )
        new_to, feedback_result = self.get_feedback(clientPt)

#        ITEM_BOX    = 'box'
#        GROUP_BOX   = 'group_box'
#        ABOVE       = 'above'
#        BELOW       = 'below'
#        BELOW_GROUP = 'below_group'
#        DISALLOW    = 'disallow'

        if feedback_result == 'group_box':
            feedback_result = 'box'
#        if feedback_result == 'below_group':
#            feedback_result = 'below'

#        if feedback_result not in ('above', 'below', 'box'):
#            feedback_result = None

        old_hilite = self.hilite
        if feedback_result is not None:
            self.hilite = (feedback_result, self.model.index_of(new_to), new_to)
        else:
            self.hilite = None

        # Is there a better way to do this? Keep track of previous mouse
        # positions, perhaps?

#        if self.hilite is not None:
#            area, i, drop_to = self.hilite
#            if area == 'disallow':
#                dragsource.SetCursor(effect, wx.StockCursor(wx.CURSOR_NO_ENTRY))
#            else:
#                dragsource.SetCursor(effect, wx.StockCursor(wx.CURSOR_COPY_ARROW))

        # only refresh lines that need it
        if self.hilite != old_hilite:
#            print self.hilite, old_hilite
#            print [old_hilite[1] if old_hilite else -1, self.hilite[1] if self.hilite else -1]
            hilites = filter(lambda a: a!=-1, [old_hilite[1] if old_hilite else -1, self.hilite[1] if self.hilite else -1])
            i, j = min(hilites), max(hilites)
            self.RefreshLines(max(0, i-1), min(self.GetItemCount()-1, j+1))
            if old_hilite and old_hilite[0] == 'below_group':
                if self.model.is_expanded(old_hilite[1]):
                    self.RefreshLine(old_hilite[1] + len(old_hilite[2]))
            if self.hilite and self.hilite[0] == 'below_group':
                if self.model.is_expanded(self.hilite[1]):
                    self.RefreshLine(self.hilite[1] + len(self.hilite[2]))

        self.dragResult = wx.DragNone if not self.hilite or self.hilite[0] == 'disallow' else wx.DragMove

        return False

    def search(self, search_string):
        self.fallback_selection = 1
        profile.blist.search(search_string, self._on_search_cb)

    def _on_search_cb(self, results):
        # results is num contacts in (prevSearch, thisSearch)
        # if we went from finding no contacts to finding some contacts, select the first one.
        prev, this = results
        if prev == -1 and this > 0:
            wx.CallAfter(self.SetSelection, 1)

    def clear_search(self):
        profile.blist.search('')

class BuddyListDropTarget(wx.PyDropTarget):

    VELOCITY = 70

    def __init__(self, list):
        wx.PyDropTarget.__init__(self)

        self.list = list
        self.lasttick = None
        self.CreateNewDataObject()

    def OnEnter(self, x, y, d):
        return self.list.dragResult

    def OnLeave(self):
        self.lasttick = None

    def OnDrop(self, x, y):
        lasttick = None

        return True

    def OnDragOver(self, x, y, d):
        blist = self.list

        listrect = wx.RectS(blist.Size)
        mp = wx.Point(x,y)

        topdif = mp.y - listrect.y
        botdif = listrect.bottom - mp.y

        if topdif < 7 or botdif < 7:
            if self.lasttick is None:
                self.lasttick = default_timer()

            now = default_timer()

            toscroll = int((now - self.lasttick) * self.VELOCITY)

            if toscroll >= 1:
                self.lasttick = now

                if topdif < 5:
                    blist.ScrollLines(-toscroll)
                elif botdif < 5:
                    blist.ScrollLines(toscroll)
        else:
            self.lasttick = None

        return blist.dragResult

    def CreateNewDataObject(self):
        self.dragged = wx.DataObjectComposite()

        # This drop target will receive certain types of draggable objects.
        import contacts.contactsdnd as cdnd
        drag_types = dict(
            file   = wx.FileDataObject(),
            buddy  = cdnd.dataobject(),
            text   = wx.TextDataObject(),
            bitmap = wx.PyBitmapDataObject() )

        # For easy access, like self.dragged.file
        for dt, dobj in drag_types.iteritems():
            setattr(self.dragged, dt, dobj)

        # Add to the wx.DataObjectComposite item, and set as our data object.
        for v in drag_types.itervalues(): self.dragged.Add(v)
        self.SetDataObject(self.dragged)

    def OnData(self, x, y, drag_result):
        "Called when OnDrop returns True. Get data and do something with it."

        with traceguard:
            self.GetData()     # Copies data from drag source to self.dragging
            dragged = self.dragged

            dropped = S(files  = dragged.file.GetFilenames(),
                        bitmap = dragged.bitmap.GetBitmap(),
                        text   = dragged.text.GetText())

            if dropped.files:
                i, unused_percent = self.list.hit_test_ex(wx.Point(x,y))
                if i != -1:
                    obj = self.list.model[i]

                    # open a "send files" confirmation
                    from common import caps
                    obj = getattr(obj, 'file_buddy', obj) #metacontact

                    @wx.CallAfter # so that we don't block the Drag and Drop
                    def later():
                        if hasattr(obj, 'send_file') and caps.FILES in obj.caps:
                            window = self.list.Top
                            window.Raise()

                            from gui.contactdialogs import send_files
                            send_files(window, obj, dropped.files)
                        else:
                            msg = _("This buddy can't accept file transfers")
                            wx.MessageBox(msg, _("Send File"))

            if dropped.bitmap:
                print dropped.bitmap
                print dir(dropped.bitmap)
                return drag_result
            if dropped.text:
                #print 'Dropped Text (%s)' % dropped.text
                pass

        if getattr(self.list, 'dragging_obj', None) is not None:
            self.list.on_drop_buddylistitem( self.list.dragging_obj )

        del self.dragged
        self.CreateNewDataObject()

        return drag_result


def _dist2(one, two):
    'Distance squared between two points.'

    return (one.x - two.x) ** 2 + (one.y - two.y) ** 2

def in_same_group(clist_obj, drop_group):
    groups = clist_obj.manager[clist_obj.id].groups
    return (drop_group.name.lower(),) in (tuple([i[0].lower()] + list(i[1:])) for i in groups)

ismeta    = lambda obj: isinstance(obj, MetaContact)

def find_group(model, obj):
    if isinstance(obj, GroupTypes):
        drop_group = obj
    else:
        parent = model.parent_of(obj)
        if isinstance(parent, MetaContact):
            drop_group = model.parent_of(parent)
        else:
            drop_group = parent

    return drop_group


class BuddyListDropSource(wx.DropSource):
    def __init__( self, list ):
        wx.DropSource.__init__(self, list)
        self.SetCursor(wx.DragNone, wx.StockCursor(wx.CURSOR_NO_ENTRY))
        self.SetCursor(wx.DragMove, wx.StockCursor(wx.CURSOR_COPY_ARROW))
        self.list = list

    def GiveFeedback(self, effect):
        return self.list.GiveFeedback(effect, self)

def fill_menu(menu, actions):
    for action_id, label in actions:
        menu.AddItem(label, id=action_id)

def chat_with(obj):
    import gui.imwin

    mode = 'im'
    if pref('conversation_window.open_email_for_offline', False):
        if not obj.online:
            mode = 'email'

    wx.CallAfter(gui.imwin.begin_conversation, obj, mode = mode)

GroupActions = [
    (actionIDs.AddContact,      _('&Add Contact')),
    (actionIDs.RenameSelection, _('&Rename Group')),
    (actionIDs.DeleteSelection, _('&Delete Group')),
    (actionIDs.AddGroup,        _('Add &Group')),
]

