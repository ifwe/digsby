'''
An interactive demo for testing popup functionality.
'''

import wx

from tests.testapp import testapp
from logging import getLogger; log = getLogger('testpopup')
from gui.controls import Button
from gui import windowfx
from gui.toast import popup, Popup
from config import platformName

class input_callback(object):
    '''Passed to fire() as handlers for "buttons" callbacks. Causes popups to
    show input fields after pressing those buttons.'''

    # TODO: document this interface and place an abstract class in toast.py

    close_button = True
    spellcheck = True

    def __init__(self, cb):
        self.input_cb = cb
        self.get_value = lambda *k: 'value'
        self.char_limit = 140

def main():
    a = testapp(plugins=False)
    f = wx.Frame(None, title = 'Popup Test', style = wx.STAY_ON_TOP | wx.DEFAULT_FRAME_STYLE,
                 size = (400, 300))
    f.CenterOnScreen()
    f.Bind(wx.EVT_CLOSE, lambda e: windowfx.fadeout(f))
    f.Sizer = sz = wx.GridSizer(2, 2)

    if platformName == "win":
        from gui.native import process
        count_gdi_objects = process.count_gdi_objects
        def settitle():
            f.Title = 'Popup Test (gdi: %s)' % count_gdi_objects()
        settitle()

        title_timer = wx.PyTimer(settitle)
        title_timer.Start(1000, False)

    from gui import skin
    service_icons = [skin.get('serviceicons.' + srv) for srv in ('aim', 'icq', 'msn', 'yahoo', 'jabber', 'gtalk')]

    for b in 'upperleft upperright lowerleft lowerright'.split():
        button = wx.Button(f, -1, b)
        button.Bind(wx.EVT_BUTTON, lambda e, b=b: popup(position = b,
                                                        badge = skin.get('serviceicons.facebook', None),
                                                        header = 'header abcdefghijklmnopqrstuvwxyz djaflk dajlfk djaklf dsjaklf djakl',
                                                        major = 'major',
                                                        minor = 'minorfd jaklf jdkla fjkldwads fdjsa flkejw alfkd jsaklf jdsklafjdklsafjkl---wdq------------------fdasfsda------------fdasfdsa----fdasfdas---------------------------------------------------------------jdskla fjklsdaa jfkldwa jfkldsa jfklds ajklfds ajklfds ajklfds ajkl'))
        sz.Add(button)

    class Target(object):
        def OnSave(self):   print 'save'
        def OnSaveAs(self): print 'save as'
        def OnCancel(self): print 'cancel'

    target = Target()

    b = Button(f, 'with buttons', lambda: popup(position = 'lowerright',
                                                header = 'digsbyDragon',
                                                major = 'wants to send you file "digsby.zip"',
                                                buttons = [('Save', lambda: log.info('SAVE'))],
                                                target = target))
    def input_cb(text, opts):
        print 'message:', text, opts

    def timed():
        for x, msg in enumerate('lol roflmao brb afk jk wtf roflcopterz omg rusrs?'.split() * 3):
            wx.CallLater(1000 * x+1, lambda msg = msg: popup(header = 'digsby', minor = msg,
                                                             input = input_cb, popupid = 'wassup'))



    b2 = Button(f, 'with several inputs', timed)


    class Email(object):
        def __init__(self, subject, message):
            self.subject = subject
            self.message = message

    b3 = Button(f, 'with pages', lambda: popup(popupid = ('a','b'),
                                               update = 'paged',
                                               position = 'lowerright',
                                               header = '${email.subject}',
                                               major = '${email.message}',
                                               pages = 'emails',
                                               emails = [Email('test subject', 'test content'),
                                                         Email('test subject 2', 'testcontent2')],
                                               ))


    email_pages_args = dict(position = 'lowerright',
                              header = '${email.subject}',
                              minor = '${email.message}',
                              pages = 'emails',
                              emails = [Email('test subject', 'test really long really long really ' * 10),
                                        Email('test subject 2', 'testcontent2')],
                              onclick = lambda a: log.info('wut'))

    b4 = Button(f, 'with pages',
                lambda: popup(**email_pages_args))

    b5 = Button(f, 'after 2 secs',
                lambda: wx.CallLater(2000, lambda: popup(position = 'lowerleft',
                                               header = '${email.subject}',
                                               major = '${email.message}',
                                               pages = 'emails',
                                               emails = [Email('test subject', 'test content'),
                                                         Email('test subject 2', 'testcontent2')],
                                               )))

    def prnt(*a):
        for f in a: print f,
        print

    def button_func(item):
        return [(item.email.subject, lambda *a, **k: prnt(item))]

    b11 = Button(f, 'multiple buttons',
                 lambda: popup(position = 'lowerleft',
                               header = '${email.subject}',
                               major = '${email.message}',
                               pages = 'emails',
                               emails = [Email('test subject', 'test content'),
                                         Email('test subject 2', 'testcontent2')],
                               buttons = button_func
                               ))
    b9 = Button(f, 'new paged',
                lambda: popup(update='paged', header='blah',
                              major='bleeh', minor='bluh',
                              popupid='facebook.alerts'))

    from itertools import count
    count = count()

    def page_adder(position='lowerleft'):
        id = count.next()

        if id == 0:
            d = dict(major = '${email.message}', minor='')
        else:
            d = dict(minor ='${email.message}', major ='')

        popup(position = position,
              header = '${email.subject}',
              pages = 'emails',
              email = Email('test subject 2', 'content%d'%id),
              #update  ='paged',
              popupid = 'add',
              onclick = lambda a: log.info('rawr %d', id),
              max_lines = 20,
              **d
              )

    b6 = Button(f, 'add pages', page_adder)

    b6_2 = Button(f, 'add pages (top left)', lambda: page_adder('upperleft'))

    b7 = Button(f, 'show modal dialog', lambda: wx.MessageBox('modal!'))

    def many():
        for x in xrange(3):
            popup(header ='wut', major = 'major', minor = 'minor')

    b8 = Button(f, 'show many at once', many)

    def input_and_pages():
        args = dict(email_pages_args)
        args.update(input = input_cb)
        popup(**args)

    def input_appends():
        popup(input = lambda text, opts: '> ' + text,
              header = 'test',
              minor = 'minor',
              max_lines=5)
              


    b10 = Button(f, 'input + pages', input_and_pages)

    b12 = Button(f, 'input appends', input_appends)

    def input_after_buttons_popup():
        buttons = [('test', input_callback(lambda **k: None))]
        popup(header='input after buttons',
              buttons = buttons)

    input_after_button = Button(f, 'input after button', input_after_buttons_popup)

    sz.AddMany((b, b2, b3, b4, b5, b6, b6_2, b7, b8, b9, b10, b11, b12))
    sz.AddMany([
        input_after_button,
    ])

    sz.Add(wx.TextCtrl(f))

    if hasattr(Popup, 'use_alphaborder'):
        use_alpha = wx.CheckBox(f, -1, 'use alphaborder')
        use_alpha.SetValue(Popup.use_alphaborder)
        use_alpha.Bind(wx.EVT_CHECKBOX, lambda e: setattr(Popup, 'use_alphaborder', e.Checked))

        sz.Add(use_alpha)

    f.Bind(wx.EVT_CLOSE, lambda e: wx.GetApp().ExitMainLoop())
    f.Show()

    a.MainLoop()


if __name__ == '__main__':
    main()
