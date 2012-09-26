'''
tests Twitter GUI components
'''

import wx
from social.twitter.twittergui import TwitterStatusDialog, TwitterAccountPanel

def test_status_dialog():
    import gettext
    gettext.install('digsby')
    from tests.testapp import testapp
    testapp('../../..')
    from social.twitter import get_snurl
    from util.threads.threadpool import ThreadPool
    ThreadPool(2)
    a = wx.PySimpleApp()
    d = TwitterStatusDialog.ShowSetStatus(None, 'foobar_username', initial_text='hello', tiny_url = get_snurl)
    d2 = TwitterStatusDialog.ShowSetStatus(None, 'foobar_username', initial_text='hello', tiny_url = get_snurl)
    assert d is d2
    d.Show()
    a.MainLoop()

def test_account_panel():
    import gettext
    gettext.install('digsby')
    from tests.testapp import testapp
    testapp('../../..')
    from util.threads.threadpool import ThreadPool
    ThreadPool(2)
    a = wx.PySimpleApp()
    f = wx.Frame(None)


    p = TwitterAccountPanel(f)
    f.SetSize((450, 350))
    f.Layout()
    f.Fit()
    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    test_account_panel()
