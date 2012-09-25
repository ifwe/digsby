from logging import getLogger; log = getLogger('tagged.account')
from social.network import SocialNetwork
import protocols
import path
from common import action
from common import pref
from common.notifications import fire
from util.callbacks import callsback
import wx
import TaggedUtil as TU
import gui.infobox.interfaces as gui_interfaces
import gui.infobox.providers as gui_providers

class TaggedAccount(SocialNetwork):
    service = protocol = 'tagged'

    alert_keys = [
            'actions',
            'birthdays',
            'cafe',
            'comments',
            'elections',
            'farm',
            'friends',
            'gifts',
            'gold_2',
            'groups',
            'luv',
            'meetme',
            'mob',
            'mobile_new_update',
            'pets',
            'cr_photo_warning',
            'poker_2',
            'profile',
            'questions',
            'sororitylife',
            'tags',
            'topics',
            'unread_messages',
            'videos',
            'wink',
            'zoosk',
    ]

    group_filters = {
            'actions' : ['action_slots',
                         'action_tabs'],
               'cafe' : ['cafe_food_ready',
                         'cafe_food_rotting',
                         'cafe_needs_love',
                         'cafe_visit',
                         'cafe_visit_clean',
                         'cafe_visit_eat',
                         'cafe_waiter_contract_expired'],
          'elections' : ['elections_job_completed',
                         'elections_favor',
                         'elections_hired',
                         'elections_new_round',
                         'elections_promo'],
               'farm' : ['farm_ready',
                         'farm_visit'],
            'friends' : ['find_friend',
                         'new_friends',
                         'friend_requests',
                         'invite_friend'],
             'groups' : ['groups_updated',
                         'group_forum_reply',
                         'group_invite'],
             'meetme' : ['meetme_headliner_reup',
                         'meetme_spotlight_reup',
                         'meetme_match',
                         'meetme_yes'],
                'mob' : ['mob_boost',
                         'mob_fight',
                         'mob_hire',
                         'mob_promo',
                         'mob_promo_simple',
                         'mob_prop_rdy'],
            'profile' : ['profile_photo',
                         'profile_viewers'],
          'questions' : ['questions_answer',
                         'questions'],
             'topics' : ['topics_promo',
                         'topics_new',
                         'topics_response'],
              'zoosk' : ['zoosk_coin',
                         'zoosk_message'],
       'sororitylife' : ['sororitylife',
                         'soriritylife_new_version']
    }

    @property
    def header_funcs(self):
        return ((_('Home'), TU.weblink()),
                (_('Profile'), TU.weblink('profile.html')),
                (_('Messages'), TU.weblink('messages.html')),
                (_('People'), TU.weblink('people.html')),
                (_('Games'), TU.weblink('games.html')))

    @property
    def extra_header_func(self):
        return (_('Invite Friends'), TU.weblink('friends.html#tab=contacts&type=0&filterpg=All_0'))

    def __init__(self, **options):
        self.connection = None
        self._dirty = True
        filters = options.pop('filters', {})
        self.update_filters(filters)
        super(TaggedAccount, self).__init__(**options)

    def set_dirty(self):
        self._dirty = True

    def Connect(self):
        log.info('Connect')
        self.change_state(self.Statuses.CONNECTING)
        if self.enabled:
            self.update_now()
        else:
            self.set_offline(self.Reasons.NONE)

    def update_now(self):
        log.info('Updating %r', self)
        self.start_timer()
        if self.state == self.Statuses.OFFLINE or self.connection is None:
            self.change_state(self.Statuses.CONNECTING)
            self.create_connection()
            self.connect(success = lambda *a: self.change_state(self.Statuses.ONLINE), # S1
                         error = lambda *a: self.set_offline(self.Reasons.CONN_FAIL))  # E1
        else:
            self.update()

    def update_filters(self, filters):
        alerts = filters if filters else [True]*len(self.alert_keys)
        self.filters = dict(zip(self.alert_keys, alerts))
        self.whitelist = dict(zip(self.alert_keys, alerts))
        for key in self.group_filters:
            alert_enabled = self.whitelist[key]
            del self.whitelist[key]
            for i in self.group_filters[key]:
                self.whitelist[i] = alert_enabled

    def update_info(self, **info):
        filters = info.pop('filters', None)
        if filters is not None:
            self.update_filters(filters)
        self.set_dirty()
        SocialNetwork.update_info(self, **info)

    def get_options(self):
        options = super(TaggedAccount, self).get_options()
        options['filters'] = [bool(self.filters[x]) for x in self.alert_keys]
        return options

    @callsback
    def connect(self, callback = None):
        def on_connect_success(*a):
            self.update(success = lambda *a: self.set_dirty(),                       # S3
                        error = lambda *a: self.set_offline(self.Reasons.CONN_LOST)) # E3
            callback.success() # S1

        self.connection.login(success = on_connect_success,
                              error = callback.error) # E1

    @callsback
    def update(self, callback = None):
        self.connection.getStatus(callback = callback)
        self.connection.getAlerts(callback = callback)
        self.connection.getFriendsInfo(callback = callback)

        def on_getCandidate_success(*a):
            self.connection.getElectionsNewsfeed(callback = callback)

        self.connection.getCandidate(success = on_getCandidate_success,
                                     error = callback.error) # E3

        def on_getPet_success(*a):
            self.connection.getPetsNewsfeed(callback = callback)

        self.connection.getPet(success = on_getPet_success,
                               error = callback.error) # E3

    # Create a connection
    def create_connection(self):
        if self.connection is not None:
            raise Exception('Already have a connection')

        import TaggedProtocol as TP
        self.connection = TP.TaggedProtocol(self, self.name, self._decryptedpw())
        log.info('Connection created')

    # Gets called by SocialNetwork
    def Disconnect(self, reason = None):
        if reason is None:
            reason = self.Reasons.NONE
        self.connection = None
        self.set_offline(reason)
        log.info('Disconnected')

    @action()
    def openurl_Home(self):
        TU.launchbrowser('')

    @action()
    def openurl_Profile(self):
        TU.launchbrowser('profile.html')

    @action()
    def openurl_Messages(self):
        TU.launchbrowser('messages.html')

    @action()
    def openurl_People(self):
        TU.launchbrowser('people.html')

    @action()
    def openurl_Games(self):
        TU.launchbrowser('games.html')

    @action()
    def SetStatus(self):
        if pref('social.use_global_status', default = False, type = bool):
            wx.GetApp().SetStatusPrompt([self])
        else:
            log.error('No alternative to global status dialog for TaggedAccount')

    @callsback
    def SetStatusMessage(self, new_message, callback = None, **k):
        def success(*a):
            self.set_dirty()
            callback.success()

        self.connection.setStatus(new_message,
                                  success = success,
                                  error = callback.error)

    def DefaultAction(self):
        self.SetStatus()

    def SendMessage(self, user_id, display_name, *a):
        event = dict(sender_uid = int(user_id))
        fire('tagged.toast',
             title = _('New Message to: %s') % display_name,
             msg = '',
             sticky = True,
             input = lambda text, opts, *a: self.connection.send_message(text, opts, event),
             popupid = ('tagged_toast!%r!%r' % (int(user_id), id(self.connection))))

## Infobox

class TaggedIB(gui_providers.InfoboxProviderBase):
    @property
    def _dirty(self):
        return self.acct._dirty

    protocols.advise(asAdapterForTypes = [TaggedAccount], instancesProvide = [gui_interfaces.ICacheableInfoboxHTMLProvider])
    def __init__(self, acct):
        gui_providers.InfoboxProviderBase.__init__(self)
        self.acct = acct

    def get_html(self, htmlfonts = None, **opts):
        self.acct._dirty = False
        return gui_providers.InfoboxProviderBase.get_html(self, **opts)

    def get_app_context(self, ctxt_class):
        return ctxt_class(path.path(__file__).parent.parent, 'component_tagged')

    def get_context(self):
        ctxt = gui_providers.InfoboxProviderBase.get_context(self)

        conn = self.acct.connection
        ctxt.update(
            conn = conn
        )

        return ctxt