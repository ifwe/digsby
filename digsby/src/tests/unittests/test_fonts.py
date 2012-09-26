from tests import TestCase, test_main
import wx

class TestFonts(TestCase):
    def test_font_size(self):
        f = wx.Frame(None)
        try:
            t = wx.TextCtrl(f, style=wx.TE_RICH2)

            # ensure passing a wxFont into and out of wxTextCtrl::Get/SetStyle
            # maintains its size
            success, style = t.GetStyle(0)
            assert success

            point_size = style.Font.PointSize

            t.SetStyle(0, t.LastPosition, style)

            success, style = t.GetStyle(0)
            assert success

            self.assertEqual(style.Font.PointSize, point_size)
        finally:
            f.Destroy()

if __name__ == '__main__':
    test_main()

