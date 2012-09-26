from tests.testframe import TestFrame
import gui.native.helpers
import wx



if __name__ == '__main__':

    from tests.testapp import testapp
    app = testapp('../..', skinname = 'silverblue')

from spelling import SpellCheckTextCtrlMixin

class SpellCheckTextCtrl(wx.TextCtrl,SpellCheckTextCtrlMixin):
    def __init__(self,parent):

        long = '''
we should just mirror the FTP site. use the sig files to check for up-to-date-ness.

we should not mess with the directories. we should just be unpacking the files on top of the aspell folder (or users aspell folder).

we should use the 0index.html file (linked above) to generate the list of choices of files. note that the table entries have links, ascii names, and unicode names, as well as the 2 letter codes that aspell needs to locate them.

we should use our file transfer window to show the progress, and provide cancel-ability.
'''

        empty = ''

        sample = empty



        wx.TextCtrl.__init__(self, parent,-1, style= wx.TE_RICH2 | wx.TE_MULTILINE| wx.TE_CHARWRAP | wx.NO_BORDER | wx.WANTS_CHARS | wx.TE_NOHIDESEL)
        SpellCheckTextCtrlMixin.__init__(self)



input = None
class SpellCheckTest(wx.Panel):
    def __init__(self,parent = None):

        wx.Panel.__init__(self,parent or TestFrame("Test - Spellcheck"))

        s = self.Sizer = wx.BoxSizer(wx.VERTICAL)

        global input
        input = self.input = SpellCheckTextCtrl(self)

#        output = self.output = wx.TextCtrl(self,-1,style= wx.TE_RICH2 | wx.TE_MULTILINE | wx.TE_CHARWRAP | wx.WANTS_CHARS | wx.TE_NOHIDESEL | wx.TE_READONLY)
#        output.MinSize = (output.MinSize.width, 60)
        s.Add(input , 1, wx.EXPAND)
#        s.Add(output, 0, wx.EXPAND)

        self.Layout()

        if isinstance(self.Parent,TestFrame):
            wx.CallAfter(self.ConfigureTestFrame,self.Parent)



    def ConfigureTestFrame(self, testframe):

        s = testframe.Sizer = wx.BoxSizer(wx.VERTICAL)

        s.Add(self,1,wx.EXPAND)

        testframe.Show(True)

        testframe.CreateStatusBar(2)
        testframe.SetStatusWidths([100,-1])



if __name__ == '__main__':
    sct = SpellCheckTest()
    app.MainLoop()









