from logging import getLogger; log = getLogger('tagged.protocol')
import util.httptools as httptools
import common.asynchttp as AsyncHttp
from util.callbacks import callsback
import ClientForm
from common.notifications import fire
from util.primitives import strings
from res.strings import elections
from res.strings import pets
from res.strings import alerts
import TaggedUtil as TU

class TaggedProtocol(httptools.WebScraper):
    @property
    def LOGIN_URL(self):
        return 'http' + TU.SECURE() + '://secure' + TU.TAGGED_DOMAIN()  + '/secure_login.html'

    def __init__(self, acct, username, password):
        super(TaggedProtocol, self).__init__()
        self.opener = self.http
        self.api = None
        self.realtime = None
        self.acct = acct
        self.username = username
        self.password = password
        self.session_token = None

        # data fetched from api calls
        self.status = None
        self.alerts = None
        self.online_friends = None
        self.elections_candidate = None
        self.elections_staff = None
        self.elections_projects = None
        self.elections_newsfeed = None
        self.pets_pet = None
        self.pets_owner = None
        self.pets_newsfeed = None
        log.info('Tagged protocol Initialized')

    @callsback
    def login(self, callback = None):
        def on_form_fetch_success(req, resp):
            loginForm = ClientForm.ParseResponse(resp, backwards_compat = False, request_class = AsyncHttp.HTTPRequest)[0]
            loginForm['username'] = self.username
            loginForm['password'] = self.password
            log.info('Form fetch successful')

            def on_login_success(*a):
                self.session_token = self.get_cookie('S', domain=TU.TAGGED_DOMAIN(), default=False)
                self.create_api()
                log.info('Login successful')

                def on_getSelfInfo_success(*a):
                    callback.success() # on_connect_success
                    self.create_realtime()
                    self.realtime_check(success = lambda *a: log.info('Realtime connection successful'), # S2
                                        error = lambda *a: log.warning('Realtime connection failed')) # E2

                self.getSelfInfo(success = on_getSelfInfo_success,
                                 error = callback.error) # E1

            self.opener.open(loginForm.click(),
                             success = on_login_success,
                             error = callback.error) # E1

        self.opener.open(self.LOGIN_URL,
                         success = on_form_fetch_success,
                         error = callback.error) # E1

## Api related
    def create_api(self):
        if self.api is not None:
            raise Exception('Already have an API')

        import TaggedApi as TA
        self.api = TA.TaggedApi(self.opener, self.session_token)
        log.info('Api created')

    @callsback
    def getSelfInfo(self, callback = None):
        '''return : {Object} {'user_id', 'opt_out'}'''
        def success(result):
            self.user_id = result['user_id']
            callback.success()

        self.api.util.selfInfo(success = success,
                               error = callback.error)

    @callsback
    def getAlerts(self, callback = None):
        '''return : {Object} {'cached', 'drop_down', 'lightbox', 'icons'}'''
        def success(result):
            self.alerts = result
            callback.success()

        self.api.header.renderAlerts(success = success,
                                     error = callback.error)

    @callsback
    def getFriendsInfo(self, callback = None):
        '''return : {Object} {'total_count', 'top', 'online', 'page_offset',
                              'new_only', 'friends_info', 'starts_with'}'''
        def success(result):
            friends_info = result.get('friends_info')
            self.online_friends = friends_info[0] if friends_info else None
            callback.success()

        self.api.friends.getFriendsInfo(page_offset = 0,
                                        num_pages = 1,
                                        user_id = self.user_id,
                                        online = True,
                                        thumb_size = 's',
                                        success = success,
                                        error = callback.error)

    @callsback
    def getStatus(self, callback = None):
        '''return : {Object} {'status', 'timestamp'}'''
        def success(result):
            self.status = result
            callback.success()

        self.api.newsfeed.user.status(other_user_id = self.user_id,
                                      success = success,
                                      error = callback.error)

    @callsback
    def setStatus(self, new_message, callback = None):
        '''param  : {String} new_message New Status Message
           return : {Object} {'status', 'displayname', 'uid', 'timestamp', 'photo', 'type'}'''
        def success(result):
            self.getStatus(callback = callback)
            callback.success()

        self.api.newsfeed.event.post(data = new_message,
                                     facebook_post = False,
                                     myspace_post = False,
                                     twitter_post = False,
                                     success = success,
                                     error = callback.error)

    @callsback
    def getCandidate(self, callback = None):
        def success(result):
            self.elections_candidate = result['data'][0]
            self.elections_staff = result['data'][1]
            self.elections_projects = result['data'][2]
            callback.success() # on_getCandidate_success

        self.api.apps.elections.getCandidate(candidate_id = self.user_id,
                                             success = success,
                                             error = callback.error) # E3

    @callsback
    def getElectionsNewsfeed(self, callback = None):
        def success(result):
            events = result['data'][0]

            # Catch bad results
            if (len(events) <= 0):
                return
            else:
                # Set up list of newsfeed events
                self.elections_newsfeed = []

            # Used for collapsing sequential events that are identical
            prev_type = None;
            prev_string = None;

            for event in events:
                # Extract the data from the event
                data = event['data']
                date = event['date']
                type = event['type']

                # Get the string for this event
                strings = elections.newsfeed_strings[type]
                obj = strings['primary']

                # Create the array of substitutable sprintf params
                params = []

                switch = {'project_title' : lambda *a: params.append(data['project']['title']),
                          'target_name'   : lambda *a: params.append('<a href="%s">%s</a>' % (data['target']['elections_link'], data['target']['name'])),
                          'displayname'   : lambda *a: params.append('<a href="%s">%s</a>' % (self.elections_candidate['elections_link'], self.candidate['name'])),
                          'issue_title'   : lambda *a: params.append(data['issue']['title']),
                          'issue_vote'    : lambda *a: params.append(data['issue']['pro'] if data['vote'] else data['issue']['con']),
                          'party'         : lambda *a: params.append(data['party_id'])}

                for param in obj['params']:
                    # Emulate switch statement
                    if param in switch:
                        switch[param]()
                    if param in ['votes', 'fame', 'funds', 'collaborators', 'party_line']:
                        params.append(data[param])

                string = obj['string'] % tuple(params)

                if prev_type == type and prev_string == string:
                    last_event = self.elections_newsfeed[len(self.elections_newsfeed) - 1]
                    last_event['numTimes'] += 1;
                    last_event['time'] = TU.format_event_time(date)
                else:
                    self.elections_newsfeed.append({'feed_type'  : 'candidate',
                                                    'event_type' : type,
                                                    'string'     : string,
                                                    'numTimes'   : 1,
                                                    'time'       : TU.format_event_time(date)})
                prev_type = type
                prev_string = string

            callback.success() # S3

        self.api.apps.elections.getNews(feed_type = 'candidate',
                                        offset = 0,
                                        count = 50,
                                        success = success,
                                        error = callback.error) # E3

    @callsback
    def getPet(self, callback = None):
        def success(result):
            self.pets_pet = result['pet']
            self.pets_owner = result['owner']
            callback.success() # on_getPet_success

        self.api.apps.pets.getPetAndOwnerInfo(pet_id = self.user_id,
                                              success = success,
                                              error = callback.error) # E3

    @callsback
    def getPetsNewsfeed(self, callback = None):
        def format_link(id, name):
            link = 'noowner' if id == 0 else '#/pet/%s' % id
            return '<a class="pets-link" href="%s">%s</a>' % (link, name)

        def format_cash(amount):
            return '<span class="cash">%s</span>' % TU.format_currency(amount)

        def format_bonus(amount):
            return '<span class="cash bonus">%s</span>' % TU.format_currency(amount)

        def success(result):
            events = result['events_html']

            # Catch bad results
            if (len(events) <= 0):
                return
            else:
                # Set up list of newsfeed events
                self.pets_newsfeed = []

            # Used for collapsing sequential events that are identical
            prev_type = None;
            prev_string = None;

            for event in events:
                # Extract the data from the event
                date = event['event_date']
                type = event['event_type']

                # Get the string for the event
                strings = pets.newsfeed_strings[type]
                obj = strings['primary'](event)

                # Create the array of substitutable sprintf params
                params = []

                switch = {'pet_link'    : lambda *a: params.append(format_link(event['pet_id'], event['pet_display_name'])),
                          'owner_link'  : lambda *a: params.append(format_link(event['owner_id'], event['owner_display_name'])),
                          'target_link' : lambda *a: params.append(format_link(self.pets_pet['user_id'], self.pets_pet['display_name']))}

                for param in obj['params']:
                    # Emulate switch statement
                    if param in switch:
                        switch[param]()
                    elif param in ['purchase_price', 'setfree_price', 'earned_amount', 'profit_amount']:
                        params.append(format_cash(event[param]))
                    elif param in ['bonus_price', 'bonus_amount']:
                        params.append(format_bonus(event[param]))
                    elif param == 'achievement_name':
                        params.append(pets.achievement_strings[event['achievement_type']])
                    elif param == 'gender':
                        params.append('himself' if event[param] == 'M' else 'herself')

                string = obj['string'] % tuple(params)

                if prev_type == type and prev_string == string:
                    last_event = self.pets_newsfeed[len(self.pets_newsfeed) - 1]
                    last_event['numTimes'] += 1
                    last_event['time'] = TU.format_event_time(date)
                else:
                    self.pets_newsfeed.append({'event_type' : type,
                                               'string'     : string,
                                               'numTimes'   : 1,
                                               'time'       : TU.format_event_time(date)})
                prev_type = type
                prev_string = string

            callback.success() # S3

        self.api.apps.pets.getNewsForUser(num_events = 50,
                                          return_as_html = False,
                                          success = success,
                                          error = callback.error) # E3

## Realtime related
    def create_realtime(self):
        log.info('Create realtime')
        if self.realtime is not None:
            raise Exception('Already have Realtime')

        import TaggedRealtime as TR
        self.realtime = TR.TaggedRealtime(self.opener, self.session_token, self.user_id)

    @callsback
    def realtime_check(self, callback = None):
        log.info('Realtime check')
        def on_query_event_id_success(data, *a):
            self.register_client(data['next_event_id'], callback = callback)

        self.realtime.query_event_id(country = 'US', # TODO add to prefs
                                     success = on_query_event_id_success,
                                     error = callback.error) # E2

    @callsback
    def register_client(self, event_id, callback = None):
        log.info('Realtime register')
        def on_register_client_success(data, *a):
            # Register again, if it fails, do a check on the server
            self.register_client(data['next_event_id'],
                                 success = callback.success,
                                 error = lambda *a: self.realtime_check(callback = callback))

            # Switch
            switch = {'alerts_update'                  : lambda event_data, *a: self.alerts_update(event_data),
                      'toast_update'                   : lambda event_data, *a: self.toast_update(event_data),
                      'elections_project_contribution' : lambda event_data, *a: self.elections_project_contribution(event_data)}

            for event in data['events_data']:
                switch[event['event_type']](event['event_data'])

            callback.success() # S2

        self.realtime.register_client(event_types = ['alerts_update', 'toast_update', 'elections_project_contribution'], # TODO form this list dynamically from prefs
                                      next_event_id = event_id,
                                      success = on_register_client_success,
                                      error = callback.error) # E2

    def alerts_update(self, event, *a):
        def onclick(link):
            if link != '':
                TU.launchbrowser(link)

        # event : {'alerts_updated', 'alert_type'}
        if event['alerts_updated']:
            self.getAlerts(success = lambda *a: self.acct.set_dirty(),
                           error = lambda *a: self.set_offline(self.acct.Reasons.CONN_LOST)) # To re-render the Alerts in the infobox

            type = event['alert_type']
            strings = alerts.popup_strings

            if self.acct.whitelist[type]:
                # TODO strings[type]['link'] sometimes look like something.html?a=A&b=B. the ? part seems to get lost after the weblink
                fire('tagged.alert',
                     title = 'Tagged Alert',
                     msg = strings[type]['string'],
                     popupid = 'tagged.alert!%r' % id(self),
                     onclick = lambda *a: onclick(strings[type]['link']))

    def send_message(self, text, opts, event, *a):
        callargs = dict(to_id = event['sender_uid'],
                        subject = event['subject'] if 'subject' in event else 'digsby message',
                        message = text)

        if 'message_id' in event:
            self.api.messages.read(msg_ids = event['message_id'],
                                   success = lambda *a: log.info('Message read'),
                                   error = lambda *a: log.warning('Message not read'))
            callargs.update(parent_msg_id = event['message_id'])

        self.api.messages.send(success = lambda *a: log.info('Message sent'),
                               error = lambda *a: log.error('Send message failed'),
                               **callargs)
        return '> ' + text

    def toast_update(self, event, *a):
        def meetme(*a):
            '''meetme : {'age', 'gender', 'location', 'sender_display_name', 'sender_url',
                         'sender_thumbnail', 'sender_uid', 'meetme_url', 'isMatch'}'''
            fire_opts.update(title = _('Meet Me') + _('Match from: %s') if event['isMatch'] else _('Interest from: %s') % event['sender_display_name'],
                             msg = '')
            if event['isMatch']:
                fire_opts.update(input = lambda text, opts, *a: self.send_message(text, opts, event))

        def message(*a):
            '''message : {'sender_display_name', 'sender_url', 'sender_uid',
                          'subject', 'message', 'message_id', 'sender_thumbnail'}'''
            fire_opts.update(title = _('New Message from: %s') % event['sender_display_name'],
                             msg = strings.strip_html(event['message']).strip(),
                             sticky = True,
                             input = lambda text, opts, *a: self.send_message(text, opts, event))

        def friend_request(*a):
            '''friend_request : {'isNewFriend', 'age', 'gender', 'location', 'sender_display_name',
                                 'sender_url', 'sender_uid', 'sender_thumbnail'}'''
            fire_opts.update(title = _('%s is now your friend') if event['isNewFriend'] else _('Friend Request from: %s') % event['sender_display_name'],
                             msg = '')
            if event['isNewFriend']:
                fire_opts.update(input = lambda text, opts, *a: self.send_message(text, opts, event))

        def topics(*a):
            '''topics : {'topics_type', 'conv_id', 'post_id', 'init_text', 'text', 'sender_displayName',
                         'sender_url', 'sender_thumbnail', 'sender_uid'}'''
            pass # TODO implement topics

        fire_opts = dict(onclick = lambda *a: TU.launchbrowser(event['sender_url']),
                         popupid = 'tagged_toast!%r!%r' % (event['sender_uid'], id(self)))

        {'meetme'         : meetme,
         'message'        : message,
         'friend_request' : friend_request,
         'topics'         : topics
         }[event['sub_type']]()

        if event['sub_type'] != 'topics': # TODO implement topics
            fire('tagged.toast', **fire_opts)

    def elections_project_contribution(self, event, *a):
        '''project : {'hash', 'total_contributions', 'contributors', 'max_contribution',
                      'starter_id', 'contributions', 'id', 'starter', 'num_contributors',
                      'finish_time', 'state', 'catalog_id', 'time_remaining'}'''

        project = event['project']
        state = project['state']

        if state == -1:  # FAILED
            msg = _('not able to get fully funded')

        elif state == 0: # ACTIVE
            msg = _('contributed')

        elif state == 1: # COMPLETED
            msg = _('completed')

        fire('tagged.elections',
             title = _('Elections'),
             msg = _('A project was %s') % msg, # TODO we need the projects catalog to be more specific
             onclick = lambda *a: TU.launchbrowser('apps/elections.html'))
