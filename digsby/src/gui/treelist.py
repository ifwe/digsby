"""

treelist.py

makes

- a
  - tree
    - of
  - items

into

- a
- list
- of
- items

"""
from __future__ import with_statement
from __future__ import division


app = None

import wx
from wx import WXK_LEFT, WXK_RIGHT, WXK_DOWN, WXK_UP, Rect
from util.primitives.funcs import Delegate
from logging import getLogger; log = getLogger('treelist'); info = log.info
from gui.textutil import GetFontHeight,default_font
from contextlib import contextmanager

# Determines equality of parents in list (group identity)
expanded_id = lambda obj: u'_'.join([type(obj).__name__, obj.name])

# Determines equality of objects in list (for maintaining things like selection)
idfunc = lambda obj: obj.__hash__()

def hasChildren( obj ):
    '''
    Returns True if
    1) obj has __iter__ OR
    2) obj has __len__ and __getitem__
    '''
    try: iter(obj)
    except: return False
    else: return True

class ListMixin(object):
    '''
    Mixin this class to let a list member variable be exposed as list methods
    in the class object.
    '''
    def __init__(self, listAttrName):
        self._listAttrName = listAttrName

    # act as an iterable list
    def __len__( self ):        return len( self.__dict__[self._listAttrName] )
    def __iter__( self ):       return self.__dict__[self._listAttrName].__iter__()
    def __getitem__( self, n ): return self.__dict__[self._listAttrName][n]

class TreeListModel(ListMixin):
    '''
    Given a list of lists, provides a flattened view of that list for use in a
    hierarchial list.

    Parents are included, so a list object appears before it's children.

    Example:

    >>> model = TreeListModel(["my group", ["sub", "children"], [["elem1", "elem2"], "thing"]])
    >>> print self.model[2]

    'sub'

    '''

    def __init__( self, root = None, collapsed = None):
        self.root = root or []
        self.collapsed = set(collapsed) if collapsed is not None else set()
        self.flattened_list = []
        self.listeners = []
        self.depths = {}
        self.filters = []
        self.donotexpand = []
        self._expandable_cache = {}

        self.update_list()
        self.expansion_state_changed = Delegate()

        # access this object (specifically, the flattened_list member) as a list
        ListMixin.__init__(self, 'flattened_list')


    def _expandable(self, eltype):
        try:
            return self._expandable_cache[eltype]
        except KeyError:
            for i in self.donotexpand:
                if issubclass(eltype, i):
                    return self._expandable_cache.setdefault(eltype, False)

            return self._expandable_cache.setdefault(eltype, True)

    def expandable(self, el):
        return self._expandable(el.__class__)

    def flatten( self, root, collapsed, depths, depth=0, filters=[], expanded_id = expanded_id ):
        '''
        Flatten a list of objects. Parent objects are "included."

        Parameters:

        expanded - a hash of {repr(obj): boolean} pairs representing whether or not
                   parent items should be traversed.
        depths -   is a hash to store {obj: integer} depth values for
        depth -    depth to begin at (defaults to zero)
        '''
        lst = [root]

        if hasChildren( root ):
            for el in root:
                depths[idfunc(el)] = (depth, root)
                if expanded_id(el) not in collapsed and self.expandable(el):
                    lst.extend( self.flatten( el, collapsed, depths, depth+1, filters, expanded_id = expanded_id ) )
                else:
                    lst.append( el )

        return lst

    def __repr__(self):
        return '<TreeListModel %r>' % self.flattened_list

    def expand( self, obj ):
        i = expanded_id(obj)
        self.collapsed.discard(i)
        self.expansion_state_changed()
        self.update_list()

    def collapse( self, obj ):
        self.collapsed.add(expanded_id(obj))
        self.expansion_state_changed()
        self.update_list()

    def toggle_expand( self, obj ):
        if obj.__class__ not in self.donotexpand:
            if expanded_id(obj) not in self.collapsed:
                self.collapse( obj )
            elif hasChildren( obj ):
                self.expand( obj )

    def is_expanded( self, n ):
        'Returns True if the nth element is currently expanded.'

        return expanded_id(self.flattened_list[n]) not in self.collapsed

    def parent_of(self, child):
        return self.depths[idfunc(child)][1]

    def index_of(self, child):
        'Returns the index of the specified child.'

        try:
            return self.indices[idfunc(child)] if idfunc(child) in self.indices else -1
        except:
            return -1

    def set_root(self, root):
        self.depths = {}
        self.root = root
        self.update_list()

    def update_list(self):
        assert wx.IsMainThread()

        self.flattened_list = self.flatten(self.root, self.collapsed, self.depths, filters = self.filters)[1:]

        # cache indices
        self.indices = dict((idfunc(item), c) for c, item in enumerate(self.flattened_list))

        for l in self.listeners:
            l.list_changed()

    def remove_child(self, child):
        assert child in self.flattened_list
        parent = self.depths[idfunc(child)][1]
        assert child in parent
        parent.remove(child)
        assert child not in parent
        self.update_list()


from cgui import SkinVList as TreeListBase

class TreeList(TreeListBase):
    '''
    Hierarchial list control.

    Usage:

    frame = wx.Frame(None, -1, 'Test')
    model = TreeListModel( [ ["lists", "of"], [ ["things", "go"], "here" ] ] )
    list  = TreeList( frame, model )
    '''

    def __init__(self, parent, model, id=-1, style = wx.NO_BORDER | wx.FULL_REPAINT_ON_RESIZE | wx.HSCROLL | wx.VSCROLL,
                 enable_hover = True, keyhandler = None):
        self.renderers = {}
        self.renderers_cache = {}

        self.context_menu_handlers = {}

        TreeListBase.__init__(self, parent, id, style)

        self.model = model
        model.listeners.append( self )

        measure = self.OnMeasureItem

        self.SetHeights([measure(n) for n in xrange(len(self.model))])

        Bind = self.Bind
        Bind(wx.EVT_LISTBOX_DCLICK, self.on_doubleclick)
        Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        if keyhandler is not None:
            Bind(wx.EVT_KEY_DOWN, keyhandler)
        Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.hoveridx = -1

        if enable_hover:
            Bind(wx.EVT_MOTION, self.on_motion)
            Bind(wx.EVT_LEAVE_WINDOW, self.on_leave_window)

        # the amount to indent each group level by
        self.indent = 10

    #
    # Hover Property
    #

    def on_leave_window(self, e):
        self.Hover = -1
        e.Skip(True)

    def on_motion(self, e):
        self.Hover = self.HitTest(e.Position)
        e.Skip(True)

    def toggle_expand(self, obj):
        '''
        Expand or collapse a treelist item.

        If the selection is a child of a collapsing item, the selection
        is moved to the collapsing item.
        '''

        i, model = self.GetSelection(), self.model
        selected = self.model[i]
        do_select = False

        if i != -1:
            try:
                parent = self.GetParent(model[i])
            except KeyError:
                pass
            else:
                p = model.index_of(parent)
                if parent is obj and model.is_expanded(p):
                    self.SetSelection(p)
                else:
                    do_select = True

        self.model.toggle_expand(obj)
        if do_select:
            self.SetSelection(model.index_of(selected), keepVisible = False)

    def GetItemRect(self, item, include_children = True):
        '''
        Return a rectangle (in client coordinates) for the given item.

        If include_children is True (default) children items will be included
        in the rectangle calculation.
        '''

        if not include_children:
            return TreeListBase.GetItemRect(self, self.model.index_of(item))

        model    = self.model
        modellen = len(self.model)
        measure  = self.OnMeasureItem

        i    = model.index_of(item)
        rect = Rect(0, self.GetItemY(i), self.ClientRect.width, measure(i))

        if include_children:
            i += 1
            while i < modellen and self.GetParent(model[i]) is item:
                rect.height += measure(i)
                i += 1

        return rect

    #
    # Hover Property
    #

    def get_hover(self):
        return self.hoveridx

    def set_hover(self, i):
        old = self.hoveridx
        self.hoveridx = i

        if i != old:
            if old != -1:
                self.RefreshLine(old)

            if i != -1:
                self.RefreshLine(i)

    Hover = property(get_hover, set_hover)

    def GetSelectedItem(self):
        i = self.GetSelection()
        if i != -1:
            try:
                return self.model[i]
            except IndexError:
                pass

    SelectedItem = property(GetSelectedItem)

    def __getitem__(self, i):
        return self.model[i]

    def GetParent(self, obj):
        return self.model.parent_of(obj)

    @contextmanager
    def save_selection(self):
        i, elem, model = self.GetSelection(), None, self.model
        if i != - 1:
            try:
                elem = model[i]
            except IndexError:
                elem = None

        try:
            yield
        finally:
            if elem is None:
                sel = -1
            else:
                sel = model.index_of(elem)

            if sel == -1:
                if hasattr(self, 'fallback_selection'):
                    sel = self.fallback_selection
                    del self.fallback_selection

            TreeList.SetSelection(self, sel, False)

    def set_root(self, root):
        with self.save_selection():
            self.renderers_cache = {}
            self.model.set_root(root)

    def on_key_down(self, e):
        i, model = self.GetSelection(), self.model

        keycode, modifiers = e.KeyCode, e.Modifiers

        try:
            obj = self.model[i]
        except IndexError:
            obj = None

        # Right and left keys affect group expansion.
        if keycode == WXK_LEFT:
            if modifiers == wx.MOD_SHIFT:
                self.collapse_all()
            elif obj is not None and modifiers == wx.MOD_NONE:
                if model.expandable(obj) and model.is_expanded( i ):
                    # left arrow on expanded item collapses it
                    self.toggle_expand( obj )
                else:
                    # left arrow on child item moves selection to its parent
                    self.select_parent(obj)

        elif keycode == WXK_RIGHT:
            if modifiers == wx.MOD_SHIFT:
                self.expand_all()
            elif obj is not None and modifiers == wx.MOD_NONE:
                if model.expandable(obj):
                    if not model.is_expanded( i ):
                        self.toggle_expand( obj )
                    elif i+1 < self.GetItemCount() and self.GetParent(model[i+1]) is obj:
                        self.SetSelection(self.GetSelection() + 1)

        elif keycode == WXK_UP:
            sel = self.GetSelection() - 1
            if sel >= 0: self.SetSelection(sel)

        elif keycode == WXK_DOWN:
            sel = self.GetSelection() + 1
            if sel < self.GetItemCount(): self.SetSelection(sel)

        elif keycode == wx.WXK_PAGEUP:
            self.PageUp()
            self.SetSelection(self.GetFirstVisibleLine())

        elif keycode == wx.WXK_PAGEDOWN:
            self.PageDown()
            self.SetSelection(self.GetFirstVisibleLine())

        else:
            e.Skip(True)

    def select_parent(self, obj):
        'Given a list item, selects its parent.'

        parent = self.GetParent(obj)
        if parent is not None:
            i = self.model.index_of(parent)
            if i != -1:
                self.SetSelection(i)

    def renderer_for(self, obj):
        try: k = obj._renderer
        except AttributeError:
            try: k = obj.__class__.__name__
            except AttributeError:
                k = None

        return self.renderers.get(k, None)

    def renderer_for_index(self, n):
        try:
            renderer = self.renderers_cache[n]
        except KeyError:
            renderer = self.renderers_cache[n] = self.renderer_for(self.model[n])

        return renderer



    hit_test_ex = lambda self, pt, h = TreeListBase.HitTestEx: h(self, *pt)

    # some fake triangles used in the default drawing behavior for a TreeList
    collapsedTri, expandedTri = [(0, 0), (7, 3), (0, 7)], [(0, 0), (7, 0), (3, 3)]

    def hit_test_parent(self, mouse_pos):
        'Returns the parent index and percent.'

        model = self.model
        i, unused_percent = self.hit_test_ex(mouse_pos)

        # mouse is not over anything
        if i == -1:
            return -1, None

        parent = model.parent_of(model[i])
        j      = model.index_of(parent)

        if j != -1:
            rect = self.GetItemRect(parent)
            i = j
        else:
            rect = self.GetItemRect(model[i])


        percent = (mouse_pos.y - rect.y) / rect.height
        return i, percent

    def default_draw(self, dc, rect, n):
        '''
        If a subclass has not provided a "better" way to draw this item, use
        a default method of drawing here--which is just to str(the object) and
        draw an exapander arrow if the object is iterable.
        '''
        # decide on a text color
        if self.IsSelected( n ): fg = wx.SYS_COLOUR_HIGHLIGHTTEXT
        else: fg = wx.SYS_COLOUR_WINDOWTEXT
        dc.SetTextForeground( wx.SystemSettings_GetColour( fg ) )

        # use GUI font
        font = default_font()
        dc.SetFont( font )

        # choose an expanded or collapsed triangle
        if self.model.is_expanded( n ): tri = self.expandedTri
        else: tri = self.collapsedTri

        # triangles will be black
        dc.SetPen( wx.BLACK_PEN )
        dc.SetBrush( wx.BLACK_BRUSH )

        obj = self.model[n]
        xoffset = self.indent * self.model.depths[idfunc(obj)][0]

        yy = rect.y + (rect.height / 2) - (3)
        if hasattr(obj, 'expandable'):
            if obj.expandable():
                dc.DrawPolygon( [( x+rect.x + xoffset, y+yy ) for ( x, y ) in tri] )
        else:
            if hasChildren( obj ):
                dc.DrawPolygon( [( x+rect.x + xoffset, y+yy ) for ( x, y ) in tri] )

        icon = getattr(obj, 'icon', None)
        x = rect.x + 20 + xoffset
        if icon:
            dc.DrawBitmap(icon, rect.x+20, rect.y + (rect.Height / 2 - icon.GetHeight() / 2 ))
            x += icon.GetWidth() + 10

        dc.DrawText( unicode(obj), x, rect.y + (rect.Height / 2 - GetFontHeight(font, dc) / 2) )

    def OnMeasureItem( self, n ):
        'Returns the size of the nth item.'

        renderer = self.renderer_for_index(n)

        if renderer:
            return renderer.item_height(self.model[n])
        else:
            return getattr(self.model[n], 'ItemHeight', 20)

    def OnDrawBackground(self, dc, rect, n, selected = None):

        obj      = self.model[n]
        selected = self.IsSelected(n) if selected is None else selected
        renderer = self.renderer_for_index(n)

        try:
            drawbg = renderer.draw_background
        except AttributeError:
            try:
                return obj.OnDrawBackground(dc, rect, n, selected)
            except AttributeError:
                return TreeListBase.OnDrawBackground(self, dc, rect, n)
        else:
            drawbg(obj, dc, rect, n, selected, self.Hover == n)


    def OnDrawItem( self, dc, rect, n):
        'Called for each item.'

        model = self.model
        obj   = model[n]
        selected = self.IsSelected(n)

        # How many levels deep is this element?
        try:
            depthVal = model.depths[idfunc(obj)][0]
        except KeyError:
            log.warning('KeyError in TreeList.OnDrawItem: %r', obj)
            return 1

        draw_args = dict(
            dc    = dc,
            rect  = rect,
            depth = depthVal,
            obj   = obj,
            index = n,
            expanded = model.is_expanded(n),
            selected = selected, #self.IsSelected(n),
            hover = self.Hover == n,
        )

        renderer = self.renderer_for_index(n)

        if renderer:
            renderer.Draw(**draw_args)
        else:
            self.default_draw(dc, rect, n)

    def list_changed( self ):
        measure = self.OnMeasureItem
        self.SetHeights([measure(n) for n in xrange(len(self.model))])

    def SetSelection(self, i, keepVisible=True):
        TreeListBase.SetSelection(self, i, keepVisible)

    #
    # mouse events
    #

    def on_doubleclick( self, e ):
        'Double click on a tree: expand the tree item.'

        if e: e.Skip(True)
        i = self.GetSelection()
        if i != -1:
            self.toggle_expand( self.model[i] )

    def on_right_down(self, e):
        """
        This is to provide slightly more native behavior--a right click down
        means select an item. This does not prevent a popup.
        """
        i = self.HitTest((e.GetX(), e.GetY()))
        self.SetSelection(i)
        e.Skip(True)
