#@PydevCodeAnalysisIgnore

import wx
import wx.lib.newevent

newevt = wx.lib.newevent.NewCommandEvent

TextFormatChangedEvent, EVT_TEXT_FORMAT_CHANGED = newevt()