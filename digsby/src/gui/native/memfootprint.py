'''
Timers that trigger memory to page out while Digsby is idle.
'''

import wx

__all__ = ['memory_event']

enabled = True

def memory_event():
    '''
    Indicates to the system that it should soon try to lower its memory
    footprint. Threadsafe.
    '''

    wx.CallAfter(start_timer)

def set_enabled(val):
    global enabled
    enabled = bool(val)

WAIT_MS = 3000               # how long to wait after a trigger before paging out RAM
LONGTERM_MS = 1000 * 60 * 15 # 15 minutes

from gui.native import lower_memory_footprint


def lower():
    if enabled:
        lower_memory_footprint()

def start_timer():
    t = memtimer()
    if not t.IsRunning():
        t.StartOneShot(WAIT_MS)

def memtimer():
    app = wx.GetApp()

    try:
        return app._memory_timer
    except AttributeError:
        # this timer is used to delay paging out RAM after a user action
        timer = app._memory_timer = wx.PyTimer(lower)

        # a longer term timer that runs repeating, trigger a page out independently
        longterm_timer = app._longterm_memory_timer = wx.PyTimer(lower)
        longterm_timer.StartRepeating(LONGTERM_MS)

        return timer
