from __future__ import print_function
import wx
import sys

class MockTwitterAccount(object):
    def __init__(self, protocol):
        from twitter.twitter import TwitterAccount
        self.protocol = TwitterAccount.protocol
        self.twitter_protocol = protocol
        self.twitter_protocol.account = self
        self.username = protocol.username
        self._dirty = True


# TODO: protocols.declare_adapter_for_type

twitter = None
def main():
    def on_close(e):
        twitter.disconnect()

        import AsyncoreThread
        AsyncoreThread.join()

        f.Destroy()

    def droptables():
        if wx.YES == wx.MessageBox(
                'Are you sure you want to drop all tables?',
                style = wx.YES_NO, parent = f):
            twitter.clear_cache()

    def build_test_frame():
        f = wx.Frame(None, title='Twitter Test')
        f.SetSize((500, 700))
        f.Bind(wx.EVT_CLOSE, on_close)

        buttons = []
        def button(title, callback):
            b = wx.Button(f, -1, title)
            b.Bind(wx.EVT_BUTTON, lambda e: callback())
            buttons.append(b)

        def infobox():
            from gui.toolbox import Monitor
            from gui.infobox.infobox import DEFAULT_INFOBOX_WIDTH
            from gui.infobox.infoboxapp import init_host, set_hosted_content

            f = wx.Frame(None)
            size = (DEFAULT_INFOBOX_WIDTH, Monitor.GetFromWindow(f).ClientArea.height * .75)
            f.SetClientSize(size)

            w = wx.webview.WebView(f)

            init_host(w)
            set_hosted_content(w, MockTwitterAccount(twitter))
            f.Show()

        def popup():
            twitter.webkitcontroller.evaljs('account.showTimelinePopup();')

        def fake_tweets():
            j('fakeTweets(%d);' % int(fake_tweets_txt.Value))
            twitter.webkitcontroller.webview.GarbageCollect()

        button('Open Window', twitter.open_timeline_window)
        button('Update',      twitter.update)
        button('Infobox',     infobox)
        button('Drop Tables', droptables)
        button('Popup',       popup)
        button('Fake Tweets', fake_tweets)

        s = f.Sizer = wx.BoxSizer(wx.HORIZONTAL)

        v = wx.BoxSizer(wx.VERTICAL)
        v.AddMany(buttons)

        fake_tweets_txt = wx.TextCtrl(f, -1, '1000')
        v.Add(fake_tweets_txt)

        s.Add(v, 0, wx.EXPAND)

        v2 = wx.BoxSizer(wx.VERTICAL)
        stxt = wx.StaticText(f)
        v2.Add(stxt, 0, wx.EXPAND)

        from pprint import pformat
        from common.commandline import wkstats
        def update_text():
            debug_txt = '\n\n'.join([
                pformat(wkstats()),
                j('debugCounts()')
            ])

            stxt.Label = debug_txt
            f.Sizer.Layout()

        f._timer = wx.PyTimer(update_text)
        f._timer.StartRepeating(1000)
        f.SetBackgroundColour(wx.WHITE)

        s.Add((50, 50))
        s.Add(v2, 0, wx.EXPAND)

        return f

    from tests.testapp import testapp

    username, password = 'ninjadigsby', 'no passwords'
    if len(sys.argv) > 2:
        username, password = sys.argv[1:3]

    app = testapp(skinname='Windows 7', plugins=True)

    global twitter # on console
    from twitter.twitter import TwitterProtocol
    twitter = TwitterProtocol(username, password)
    twitter.events.state_changed += lambda state: print('state changed:', state)
    twitter.events.reply += lambda screen_name: print('reply:', screen_name)

    import common.protocolmeta
    account_opts = common.protocolmeta.protocols['twitter']['defaults'].copy()

    if '--twitter-offline' in sys.argv:
        account_opts['offlineMode'] = True

    #import simplejson
    #account_opts['feeds'] = simplejson.loads('[{"type": "timeline", "name": "timeline"}, {"type": "mentions", "name": "mentions"}, {"type": "directs", "name": "directs"}, {"name": "group:1", "popups": false, "ids": [14337372, 9499402, 8517312, 7341872, 32218792, 9853162], "filter": false, "groupName": ".syntax", "type": "group"}, {"name": "search:1", "title": "foramilliondollars", "popups": false, "merge": false, "query": "#foramilliondollars", "save": true, "type": "search"}]')

    twitter.connect(account_opts)

    # mock an accountmanager/social networks list for the global status dialog
    from util.observe import ObservableList, Observable
    class TwitterAccount(Observable):
        service = protocol = 'twitter'
        enabled = True
        ONLINE = True
        def __init__(self, connection):
            Observable.__init__(self)
            self.display_name = self.name = connection.username
            self.connection = connection
            self.connection.account = self

    import digsbyprofile
    from util import Storage as S

    acctmgr = digsbyprofile.profile.account_manager = S(
        socialaccounts = ObservableList([TwitterAccount(twitter)])
    )
    digsbyprofile.profile.socialaccounts = acctmgr.socialaccounts

    global j
    j = twitter.webkitcontroller.evaljs

    def _html():
        txt = twitter.webkitcontroller.FeedWindow.PageSource.encode('utf-8')
        from path import path
        p = path(r'c:\twitter.html')
        p.write_bytes(txt)
        wx.LaunchDefaultBrowser(p.url())

    global html
    html = _html

    f = build_test_frame()
    f.Show()

    if '--drop' in sys.argv:
        twitter.clear_cache()

    wx.CallLater(500, twitter.open_timeline_window)

    app.MainLoop()

if __name__ == '__main__':
    main()
