from __future__ import with_statement
import wx, gc, sys

from weakref import ref
from inspect import currentframe
from types import FrameType

from util.primitives.refs import better_ref_types
from logging import getLogger; log = getLogger('gcutil')

import locale
enc = locale.getpreferredencoding()

SET_AS_ROOT   = wx.NewId()
SET_SHELL_OBJ = wx.NewId()
NEW_GCTREE    = wx.NewId()
DELETE        = wx.NewId()

custom_reprs = {
    FrameType: lambda f: '%r for %r' % (f, f.f_code)
}

weak = (ref, better_ref_types)

def nameof(obj):
    '''
    if obj is referenced strongly in another object's __dict__, give its attribute name.
    '''

    for r in gc.get_referrers(obj):
        for r2 in gc.get_referrers(r):
            if r is getattr(r2, '__dict__', object()):
                for k, v in r.iteritems():
                    if v is obj:
                        return '[%r attribute of %r]' % (k, r2)

def isweak(obj):
    return isinstance(obj, weak)

class gctree_ref(ref):
    def __init__(self, obj, cb = None):
        ref.__init__(self, obj, cb)

def deref(wr):
    return wr() if isinstance(wr, gctree_ref) else wr

def repritem(i):
    from util import funcinfo
    try:
        if type(i) in custom_reprs:
            return custom_reprs[type(i)](i)
        repr_txt = unicode(repr(i)).decode(enc, 'replace')[:300]

        if repr_txt.startswith('<function <lambda> at'):
            repr_txt = funcinfo(i)
        else:
            repr_txt = repr(i.__class__) + ': ' + repr_txt

    except Exception: # (UnicodeDecodeError, UnicodeEncodeError, wx.PyDeadObjectError):
        return '<%s at %x>' % (type(i).__name__, id(i))

    return repr_txt

def makeref(obj):
    try:
        return gctree_ref(obj)
    except TypeError, e:
        if repr(e).find('cannot create weak reference to') != -1:
            return obj
        raise

class colors:
    cycle = wx.Color(128, 128, 128)   # gray
    weakref = wx.Color(80, 170, 80) # green
    root = wx.Color(255, 0, 0)        # red

class LazyTree(wx.TreeCtrl):
    def __init__(self, parent, root = None):
        super(LazyTree, self).__init__(parent)

        Bind = self.Bind
        Bind(wx.EVT_TREE_ITEM_EXPANDING,  self.OnExpandItem)
        Bind(wx.EVT_TREE_ITEM_COLLAPSING, self.OnCollapseItem)
        Bind(wx.EVT_TREE_ITEM_MENU,       self.OnTreeMenuItem)
        Bind(wx.EVT_RIGHT_DOWN,           self.OnRightDown)
        Bind(wx.EVT_MENU,                 self.OnMenu)
        Bind(wx.EVT_KEY_DOWN,             self.OnKeyDown)

        self.__collapsing = False

        self.getChildren = gc.get_referrers

        if root is not None:
            self.setroot(root)

    def setfunc(self, func):
        self.getChildren = func
        self.setroot(deref(self.rootref))


    def setroot(self, root):
        self.DeleteAllItems()

        rootId = self.AddRoot(repritem(root))
        self.SetPyData(rootId, makeref(root))
        self.SetItemHasChildren(rootId)
        self.rootref = makeref(root)

    def OnRightDown(self, e):
        item, area = self.HitTest(e.Position)
        self.SelectItem(item)
        e.Skip()

    def OnKeyDown(self, e):
        if e.KeyCode == wx.WXK_DELETE:
            self.Delete(self.GetSelection())
        else:
            e.Skip()

    def OnExpandItem(self, event):
        parentItem = event.Item
        wr = self.GetPyData(parentItem)
        parent = deref(wr)

        if parent is None: return

        curframe = currentframe()

        count    = 0

        for child in self.getChildren(parent):
            childStr = repritem(child)

            if child is parent:
                continue

            if 'gcutil' in childStr and 'OnExpandItem' in childStr:
                # this is basically a hack to keep THIS frame object out of the list
                continue

            if type(child).__module__.startswith('guppy.'):
                continue

            childItem = self.AppendItem(parentItem, childStr)
            self.SetPyData(childItem, makeref(child))

            if self.IsCycle(childItem):
                self.SetItemTextColour(childItem, colors.cycle)
            elif isweak(child):
                self.SetItemTextColour(childItem, colors.weakref)
                self.SetItemHasChildren(childItem, True)
            else:
                self.SetItemHasChildren(childItem, True)

            count += 1


        if count == 1:
            # automatically expand parents with one child
            self.Expand(childItem)
        elif count == 0:
            # parent didn't have any children
            self.SetItemHasChildren(parentItem, False)

    def IsCycle(self, item):
        GetItemParent = self.GetItemParent
        GetPyData     = self.GetPyData

        def GetPyData(item, get_data = self.GetPyData):
            return deref(get_data(item))

        obj = GetPyData(item)

        while True:
            item = GetItemParent(item)

            if not item.Ok():
                break

            if GetPyData(item) is obj:
                return True

        return False

    def OnCollapseItem(self, event):
        if self.__collapsing: # CollapseAndReset may trigger COLLAPSING event
            return event.Veto()

        self.__collapsing = True
        item = event.Item
        self.CollapseAndReset(item)
        self.SetItemHasChildren(item)
        self.__collapsing = False

    def OnTreeMenuItem(self, e):
        m = wx.Menu()

        m.Append(NEW_GCTREE, 'New GCTree with this object')
        m.Append(SET_AS_ROOT, 'Set as Root')

        if hasattr(wx.GetApp(), 'shell_locals'):
            m.Append(SET_SHELL_OBJ, 'Set in Shell as "obj"')

        m.AppendSeparator()
        m.Append(DELETE, 'Delete')

        self.PopupMenu(m)

    def OnMenu(self, e):
        obj = self.GetPyData(self.GetSelection())
        i = e.Id

        if i == SET_AS_ROOT:
            self.setroot(obj)
        elif i == SET_SHELL_OBJ:
            wx.GetApp().shell_locals.update(obj = obj)
        elif i == NEW_GCTREE:
            gctree(makeref(obj))
        elif i == DELETE:
            self.Delete(self.GetSelection())
        else:
            assert False

class GCInfoPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.Sizer = s = wx.FlexGridSizer(0, 2, 5, 5)

        rows = [('__repr__',        repritem),
                ('Reference Count', sys.getrefcount),
                ('referrers',       lambda obj: len(gc.get_referrers(obj)))]

        if hasattr(sys, 'getsizeof'):
            rows.extend([
                ('Size',            sys.getsizeof)
            ])

        self.ctrls = []

        for label, func in rows:
            s.Add(wx.StaticText(self, -1, label))
            ctrl = wx.StaticText(self, -1, '')
            s.Add(ctrl)
            self.ctrls.append((ctrl, func))

    def set_object(self, obj):
        for ctrl, func in self.ctrls:
            try:
                ctrl.Label = str(func(obj))
            except Exception, e:
                ctrl.Label = str(e)

        self.Layout()

class GCTreeFrame(wx.Frame):
    def __init__(self, item):
        size =  wx.Size(1000, 600)
        wx.Frame.__init__(self, None, name = 'GCTreeFrame', size = size)

        #from gui.toolbox import persist_window_pos
        #persist_window_pos(self)

        split = wx.SplitterWindow(self, style = wx.SP_LIVE_UPDATE)
        self.gcinfopanel = GCInfoPanel(split)

        tree = LazyTree(split, item)

        def OnSelection(e):
            tree_item = e.Item
            if tree_item:
                wr = tree.GetPyData(tree_item)

                self.gcinfopanel.set_object(deref(wr))

        tree.Bind(wx.EVT_TREE_SEL_CHANGED, OnSelection)

        self.SetTitle(repritem(item))

        split.SetSashGravity(1)
        split.SetMinimumPaneSize(100)
        split.SplitVertically(tree, self.gcinfopanel)
        wx.CallAfter(lambda: split.SetSashPosition(size.width - 250))

        panel = wx.Panel(self)

        b1 = wx.RadioButton(panel, -1, 'refer&rers')
        b2 = wx.RadioButton(panel, -1, 'referen&ts')

        def onradio(e, itemref = makeref(item)):
            func = gc.get_referrers if e.EventObject is b1 else gc.get_referents
            tree.setfunc(func)

        self.Bind(wx.EVT_RADIOBUTTON, onradio)
        self.Bind(wx.EVT_CLOSE, self.__onclose)

        b1.SetValue(True)

        b1.SetToolTipString(gc.get_referrers.__doc__)
        b2.SetToolTipString(gc.get_referents.__doc__)

        s2 = panel.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        s2.AddMany([(5, 10),
                    (b1, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL),
                    (10, 20),
                    (b2, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL),
                    ])


        s = wx.BoxSizer(wx.VERTICAL)
        s.AddMany([(split, 1, wx.EXPAND),
                   (panel, 0, wx.EXPAND)])

        self.Sizer = s
        s.Layout()

    def __onclose(self, e):
        self.Destroy()
        wx.CallAfter(collect_garbage)

    def onradio(self):
        pass

def collect_garbage():
    # also clear sys.last_XXX values set by the interactive console; they can
    # maintain references indirectly to a lot of objects
    sys.last_traceback, sys.last_value, sys.last_type = None, None, None
    gc.collect()

def gctree(obj):
    collect_garbage()
    GCTreeFrame(obj).Show()

try:
    import sip
except ImportError:
    pass
else:
    def leaked():
        collect_garbage()
        import util
        return (o for o in util.uncollectable(sip.wrapper) if sip.isdeleted(o))

def count(identifier):
    collect_garbage()
    if isinstance(identifier, basestring):
        obj_gen = byclassname(identifier)
    else:
        obj_gen = byclass(identifier)

    return sum(1 for o in obj_gen)

def byclass(cls):
    collect_garbage()
    return (o for o in gc.get_objects() if isinstance(o, cls))

def byclassname(classname):
    collect_garbage()
    return (o for o in gc.get_objects() if type(o).__name__ == classname)

def last(gen):
    gen = iter(gen)
    while True:
        i = None
        try:
            i = gen.next()
        except StopIteration:
            return i

def newest(classname):
    return last(byclassname(classname))

def byaddress(addr):
    objs = [o for o in gc.get_objects() if id(o) == addr]
    if objs:
        if len(objs) == 1:
            return objs[0]
        else:
            raise AssertionError('found more than one object at that address: %r' % objs)


if __name__ == "__main__":
    from tests.testapp import testapp
    import gui.native.helpers

    a = 5
    b = ['some items', a]
    c = [b, 'some other items']

    app = testapp('../../')
    frame = GCTreeFrame(c)
    frame.Show()
    app.MainLoop()
