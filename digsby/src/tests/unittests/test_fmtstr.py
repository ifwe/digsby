import wx
from tests import TestCase, test_main

test_rtf = '''{\\rtf1\\ansi\\ansicpg1252\\deff0\\deflang1033{\\fonttbl{\\f0\\fswiss\\fcharset0 Times New Roman;}}\r\n{\\colortbl ;\\red0\\green0\\blue0;\\red255\\green255\\blue255;}\r\n{\\*\\generator Msftedit 5.41.21.2509;}\\viewkind4\\uc1\\pard\\cf1\\highlight2\\b\\f0\\fs20 test\~abc def\\par\r\n}\r\n'''

class TestFmtStr(TestCase):
    def test_rtf(self):
        from util.primitives.fmtstr import fmtstr

        s = fmtstr(rtf=test_rtf)

        self.assertEqual(s.format_as('rtf'), test_rtf)
        self.assertEqual(s.format_as('html'),
            '<HTML><BODY><FONT FACE="Times New Roman" SIZE=2 COLOR=#000000><B>test&nbsp;abc def</B></FONT></BODY></HTML>')

    def test_plaintext(self):
        from util.primitives.fmtstr import fmtstr

        txt = u'this is plaintext with an & ampersand.'
        s = fmtstr(plaintext=txt)

        self.assertEqual(txt, s.format_as('plaintext'))

        self.assertEqual(u'this is plaintext with an &amp; ampersand.',
                         s.format_as('xhtml'))

    def test_append(self):
        from util.primitives.fmtstr import fmtstr
        a = fmtstr(rtf=test_rtf)
        b = a + 'foo'

        self.assertEqual(b.format_as('html'),
            '<HTML><BODY><FONT FACE="Times New Roman" SIZE=2 COLOR=#000000><B>test&nbsp;abc deffoo</B></FONT></BODY></HTML>')

        rtf2 = '{\\rtf1\\ansi\\ansicpg1252\\deff0\\deflang1033{\\fonttbl{\\f0\\fswiss\\fcharset0 Arial;}{\\f1\\fswiss\\fcharset0 Levenim MT;}}\r\n{\\colortbl ;\\red0\\green0\\blue0;\\red255\\green255\\blue255;}\r\n{\\*\\generator Msftedit 5.41.21.2509;}\\viewkind4\\uc1\\pard\\cf1\\highlight2\\f0\\fs16 test small \\b\\fs72 large bold \\i italic\\i0\\f1\\fs48\\par\r\n}\r\n'
        f = fmtstr(rtf=rtf2)
        msn = f.format_as('msn')

        f2 = f + 'test'
        self.assertEquals(msn + 'test', f2.format_as('msn'))

    def test_singleformat(self):
        from util.primitives.fmtstr import fmtstr
        s = fmtstr.singleformat(u'lgkjsdg df gd fg df d',
                {'foregroundcolor': wx.Colour(0, 0, 0, 255),
                 'bold': False,
                 'family': u'default',
                 'face': u'arial',
                 'italic': False,
                 'backgroundcolor': wx.Colour (255, 255, 255, 255),
                 'underline': False, 'size': 11})

        # test that wxColors get turned into tuples
        import simplejson
        simplejson.dumps(s.asDict())


if __name__ == '__main__':
    test_main()
