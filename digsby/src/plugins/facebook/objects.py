from logging import getLogger
log = getLogger("facebook.objects")

class Alerts(object):
    stuff = ['num_msgs', 'msgs_time', 'num_pokes', 'pokes_time',
                 'num_shares', 'shares_time', 'friend_requests',
                 'group_invites', 'event_invites', 'notifications']

    urls = dict(msgs =            'http://www.facebook.com/inbox/',
                pokes =           'http://www.facebook.com/home.php',
                shares =          'http://www.facebook.com/posted.php',
                friend_requests = 'http://www.facebook.com/reqs.php',
                group_invites =   'http://www.facebook.com/reqs.php#group',
                event_invites =   'http://www.facebook.com/?sk=events',
                notifications =   'http://www.facebook.com/notifications.php')

    def __init__(self, fb=None, notifications_get_xml=None, notifications = None):
        log.debug("type(notifications_get_xml) ==> %r", type(notifications_get_xml))
        self.fb = fb

        if notifications_get_xml is not None:
            log.debug("here")
            t = notifications_get_xml
            self.num_msgs        = int(t.messages.unread)
            self.msgs_time       = int(t.messages.most_recent)
            self.num_pokes       = int(t.pokes.unread)
            self.pokes_time      = int(t.pokes.most_recent)
            self.num_shares      = int(t.shares.unread)
            self.shares_time     = int(t.shares.most_recent)
            self.friend_requests = set(int(uid) for uid in t.friend_requests)
            self.group_invites   = set(int(gid) for gid in t.group_invites)
            self.event_invites   = set(int(eid) for eid in t.event_invites)

        else:

            self.num_msgs        = 0
            self.msgs_time       = 0
            self.num_pokes       = 0
            self.pokes_time      = 0
            self.num_shares      = 0
            self.shares_time     = 0
            self.friend_requests = set()
            self.group_invites   = set()
            self.event_invites   = set()

            log.debug("there")
        self.update_notifications(notifications)

    def update_notifications(self, notifications=None):
        if notifications is None:
            notifications = []
        self.notifications   = set(n['notification_id'] for n in notifications
                                   if ((n.get('title_html', None) is not None)
                                       and (int(n['is_unread']) == 1)))

    def __repr__(self):
        from pprint import pformat
        s = pformat([(a, getattr(self, a)) for a in self.stuff])

        return '<Alerts %s>' % s

    def __sub__(self, other):
        ret = Alerts(self.fb)
        for attr in self.stuff:
            setattr(ret, attr, getattr(self, attr) - getattr(other, attr))
        return ret

    def __cmp__(self, other):
        if type(self) != type(other):
            return 1
        for attr in self.stuff:
            if getattr(self, attr) != getattr(other, attr):
                return (self.num_all - other.num_all) or 1
        return 0

    @property
    def num_all(self):
        return sum([
                    self.num_msgs,
                    self.num_pokes,
                    self.num_shares,
                    len(self.friend_requests),
                    len(self.group_invites),
                    len(self.event_invites),
                    len(self.notifications)
                ])

    @property
    def count(self):
        return sum([
                    self['num_msgs'],
                    self['num_pokes'],
                    self['num_shares'],
                    self['num_friend_requests'],
                    self['num_group_invites'],
                    self['num_event_invites'],
                    self['num_notifications']
                ])

    @property
    def num_friend_requests(self):
        return len(self.friend_requests)

    @property
    def num_group_invites(self):
        return len(self.group_invites)

    @property
    def num_event_invites(self):
        return len(self.event_invites)

    @property
    def num_notifications(self):
        return len(self.notifications)

    def __nonzero__(self):
        return any(getattr(self, attr) for attr in self.stuff)

    def __getitem__(self, key):
        if not hasattr(self, 'fb') or self.fb is None:
            raise KeyError(key)
        return self.fb.filters['alerts'][key] * getattr(self, key)

