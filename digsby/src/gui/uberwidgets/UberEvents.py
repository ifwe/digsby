#@PydevCodeAnalysisIgnore

import wx
import wx.lib.newevent

newevt = wx.lib.newevent.NewEvent

UBOver, EVT_UB_OVER = newevt()
UBOut, EVT_UB_OUT = newevt()

DragStart, EVT_DRAG_START = newevt()

TabNotifiedEvent, EVT_TAB_NOTIFIED = newevt()