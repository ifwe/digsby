'''
The protocol class is responsible for managing an MSIMApi object and converting requests dealing with buddies,
conversations, groups, etc into strings, ints, etc for the API object to send. It also binds to the API's events and
provides feedback to Digsby when information is delivered from the server.
'''
NETWORK_FLAG = 'NETWORK_FLAG'
import collections
import wx
import logging
log = logging.getLogger('msim.protocol')
# log.setLevel(1)
from base64 import b64encode
import common
import common.asynchttp as asynchttp
import contacts
import util
import util.net as net
import util.callbacks as callbacks
import util.observe as observe
from util.primitives.funcs import get, Delegate
from MSIMApi import MSIM_Api
import MSIMUtil as msimutil
import MSIMContacts as msimcontacts
import MSIMConversation
from common import pref


def needs_user_id(f):
    """ Most actions done by the user will provide a username or email address, but most protocol actions require a
        user ID. this value is not always available, so we have to use the "user_search" feature of the protocol to get
        the info we need.

        this decorator wraps a method that needs a user_id but adapts it to accept a username or email. """

    def _wrapper(self, buddy_name_or_email, *a, **k):
        log.info('doing user search for %r', buddy_name_or_email)
        if util.is_email(buddy_name_or_email):
            email = buddy_name_or_email
            name = None
        else:
            name = buddy_name_or_email
            email = None

        def success(sent, recvd):
            log.info('got success for usersearch! %r, %r', sent, recvd)
            body = recvd.get('body', {})
            buddy_id = body.get('UserID', body.get('ContactID'))
            if buddy_id is None:
                log.error('buddy_id for %r not found! probably doesn\'t exist', buddy_name_or_email)
            f(self, buddy_id, *a, **k)

        self.api.user_search(username=name, email=email, success=success)

    return _wrapper


class MyspaceIM(common.protocol):

    name = service = protocol = 'msim'

    def __init__(self, username, password, user, server=None, login_as='online', **options):
        common.protocol.__init__(self, username, password, user)
        self.api = None
        self.challenges = []
        self.root_group = contacts.Group('__msimroot__', self, '__msimroot__')

        # Keyed by user ID
        self.buddies = observe.ObservableDict()
        self.conversations = {}
        self.server = server

        # Keyed by name
        self.groups = {}
        self.block_list = []
        self.has_added_friends = options.get('has_added_friends', False)
        self._self_buddy = None

    @property
    def caps(self):
        return [common.caps.IM, common.caps.INFO, common.caps.VIDEO]

    @callbacks.callsback
    def add_group(self, name, callback=None):
        if self.groups.values():
            new_position = max(util.try_this(lambda: int(x.Position), 0) for x in self.groups.values()) + 1
        else:
            new_position = 0

        def success(sent, recvd):

            def new_group_listener(g_info):
                if g_info.get('GroupName') == name:
                    callback.success(self.get_group(name))
                    self.api.unbind('got_group', new_group_listener)

            self.api.bind('got_group', new_group_listener)
            self.request_group_list()

        self.api.set_group_details(id=None, name=name.encode('utf8'), flag=0, position=new_position, success=success,
                                   error=callback.error)

    @callbacks.callsback
    def remove_group(self, group_id, callback=None):

        def success(*a, **k):
            self.request_group_list()
            callback.success()

        self.api.delete_group(group_id, success=success, error=callback.error)

    def remove_buddy(self, buddy_id, group_id=None):
        self.api.deletebuddy(buddy_id)
        self.api.delete_contact_info(buddy_id)
        self.edit_privacy_list(remove_from_block=[buddy_id], remove_from_allow=[buddy_id])
        self.buddy_deleted(buddy_id)

    def buddy_deleted(self, id, sort=True):
        buddy = self.get_buddy(id)
        group = self.get_group(buddy.GroupID)
        if not group:
            for group in self.groups.values():
                if buddy in group:
                    break
        if group is not None and buddy in group:
            log.info('removing %r from %r', buddy, group)
            while buddy in group:
                group.remove(buddy)
            if sort:
                group.sort(key=lambda b: b.Position)
                group.notify()
                self.root_group.notify()
        elif buddy in self.root_group:
            while buddy in self.root_group:
                self.root_group.remove(buddy)
            self.root_group.notify()
        else:
            log.info('No group found for %r or buddy %r not in group', buddy.GroupName, buddy)

    def get_group(self, group_id):
        group = self.groups.get(group_id)
        if group is None:
            group = self.get_group_by_name(group_id)
        return group

    def get_group_by_name(self, name):
        for group in self.groups.values():
            if group.name == name:
                return group
        return None

    def group_for(self, buddy):
        return buddy.GroupName

    def _get_self_buddy(self):
        if self._self_buddy is None:
            self._self_buddy = self.get_buddy(self.api.userid)
        return self._self_buddy

    def _set_self_buddy(self, _val):
        pass

    self_buddy = property(_get_self_buddy, _set_self_buddy)

    def get_groups(self):
        """ Returns a list of group names. """
        return [g.name for g in self.root_group if g.id in self.groups]

    def get_buddy(self, buddy_id):
        if isinstance(buddy_id, tuple):
            buddy_id = buddy_id[0]  # group chat id = (buddyid, gid)
        if not isinstance(buddy_id, str):
            buddy_id = str(buddy_id)
        return self.buddies.get(buddy_id)

    def has_buddy_on_list(self, buddy):
        # Available keys in buddy: 'name', 'service'
        return self.get_buddy(buddy.name) is not None

    def connection_closed(self, socket=None):
        if self.state == self.Statuses.OFFLINE:
            log.info('socket closed normally')
            reason = self.Reasons.NONE
        else:
            log.info('socket closed unexpectedly (-> CONN_LOST)')
            reason = self.Reasons.CONN_LOST
        self.Disconnect(reason)
        self.on_connect = Delegate()

    def connection_failed(self):
        log.error('socket error. disconnecting with reason CONN_LOST')
        self.Disconnect(self.Reasons.CONN_LOST)
        self.on_connect = Delegate()

    def _bind_events(self, api=None):
        if api is None:
            api = self.api
        if api is None:
            return
        api.bind('connect_failed', self.connection_failed)
        api.bind('connection_closed', self.connection_closed)
        api.bind('login_challenge', self.on_login_challenge)
        api.bind('login_success', self.session_start)
        api.bind('on_error', self.on_api_error)
        api.bind('got_buddy', self._got_buddy)
        api.bind('got_buddies', self._got_buddies)
        api.bind('got_group', self._got_group)
        api.bind('got_groups', self._got_groups)
        api.bind('got_contact_info', self._got_contact_info)
        api.bind('got_group_info', self._got_group_info)
        api.bind('got_webchallenge_info', self._got_webchallenges)

        api.bind('got_im', self._got_im)
        api.bind('got_zap', self._got_zap)
        api.bind('got_typing', self._got_typing)
        api.bind('got_groupmsg', self._got_groupmsg)
        api.bind('got_buddy_presence', self.on_buddy_presence)

    def _unbind_events(self, api=None):
        if api is None:
            api = self.api
        if api is None:
            return
        api.unbind('connect_failed', self.connection_failed)
        api.unbind('connection_closed', self.connection_closed)
        api.unbind('login_challenge', self.on_login_challenge)
        api.unbind('login_success', self.session_start)
        api.unbind('on_error', self.on_api_error)
        api.unbind('got_buddy', self._got_buddy)
        api.unbind('got_buddies', self._got_buddies)
        api.unbind('got_group', self._got_group)
        api.unbind('got_groups', self._got_groups)
        api.unbind('got_contact_info', self._got_contact_info)
        api.unbind('got_group_info', self._got_group_info)
        api.unbind('got_im', self._got_im)
        api.unbind('got_zap', self._got_zap)
        api.unbind('got_typing', self._got_typing)
        api.unbind('got_groupmsg', self._got_groupmsg)
        api.unbind('got_buddy_presence', self.on_buddy_presence)

    def _got_contact_info(self, id, info, info_type):
        self._got_buddy(id, info)
        b = self.get_buddy(id)
        b.notify()
        log.info('got %r info for buddy %r. info = %r', info_type, b, info)
        self._process_queued_ims(id)
        if 'Position' in info:
            group = self.get_group_by_name(info.get('GroupName'))
            if group is not None:
                group.sort(key=lambda b: b.Position)
                group.notify()
                self.root_group.sort(key=lambda b: b.Position)
                self.root_group.notify()

    def _got_group_info(self, gid, info):
        g = self.get_group(gid)
        g.update_info(info)
        g.notify()
        self.root_group.sort(key=lambda b: b.Position)
        self.root_group.notify()

    def _update_pending_buddy_properties(self, id, props, notify):
        self._pending_props[str(id)].update(props)
        self._pending_notify[str(id)] |= notify

    def _apply_pending_buddy_properties(self, id):
        props = self._pending_props.pop(str(id), {})
        if props:
            log.info('applying pending properties for %r: %r', id, props)
            notify = self._pending_notify.pop(str(id), False)
            self._update_buddy_properties(id, props, notify)

    def _update_buddy_properties(self, id, props, notify=False):
        buddy = self.get_buddy(id)
        if buddy is None:
            self._update_pending_buddy_properties(id, props, notify)
            log.info('applying properties to %r later. props = %r', id, props)
            return
        for key, val in props.items():
            setattr(buddy, key, val)
        if notify:
            for key, val in props.items():
                buddy.notify(key)

    def on_buddy_presence(self, id, status, status_message):
        should_notify = True
        self._update_buddy_properties(id, {'status': status, 'status_message': status_message or None},
                                      notify=should_notify)

    @common.action(lambda self, *a, **k: (True if self.state == self.Statuses.OFFLINE else None))
    def Connect(self, *a, **k):
        if self.state == self.Statuses.OFFLINE or self.api is None:
            self._queued_ims = collections.defaultdict(list)
            self._pending_props = collections.defaultdict(dict)
            self._pending_notify = collections.defaultdict(bool)
            del self.challenges[:]
            self.change_reason(self.Reasons.NONE)
            self.change_state(self.Statuses.CONNECTING)
            log.debug('connecting myspace')
            self._init_api()
            self.api.connect(self.server)
            return
        log.critical('Not connecting. state=%r, reason=%r', self.state, self.offline_reason)

    def _init_api(self):
        api = MSIM_Api()
        self._bind_events(api)
        self.api = api

    def _send_logout(self):
        if self.api is not None:
            self.api.logout()

    def Disconnect(self, reason=None):
        log.info('Disconnecting. state=%r, reason=%r', self.state, self.offline_reason)
        if self.state != self.Statuses.OFFLINE:
            self._unregister_buddies()
            self.groups.clear()
            self.root_group[:] = []
            self.challenges[:] = []
            try:
                del self.sesskey
            except AttributeError:
                pass
            self.set_offline(reason)
            self._send_logout()
            if self.api is not None:
                api, self.api = self.api, None
                self._unbind_events(api)
                api.disconnect()
            common.protocol.Disconnect(self)

    def on_api_error(self, reason):
        real_reason = {'connection_lost': self.Reasons.CONN_LOST,
                       'session_expired': self.Reasons.CONN_LOST,
                       'auth_error': self.Reasons.BAD_PASSWORD,
                       'other_user': self.Reasons.OTHER_USER,
                       }.get(reason)

        self.Disconnect(real_reason)

    def on_login_challenge(self, nonce):
        self.change_state(self.Statuses.AUTHENTICATING)
        self.api.send_login_response(self.username, self.password, nonce)

    def session_start(self):
        log.info('session started')
        self.change_state(self.Statuses.LOADING_CONTACT_LIST)
        self.request_self_buddy_info()
        self.request_group_list()

    @callbacks.callsback
    def request_group_list(self, callback=None):
        self.api.request_group_list(callback=callback)

    def request_contact_list(self):
        self.api.request_contact_list()

    def _got_webchallenges(self, challenges):
        self.challenges.extend(Challenge(**x) for x in challenges)

    def _got_group(self, g_info):
        group = self.get_group_by_name(g_info.get('GroupName'))
        if group is None:
            group = msimcontacts.MSIM_Group(g_info, self)
            self.groups[group.id] = group
        if group not in self.root_group:
            self.root_group.append(group)

    def _got_groups(self, all_groups):
        group_ids = set(g['GroupID'] for g in all_groups)
        log.info('Got groups!')
        for group_id in self.groups.keys():
            if group_id not in group_ids:
                old_group = self.groups.pop(group_id)
                if old_group in self.root_group:
                    self.root_group.remove(old_group)
        self.root_group.sort(key=lambda b: b.Position)
        self.root_group.notify()
        self.request_contact_list()

    def _got_buddy(self, id, info):
        buddy = self.get_buddy(id)
        if buddy is None:
            buddy = msimcontacts.MSIM_Buddy(info, self)
            self.buddies[id] = buddy
        else:
            buddy.update_info(info)
        self.buddy_added(id)
        self._apply_pending_buddy_properties(id)

    def buddy_added(self, id):
        buddy = self.get_buddy(id)
        if buddy.visible:
            group = self.get_group_by_name(buddy.GroupName)
            if group is None:
                group = self.root_group
            if buddy not in group:
                group.append(buddy)
            for g in self.groups.values():
                if g is not group:
                    while buddy in g:
                        g.remove(buddy)

    def _got_buddies(self, all_buddies):
        buddy_ids = set(b.get('ContactID', b.get('UserID')) for b in all_buddies)
        for buddy_id in self.buddies.keys():
            buddy = self.get_buddy(buddy_id)
            if not (buddy.visible and buddy_id in buddy_ids):
                self.buddy_deleted(buddy_id, sort=False)
        for group in list(self.groups.values()):
            group.sort(key=lambda b: b.Position)
            group.notify()
        self.root_group.notify()
        self._on_login()

    def convo_for(self, buddy):
        buddy_id = getattr(buddy, 'id', buddy)
        try:
            return self.conversations[buddy_id]
        except KeyError:
            c = MSIMConversation.MSIMConversation(self, buddy_id)
            self.conversations[buddy_id] = c
            return c

    chat_with = convo_for

    def _got_im(self, buddy_id, message):
        log.info('incoming IM from %r: %r', buddy_id, message)
        if not isinstance(buddy_id, tuple):
            queue_id = buddy_id = str(buddy_id)
            buddy = self.get_buddy(buddy_id)
        else:
            buddy = self.get_buddy(buddy_id[-1])
            buddy_id = buddy_id[:2]
        if buddy is None or buddy.alias == buddy_id:
            self._queue_im(queue_id, message)
            self.request_buddy_info(buddy_id)
        else:
            c = self.convo_for(buddy_id)
            c.received_message(buddy, message)

    def _queue_im(self, buddy_id, message):
        self._queued_ims[buddy_id].append(message)

    def _process_queued_ims(self, who):
        ims = self._queued_ims.pop(who, [])
        for im in ims:
            self._got_im(who, im)

    def _got_zap(self, buddy_id, zaptxt):
        buddy = self.get_buddy(buddy_id)
        c = self.convo_for(buddy)
        c.received_zap(buddy, zaptxt)

    def _got_typing(self, buddy_id, is_typing):
        buddy = self.get_buddy(buddy_id)
        c = self.convo_for(buddy)
        c.received_typing(buddy, is_typing)

    def _got_groupmsg(self, source_id, group_id, actor_id, msg_text):
        log.info('incoming group IM from (%r, %r, %r): %r', source_id, group_id, actor_id, msg_text)
        c = self.convo_for(source_id)
        c.received_group_message(group_id, actor_id, msg_text)

    def user_search(self, username=None, email=None):
        self.api.user_search(username, email)

    def send_typing(self, who, typing):
        self.api.send_typing(who, typing)

    @callbacks.callsback
    def send_message(self, buddy, message, callback=None, **kwds):
        log.info_s('Sending message to %r. message = %r, format = %r, kwds = %r', buddy, message, format, kwds)
        self.api.send_im(buddy.id, message, callback=callback)

    def request_self_buddy_info(self):
        self.api.request_self_im_info()
        self.api.request_self_social_info()

    def request_buddy_info(self, userid):

        @common.netcall
        def _do_request():
            self.api.request_contact_general_info(userid)
            self.api.request_contact_im_info(userid)
            self.api.request_contact_social_info(userid)

    def _on_login(self):
        self.change_state(self.Statuses.ONLINE)
        if not self.has_added_friends:
            acct = common.profile.find_account(self.username, self.protocol)
            if acct is not None:
                self.has_added_friends = acct.has_added_friends = True
                common.profile.update_account(acct)
            wx.CallAfter(self.ask_add_buddies)

    def ask_add_buddies(self):
        import msim.myspacegui.prompts as prompts
        prompts.AddBuddiesPrompt(success=self.autoadd_buddies)

    def autoadd_buddies(self, which):
        if which == 'cancel':
            return
        elif which == 'all':
            self.api.add_all_friends(GroupName='IM Friends')
        elif which == 'top':
            self.api.add_top_friends(GroupName='IM Friends')

    def request_challenges(self):
        self.api.request_webchlg()

    def set_buddy_icon(self, icondata):
        pass

    def on_login(self):
        self.change_state(self.Statuses.ONLINE)

    @needs_user_id
    def add_buddy(self, buddy_id, group_id, service=None, reason=u''):
        assert service in (None, self.service)
        self.api.addbuddy(buddy_id, reason.encode('utf8'))
        self.edit_privacy_list(remove_from_block=[buddy_id], add_to_allow=[buddy_id])
        buddy = self.get_buddy(buddy_id)
        group = self.get_group(group_id)
        infodict = buddy.get_infodict()
        infodict.update(Visibility='1', GroupName=group.GroupName, Position='1000', NameSelect='0')
        self.api.set_contact_info(buddy_id, infodict)
        buddy.update_info(infodict, 'im')
        self.buddy_added(buddy_id)
        group.sort(key=lambda b: b.Position)
        group.notify()
        if group is not self.root_group:
            while buddy in self.root_group:
                self.root_group.remove(buddy)
        self.root_group.notify()

    def block(self, buddy, block=True):
        if block:
            self.edit_privacy_list(remove_from_allow=[buddy.id], add_to_block=[buddy.id])
        else:
            self.edit_privacy_list(add_to_allow=[buddy.id], remove_from_block=[buddy.id])

    @callbacks.callsback
    def move_buddy(self, contact, to_gname, from_gname, index, callback=None):
        start_group = self.get_group(from_gname)
        end_group = self.get_group(to_gname)
        log.info('Moving %r from %r to %r (at position %r)', contact, to_gname, from_gname, index)
        if end_group is None:
            log.info('Group %r doesn\'t exist, bailing', to_gname)
            return
        if end_group is not None:
            buddies_to_shift = end_group[index:]
            for buddy in reversed(buddies_to_shift):
                new_pos = str(end_group.index(buddy) + 1)
                d = {'ContactID': buddy.id,
                     'Position': new_pos,
                     'GroupName': buddy.GroupName}
                self.api.set_contact_info(buddy.id, d)
                buddy.update_info(d, 'im')

        d = {'ContactID': contact.id,
             'Position': str(index),
             'GroupName': end_group.GroupName}
        self.api.set_contact_info(contact.id, d)
        contact.update_info(d, 'im')
        end_group.insert(index, contact)
        if start_group is not None:
            old_position = start_group.index(contact)
            buddies_to_shift = start_group[old_position + 1:]
            for buddy in buddies_to_shift:
                new_pos = str(start_group.index(buddy) - 1)
                d = {'ContactID': buddy.id,
                     'Position': new_pos,
                     'GroupName': buddy.GroupName}
                self.api.set_contact_info(buddy.id, d)
                buddy.update_info(d, 'im')
            while contact in start_group:
                start_group.remove(contact)
        while contact in self.root_group:
            self.root_group.remove(contact)
        if start_group is not None:
            start_group.sort(key=lambda b: b.Position)
            start_group.notify()
        if end_group is not None:
            end_group.sort(key=lambda b: b.Position)
            end_group.notify()
        self.root_group.sort(key=lambda b: b.Position)
        self.root_group.notify()
        callback.success()

    def edit_privacy_list(self,
                          add_to_block=None,
                          add_to_allow=None,
                          remove_from_block=None,
                          remove_from_allow=None,
                          presence_vis=None,
                          contact_vis=None,
                          ):

        self.api.edit_privacy_list(add_to_block=add_to_block,
                                   add_to_allow=add_to_allow,
                                   remove_from_block=remove_from_block,
                                   remove_from_allow=remove_from_allow,
                                   presence_vis=presence_vis,
                                   contact_vis=contact_vis)

    @property
    def popupids(self):
        return set((self, ))

    @callbacks.callsback
    def get_buddy_icon(self, buddy_name, callback=None):
        b = self.get_buddy(buddy_name)
        if b is None:
            return callback.error(Exception('no buddy named %r', buddy_name))
        if not b.icon_hash:
            return callback.success(None)
        url = b.icon_hash

        def success(req, resp):
            b.cache_icon(resp.read(), url)
            b.notify('icon')
            log.error('got buddy icon for %r: %r', b, resp)
            callback.success()

        def error(req, exc):
            log.error('error requesting buddy icon for %r: %r', b, exc)
            callback.error(exc)

        asynchttp.httpopen(url, headers={'User-Agent': 'AsyncDownloadMgr'}, success=success, error=error)

    def set_message(self, message='', status='', format=None, **k):
        self._set_status(status, message.encode('utf8'))

    def set_idle(self, idle):
        log.info('set_idle(%r)', idle)
        if idle:
            self._old_status = self._status
            self._set_status('idle')
        else:
            self._set_status(getattr(self, '_old_status', None) or 1)
            self._old_status = None

    def set_invisible(self, invis):
        if invis:
            self._old_status = self._status
            self._set_status('invisible')
        else:
            self._set_status(getattr(self, '_old_status', None) or 1)
            self._old_status = None

    def _set_status(self, status, status_string=None, locstring=None):
        log.info_s('_set_status(%r, %r, %r)', status, status_string, locstring)
        if status_string is None:
            status_string = getattr(self, '_status_string', '')
        if locstring is None:
            locstring = getattr(self, '_loc_string', '')
        self._status = status
        self._status_string = status_string
        self._loc_string = locstring
        if status is None:
            log.info('got None for _set_status')
            return
        self.api.set_status(msimutil.status_to_int(status), status_string, locstring)

    def alert_update(self):
        log.info('Sending update request')
        self.api.request_social_alerts()

    def launchbrowser(self, url):
        wx.LaunchDefaultBrowser(url)

    def openurl(self, name, userid=None):
        if get(self, 'sesskey', False) and pref('privacy.www_auto_signin', False):
            url = self.getURL(name, userid)
        else:
            url = 'http://www.myspace.com'
        self.launchbrowser(url)

    def make_chl_response(self, s):
        return b64encode(msimutil.crypt(s, self.password.lower())).strip('=')

    def getURL(self, s, userid=None, pop=True):
        '''
        possible values of s include:
            friendmoods
            viewbirthdays
            home
        '''
        if userid is None:
            try:
                userid = self.api.userid
            except AttributeError:
                return 'http://www.myspace.com'
        chl = self.next_chl(pop)
        if chl is None:
            return 'http://www.myspace.com'
        n = msimutil.roflcopter(chl.key, self.api.sesskey, self.api.userid)
        return net.UrlQuery('http://home.myspace.com/Modules/IM/Pages/UrlRedirector.aspx',
                            challenge='%s-%s-%s' % (n, self.api.userid, self.api.sesskey),
                            response=str(self.make_chl_response(chl.data)),
                            target=s,
                            targetid=userid)

    def next_chl(self, pop=True):
        try:
            if pop:
                f = list.pop
            else:
                f = list.__getitem__
            return f(self.challenges, 0)
        except IndexError:
            # No challenges
            return None
        finally:
            if len(self.challenges) == 3:
                log.info('requesting more challenges')
                self.request_challenges()

    @classmethod
    def get_privacy_panel_class(cls):
        import msim.myspacegui.privacy as priv_gui
        return priv_gui.MSIMPrivacyPanel

    def save_userinfo(self, settings=None):
        if settings is None:
            settings = self.self_buddy.IMSettings
        self.self_buddy.update_info(settings)
        self.api.set_user_prefs(settings)

    def set_userpref(self, **k):
        self.save_userinfo(k)

    def rename_group(self, group_id, new_name):
        group = self.get_group(group_id)
        group.GroupName = new_name
        info = group.get_infodict()
        self.api.set_group_details(info)
        self.root_group.notify()

    def send_exitchat(self, buddy_id, group_id):
        self.api.send_exitchat(buddy_id, group_id)


class Challenge(object):

    def __init__(self, Challenge, ChallengeData):
        self.key = int(Challenge)
        self.data = ChallengeData

    def __repr__(self):
        return '<Challenge key=%s data=%s>' % (self.key, self.data)


import gui.infobox.providers as gui_providers
import gui.infobox.interfaces as gui_interfaces
import protocols


class MSIMBuddyIB(gui_providers.InfoboxProviderBase):

    javascript_libs = []
    protocols.advise(asAdapterForTypes=[msimcontacts.MSIM_Buddy],
                     instancesProvide=[gui_interfaces.IInfoboxHTMLProvider])

    def __init__(self, buddy):
        gui_providers.InfoboxProviderBase.__init__(self)
        self.buddy = buddy

    def get_html(self, *a, **opts):
        self.buddy._dirty = False
        return gui_providers.InfoboxProviderBase.get_html(self, **opts)

    def get_app_context(self, ctxt_class):
        import path
        return ctxt_class(path.path(__file__).parent.parent, self.buddy.protocol.name)

    def get_context(self):
        import gui.skin
        import gui.buddylist.renderers as renderers
        ctxt = gui_providers.InfoboxProviderBase.get_context(self)
        proto = self.buddy.protocol
        ctxt.update(
          proto=proto,
          self_buddy=proto.self_buddy,
          buddy=self.buddy,
          skin=gui.skin,
          renderers=renderers,
          common=common,
        )
        return ctxt

    @property
    def _dirty(self):
        return getattr(self.buddy, '_dirty', True)
