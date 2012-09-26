import wx
import wx.lib.sized_controls as sc
import unittest

import utiltests
import menutests

class UnitTestDialog(sc.SizedDialog):
    def __init__(self, *args, **kwargs):
        sc.SizedDialog.__init__(self, *args, **kwargs)
        
        self.pane = self.GetContentsPane()
        wx.StaticText(self.pane, -1, "Test Runner Console")
        
        self.outputText = wx.TextCtrl(self.pane, -1, style=wx.TE_MULTILINE)
        self.outputText.SetSizerProps(expand=True, proportion=1)
        
        self.testButton = wx.Button(self.pane, -1, "Run Tests")
        
        self.Bind(wx.EVT_BUTTON, self.run_tests, self.testButton)
        
    def run_tests(self, event):
        results = unittest.TestResult()
        suite = unittest.TestLoader().loadTestsFromTestCase(utiltests.UtilTestingSuite)
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(menutests.MenubarTestingSuite))
        
        suite.run(results)
        
        self.outputText.WriteText("%d tests run\n\n" % results.testsRun)
        
        errors = len(results.errors)
        failures = len(results.failures)
        
        if errors > 0 or failures > 0:
            for failure in results.failures:
                self.outputText.WriteText("Failure in %r\n%s" % (failure[0], failure[1]))
        
            for error in results.errors:
                self.outputText.WriteText("Error in %r\n%s" % (error[0], error[1]))
            
            
        else:
            self.outputText.WriteText("All tests passed!")
