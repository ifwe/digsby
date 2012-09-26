from tests import TestCase, test_main
import wx
from gui.imwin.styles import get_theme_safe

class TestWebKit(TestCase):
    def test_unicode_paths(self):
        '''
        ensure that the example conversation loads correctly
        '''

        f = wx.Frame(None)
        
        theme = get_theme_safe('Smooth Operator', None)
        from gui.pref.pg_appearance import build_example_message_area

        a = build_example_message_area(f, theme)
        html = a.HTML
        f.Destroy()

        
        from common import profile
        username = profile.username

        print 'username is', username
        assert username in html, 'username %r was not in HTML:\n%r' % (username, html)

if __name__ == '__main__':
    test_main()
