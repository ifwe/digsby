from common.accountbase import AccountBase
from util.primitives import Storage
from util.Events import EventMixin
from util.threads.timeout_thread import Timer
from social.network import SocialNetwork
from util.threads.timeout_thread import RepeatTimer
from util.threads.threadpool2 import threaded

class RssAccount(SocialNetwork, EventMixin):
    events = set(['enabled', 'disabled']) | EventMixin.events
    service = protocol = 'rss'

    def __init__(self, name, password, *a, **k):
        self.location = name
        EventMixin.__init__(self)
        self.proto = RssProtocol(self)
        SocialNetwork.__init__(self, name=name, password=password, *a, **k)
        self._dirty = True
        self.change_state(self.Statuses.ONLINE)

    def Connect(self, *a, **k):
        self.change_state(self.Statuses.ONLINE)

    def Disconnect(self, *a, **k):
        self.change_state(self.Statuses.OFFLINE)
    disconnect = Disconnect

    def get_enabled(self):
        try:
            return self._enabled
        except AttributeError:
            self.enabled = False
            return self.enabled

    def set_enabled(self, value):
        self._enabled = value
        if value:
            self.event('enabled')
        else:
            self.event('disabled')

    @property
    def count(self):
        return 2

    @property
    def feed(self):
        return sorted(list(self.proto.feed), reverse = True)

    def observe_count(self,callback):
        self.add_gui_observer(callback, 'count')

    def observe_state(self, callback):
        self.add_gui_observer(callback, 'enabled')

    def unobserve_count(self,callback):
        self.remove_gui_observer(callback, 'count')

    def unobserve_state(self,callback):
        self.remove_gui_observer(callback)

    enabled = property(get_enabled, set_enabled)

class RssProtocol(object):

    def __init__(self, myacct):
        self.myacct = myacct
        self.filter = RssFeedFilter(myacct.location)
        self.filter.bind('new_data', self.got_data)
        self.myacct.bind('enabled', self.start)
        self.myacct.bind('disabled', self.stop)

    def start(self):
        try:
            print 'starting timer'
            self.timer.start()
        except AttributeError:
            self.timer = RepeatTimer(300, self.fetch)
            print 'starting timer'
            self.start()
            self.fetch()

    def stop(self):
        try:
            print 'stopping timer'
            self.timer.stop()
        except AttributeError:
            pass

    @threaded
    def fetch(self):
        self.filter.update()
        self.myacct._dirty = True

    def got_data(self, items):
        self._dirty = True
        for item in items:
            print 'new rss item', item.title

#-------------------------------------------------

    @property
    def count(self):
        return len(self.filter.items)

    @property
    def feed(self):
        return sorted(self.filter.items)

class RssItem(Storage):
    pass

class RssFeedFilter(EventMixin):
    events = set(['new_data']) | EventMixin.events

    def __init__(self, location):
        self.location = location
        self.items = []
        EventMixin.__init__(self)

    def update(self):
        import feedparser
        new_items = feedparser.parse(self.location)
        items = [RssItem(item) for item in new_items['items']]
        self.items = items
        self.event('new_data', items)

##
#  Protocol Meta stuff
##
#protocols.rss = S(
#      name = 'RSS',
#      name_truncated = 'rss',
#      path = 'tests.rss.RssAccount',
#      username_desc = _(u'Feed URL'),
#      newuser_url = '',
#      password_url = '',
#      alerts_desc = '',
#      form = 'social',
#      needs_alerts = False,
#      alerts = [],
#      defaults = dict(),
#      whitelist_opts = set(['location']),
#      type = 'social',
#      notifications = {},
#    )


