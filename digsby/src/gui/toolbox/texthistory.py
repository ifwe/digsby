'''

history support for text ctrls

ctrl+up   -> older
ctrl+down -> newer

TODO: use util.fmtstr and textctrl.GetFormattedValue to preserve formatting

'''
import wx
from util import strip_html2
from util.primitives.structures import roset
from util.lrucache import lru_cache

strip_html2 = lru_cache(80)(strip_html2)


class TextHistory(object):
    def __init__(self, ctrl = None, backlog = None):

        self.history = roset()
        self.clip    = ''
        self.index   = 0
        self.backlog = backlog

        if ctrl is not None:
            self.bind_textctrl(ctrl)

    def commit(self, val):
        if not val: return

        # [x, y, z, ''] -> [x, y, z, A, '']

        # insert the new message
        self.history.add(val)
        if self.clip == val:
            self.clip = ''

    def prev(self):
        val      = self.get()
        clip  = self.clip

        if self.index == 0 and val:
            self.history.add(val)
            self.index -= 1

        if not self.index and clip and clip != val:
            self.set(clip)
        elif self.history and abs(self.index) < len(self.history):
            self.index -= 1
            self.set(self.history[self.index])
        elif self.backlog is not None:
            try:
                messageobj = self.backlog.next()
                message = getattr(messageobj, 'message', None)
                if message is not None:
                    message = strip_html2(message)
            except StopIteration:
                self.backlog = None
            else:
                if message is not None:
                    self.history.insert(0, message)
                    self.prev()


    def next(self):
        val = self.get()

        if self.index:
            self.index += 1
            if self.index:
                self.set(self.history[self.index])
            elif self.clip:
                self.set(self.clip)
            else:
                self.set('')
        elif val:
            self.clip = val
            self.set('')

    def ParadoxCheck(self):
        present = self.get()
        past = self.history[self.index]
        if present != past:
            self.index = 0

    def bind_textctrl(self, ctrl):
        ctrl.Bind(wx.EVT_KEY_DOWN, self.keydown)
        self.set = ctrl.SetValue
        self.get = ctrl.GetValue


    def keydown(self, e, WXK_DOWN = wx.WXK_DOWN, WXK_UP = wx.WXK_UP):
        c = e.KeyCode


        if e.GetModifiers() == wx.MOD_CMD:
            if   c == WXK_DOWN: return self.next()
            elif c == WXK_UP:   return self.prev()
            elif self.index:    self.ParadoxCheck()
        elif self.index:
            self.ParadoxCheck()

        e.Skip()
