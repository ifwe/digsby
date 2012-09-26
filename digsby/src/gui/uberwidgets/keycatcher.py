'''

A simpler interface than wxAcceleratorTable (which is immutable, unexplainably)
for binding and unbinding keyboard shortcuts.

'''

import wx
from collections import defaultdict
from util.primitives.funcs import Delegate

from gui.input import keycodes


# unique id pool since there are a limited amound

_ids = set()

def MyNewId():
    global _ids
    return wx.NewId() if not len(_ids) else _ids.pop()

def ReleaseIds(ids):
    global _ids
    _ids.update(ids)


class KeyCatcher(wx.EvtHandler):
    def __init__(self, frame):
        frame.Bind(wx.EVT_MENU, self._oncommandevent)

        self.frame = frame
        self.cbs   = defaultdict(lambda: Delegate(ignore_exceptions = wx.PyDeadObjectError))
        self.idcbs = {}

    def OnDown(self, shortcut, callback):

        sc = str(shortcut)

        accel = keycodes(sc, accel = True)
        self.cbs[accel].insert(0, callback)
        self.update_table()

        def rem(accel=accel, callback=callback, shortcut=sc):
            self.cbs[accel].remove(callback)

        return rem

    def update_table(self):
        '''
        The wx.AcceleratorTable class used for binding keyboard shortcuts to
        a window seems to be read only, so this function rebuilds the
        table every time a callback is added.
        '''
        idcbs = self.idcbs
        ReleaseIds(idcbs.keys())
        idcbs.clear()

        entries = []

        for (modifiers, key), callback in self.cbs.iteritems():
            wxid = MyNewId()
            idcbs[wxid] = callback
            entries.append((modifiers, key, wxid))

        atable = wx.AcceleratorTableFromSequence(entries)
        if not atable.IsOk(): print 'warning: accelerator table is not OK'

        self.frame.SetAcceleratorTable(atable)

    def _oncommandevent(self, e):
        try:
            cbs = self.idcbs[e.Id]
        except KeyError:
            e.Skip()
        else:
            cbs(e)
            e.Skip()

