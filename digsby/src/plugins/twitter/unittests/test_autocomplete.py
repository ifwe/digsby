import wx

def sample_users():
    from os.path import dirname, abspath, join as pathjoin
    with open(pathjoin(dirname(abspath(__file__)), 'sample_users.json')) as f:
        users_json = f.read()
    import simplejson
    return simplejson.loads(users_json)


def main():
    from tests.testapp import testapp

    with testapp(skinname='Windows 7'):
        f = wx.Frame(None, size=(400, 140))
        from twitter.twitter_gui import TwitterInputBoxBase
        #screen_names = sorted_screen_names(sample_users())
        users = sorted(sample_users().values(), key=lambda user: user['screen_name'].lower())
        t = TwitterInputBoxBase(f)

        from twitter.twitter_gui import TwitterAutoCompleteController

        def complete():
            from gui.autocomplete import autocomplete
            from twitter.twitter_gui import TwitterSearchResult
            t.a = autocomplete(t, [TwitterSearchResult(u) for u in users], TwitterAutoCompleteController(users))

        f.Show()

if __name__ == '__main__':
    main()

