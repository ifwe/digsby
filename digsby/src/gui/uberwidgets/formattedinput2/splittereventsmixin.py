'''
Mixin with logic to manage making the autoresizing IMInput play well with the splitter
'''

import wx
import config #@UnresolvedImport

from common import setpref, pref

wxMSW = 'wxMSW' in wx.PlatformInfo
from FormattedExpandoTextCtrl import EVT_ETC_LAYOUT_NEEDED

#SWIG HAX: In Robin's bindings, wx.EVT_SIZE is a function, and wx.wxEVT_SIZE is the int id
EVT_SIZE = wx.EVT_SIZE if config.platform == "win" else wx.wxEVT_SIZE

class SplitterEventMixin(object):
    def OnExpandEventSplitter(self, event):

        if self.resizing:
            return

        #Can't event.Skip() here or a scroll happens
        self.OnExpandEvent(event)
        if hasattr(self, 'splitter'):
            best_size = self.BestSizeControl.BestSize.height
            splitterpos = self.splitter.ClientSize.height - best_size - self.splitter.SashSize
            self.splitter.SetSashPosition(splitterpos)
            self.Layout()

    @property
    def BestSizeControl(self):
        if 'wxMac' in wx.PlatformInfo:
            return self.tc
        else:
            return self

    def BindSplitter(self, splitter, heightpref = None):

        splitter.Bind(wx.EVT_LEFT_DOWN, self.OnSplitterStart)
        splitter.Bind(wx.EVT_LEFT_UP, self.OnSplitterSet)
        #splitter.Connect(splitter.Id, splitter.Id, EVT_SIZE, self.OnFirstSplitterSize)

        self.splitter = splitter

        self.heightpref = heightpref

        self.resizing = False

        self.Bind(EVT_ETC_LAYOUT_NEEDED, self.OnExpandEventSplitter)
        if 'wxMac' in wx.PlatformInfo:
            self.tc.Bind(wx.EVT_TEXT, self.OnExpandEventSplitter)


        tc = self.tc
        tc.SetMinHeight(pref(self.heightpref, 0))
        tc.ForceExpandEvent()


        #Layout on coming out of window hidden - fixes tray and fresh window layouts
        self.Top.Bind(wx.EVT_SHOW, self.OnTopShow)
        self.Top.Bind(wx.EVT_SET_FOCUS, self.OnTopShow)

        #Layout on page shown, fixes layout on showing tab, notably a new tab when win is minimized
        self.splitter.GrandParent.Bind(wx.EVT_SHOW, self.OnTopShow)

        #Layout when window is restored from iconized state
        if hasattr(self.Top, 'iconizecallbacks'):
            self.Top.iconizecallbacks.add(self.OnRestore)
        else:
            self.Top.Bind(wx.EVT_ICONIZE, self.OnRestore)



#    def OnFirstSplitterSize(self, event):
#
#        #HAX: make sure the splitter lays out the first time it get's a real size
#
#        event.Skip()
#
#        splitter = self.splitter
#
#        if splitter.Size.height and splitter.Size.width:
#            splitter.Disconnect(splitter.Id, splitter.Id, EVT_SIZE)
#            wx.CallAfter(self.OnExpandEvent, event)

    def OnSplitterStart(self, event):

        self.resizing = True

        tc = self.tc

        baseh = tc.GetNatHeight()

        tc.SetMinHeight(baseh)

        #HAX for FormattedInput's extra layer of abstraction from the Expando, should be handled better
        self.BestSizeControl.MinSize = self.BestSizeControl.BestSize

        event.Skip()

    def OnSplitterSet(self, event):

        self.resizing = False

        event.Skip()
        tc = self.tc


        natHeight = tc.GetNatHeight();
        setHeight = tc.GetSize().height;
        h = -1 if setHeight <= natHeight else setHeight

#        log.info("input_base_height set to %s", h)

        if hasattr(self, 'heightpref') and self.heightpref is not None:
            setpref(self.heightpref, h)

        tc.SetMinHeight(h)



    def OnTopShow(self, event):
        """
        Bound to the top level window of this control
        it's a hax to make sure the text control is the the correct height when shown
        """

        event.Skip()
        if not hasattr(event, 'GetShow') or event.GetShow():
            self.tc.ForceExpandEvent()

    def OnRestore(self, event=None):
        """
        Bound to the top level window of this control
        it's a hax to make sure the text control is the the correct height when shown
        """

        if event is not None:
            event.Skip()
        if event is None or not event.Iconized():
            wx.CallAfter(self.tc.ForceExpandEvent)
