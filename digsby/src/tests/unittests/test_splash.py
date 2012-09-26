from tests import TestCase, test_main
import digsbysplash
import config
import os.path
import gui.skin
import wx

def _create_splash_screen():
    def res(*a):
        return os.path.join(gui.skin.resourcedir(), *a)

    import cgui
    bitmaps = cgui.LoginWindowBitmaps()
    bitmaps.logo = wx.Bitmap(res('digsbybig.png'))
    bitmaps.help = wx.Bitmap(res('skins/default/help.png'))
    bitmaps.settings = wx.Bitmap(res('AppDefaults', 'gear.png'))
    bitmaps.language = wx.Bitmap(res('skins/default/serviceicons/widget_trans.png'))
    revision_string  = ' '
    return digsbysplash.LoginWindow(None, (0, 0), bitmaps, str(revision_string), True)


class TestSplash(TestCase):
    def test_validator(self):
        'test the splash screen validator function'

        val, reason = digsbysplash.validate_data(dict(username='digsby'))
        self.expect(val)

        val, reason = digsbysplash.validate_data(dict(username='fake@hotmail.com'))
        self.expect(not val)

    if config.platform == 'win':
        def test_splash_windowclass(self):
            '''Ensure that we can construct a splash screen, and that its window class name is
            "wxWindowClassNR", since that is what the installer uses to detect if Digsby
            is running.'''

            window = _create_splash_screen()

            def GetClassName(window):
                import ctypes
                count = 200
                class_name = ctypes.create_string_buffer(200)
                assert ctypes.windll.user32.GetClassNameA(window.Handle, ctypes.byref(class_name), count)
                return class_name.value

            assert GetClassName(window) == 'wxWindowClassNR'
            window.Destroy()

if __name__ == '__main__':
    test_main()

