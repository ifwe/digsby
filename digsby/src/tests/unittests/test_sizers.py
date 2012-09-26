from tests import TestCase, test_main
import wx

class TestSizers(TestCase):
    def test_adding_to_two_sizers(self):
        f = wx.Frame(None)
        p = wx.Panel(f)
        c = wx.CheckBox(p, -1, 'Test')

        sz = wx.BoxSizer(wx.VERTICAL)
        sz.Add(c)

        sz2 = wx.BoxSizer(wx.VERTICAL)
        self.assert_raises(Exception, lambda: sz2.Add(c))

        f.Destroy()

if __name__ == '__main__':
    test_main()

