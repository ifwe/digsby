from tests import TestCase, test_main
import actionIDs
import time
import wx

from gui.app.mainMenuEvents import fire_action_event

popupActions =  [
                actionIDs.ShowBuddyList,
                actionIDs.ShowMenuBar,
                actionIDs.SetStatus,
                actionIDs.SetStatusCustom,
                ]

# requires Digsby app to be running
class MenubarTestingSuite(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        wx.GetApp().testing = True
    
    def tearDown(self):
        TestCase.tearDown(self)
        wx.GetApp().testing = False
    
    def testHandlers(self):
        # event system requires App mixin; we need to make it more testable
        return 

        app = wx.GetApp()
        for action in dir(actionIDs):
            app.event_fired = None
            if action.startswith("__"):
                continue
            
            id = getattr(actionIDs, action, -1)
            self.assert_(action != -1)
            
            if isinstance(id, int) and not id == wx.ID_EXIT and not id in popupActions:
                print "Firing handler for id=%r" % id
                fire_action_event(id)
            
                app.Yield()
                self.assert_(app.event_fired, "No event fired for action %s" % action)


if __name__ == "__main__":
    test_main()
