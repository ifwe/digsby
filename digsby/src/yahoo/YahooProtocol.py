"""

Yahoo! Messenger Protocol

"""
from __future__ import with_statement
from .login import async_get_load_balance_info, LOAD_BALANCERS, HTTP_LOAD_BALANCERS
from .YahooSocket import YahooSocketBase
from .endpoints import ALL_PORTS, S1_PORTS, S3_PORTS, ServerEndpoint, HTTPEndpoint

import heapq

import logging, sys, random, urllib2
from time import time
from datetime import datetime
from urllib2 import urlopen, Request
from collections import defaultdict

import common
from common import action, netcall
from common.Buddy import get_bname
from common.Buddy import get_bname as _buddy_name
from contacts import Group
from .YahooConversation import YahooConvo, YahooChat, YahooConf
from .yahoobuddy import YahooBuddy, YahooContact
from .yahoolookup import ykeys, commands, statuses
from .yahooutil import add_cookie, yiter_to_dict
from .yfiletransfer import YahooHTTPIncoming
from .peerfiletransfer import YahooPeerFileTransfer
from .yahoologinsocket import YahooLoginSocket
from .yahooP2Pprotocol import YahooP2P, ack_message
from . import yahooformat
from . import yahoo360

from util.observe import ObservableDict
from util import Storage, callsback, DefaultCallback, threaded, Timer, \
    is_email, traceguard, groupify, UrlQuery
from util.xml_tag import tag
from util.xml_tag import post_xml
from util import dictreverse

from . import yahoohttp

import traceback
from util.primitives.mapping import lookup_table

KEEPALIVE_SECONDS = 60
PING_SECONDS = 60 * 60

log = logging.getLogger('yahoo'); info = log.info; error = log.error

MOVE        = '240'

BEGIN_ENTRY = 'begin_entry'
END_ENTRY   = 'end_entry'
BEGIN_MODE  = 'begin_mode'
END_MODE    = 'end_mode'

LIST_COMMANDS = frozenset((BEGIN_ENTRY, END_ENTRY, BEGIN_MODE, END_MODE))
#313, 314

GROUP       = '318'
CONTACT     = '319'
BLOCK_ENTRY = '320'
#312, 315, 444

BLIST_ENTRIES = lookup_table({'group':'318', 'contact':'319', 'block_entry':'320'})


PROTOCOL_CODES = {'1':'lcs','2':'msn', '9':'sametime', '100':'pingbox'}
PROTOCOL_CODES.update(dictreverse(PROTOCOL_CODES))

# These base "normal set" of statuses come in from the network as integer codes.
nice_statuses = {
  1: 'Be Right Back',
  2: 'Busy',
  3: 'Not At Home',
  4: 'Not At My Desk',
  5: 'Not In Office',
  6: 'On the Phone',
  7: 'On Vacation',
  8: 'Out To Lunch',
  9: 'Stepped Out',
}

nice_statuses.update((v.lower(), k) for k, v in nice_statuses.items())

class YahooBuddies(ObservableDict):
    'dict subclass, creates YahooBuddy objects on demand'

    def __init__(self, protocol):
        ObservableDict.__init__(self)
        self.protocol = protocol

    def __getitem__(self, buddy_name):
        if not isinstance(buddy_name, basestring):
            raise TypeError('buddy name must be a string (you gave a %s)' % type(buddy_name))

        nice_name = buddy_name
        buddy_name = buddy_name.lower()

        try:
            return ObservableDict.__getitem__(self, buddy_name)
        except KeyError:
            return self.setdefault(buddy_name, YahooBuddy(nice_name, self.protocol))

class YahooError(Exception):
    pass

class YahooProtocol(common.protocol):
    'A connection to the Yahoo Messenger network.'

    name = 'yahoo'

    # Message Formatting
    message_sizes = [6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32]
    message_bg = False

    supports_group_chat = True

    @classmethod
    def email_hint(cls, contact):
        if is_email(contact.name):
            return contact.name
        else:
            return contact.name + '@yahoo.com'

    def __init__(self, username, password, user, server, sign_on_invisible=False,
                 block_unknowns=False, use_http_only=False, **extra_args):
        if '@yahoo.' in username:
            username = username.split('@yahoo.')[0]
        common.protocol.__init__(self, username, password, user)
        self.init_server = server
        self.session_id = 0
        self.buddies = YahooBuddies(self)
        self.self_buddy = self.buddies[self.username]
        self.cookies = {}
        self._status_message = u''
        self._old_status = 'offline'

        self.block_unknowns = block_unknowns
        self.use_http_only  = use_http_only

        self.conversations = ObservableDict()
        self.conferences   = {}
        self.chats = {}
        self.file_transfers = {}
        self.peertopeers    = {}

        self.picture_checksum = ''
        self.picture_url      = ''

        root = Group('Root', self, 'Root')
        self.groups = {}
        self.root_group = root

        self.relayhost = 'relay.msg.yahoo.com'

        self.last_contact_get = 0

        self.loadbalanced_servers = []
        self.loadbalance_success_count = 0
        self.loadbalance_error_count = 0
        self.loadbalanced_http_servers = []
        self.loadbalance_http_success_count = 0
        self.loadbalance_http_error_count = 0
        self.endpoints = []

        self.callbacks = defaultdict(lambda: DefaultCallback)

        self.keepalive_timer = Timer(KEEPALIVE_SECONDS, self.send_keepalive) # seconds
        self.ping_timer = Timer(PING_SECONDS, self.send_ping) # seconds

        self.init_buddylist()

    def send_keepalive(self):
        if self.state not in (self.Statuses.ONLINE, self.Statuses.CONNECTING):
            self.keepalive_timer.stop()
            return
        else:
            log.info('sending a keepalive')
            netcall(lambda: self.send('keepalive', 'available', {'away_buddy':
                                                                 self.self_buddy.name}))
            self.keepalive_timer.start()

    def send_ping(self):
        if self.state not in (self.Statuses.ONLINE, self.Statuses.CONNECTING):
            self.ping_timer.stop()
            return
        else:
            log.info('sending a PING')
            netcall(lambda: self.send('ping', 'available'))
            self.ping_timer.start()

    @property
    def caps(self):
        from common import caps
        return [caps.INFO,
                caps.IM,
                caps.FILES,
                caps.EMAIL,
                caps.SMS,
                caps.BLOCKABLE,
                caps.VIDEO]

    def get_group(self, groupname):
        return self.groups.get(groupname, None)

    @action(lambda self, *a, **k: True if self.state == self.Statuses.OFFLINE else None)
    def Connect(self, invisible = False):
        log.info('%r.Connect(invisible = %s)', self, invisible)

        self.silence_notifications(15)
        self.initial_status = 'available' if not invisible else 'invisible'
        self.connection_stage = 0
        self.continue_connect()

    def continue_connect(self):
        if self.connection_stage == 0:
            if self.use_http_only:
                self.connection_stage = 2
            else:
                self.connection_stage = 1
                self.connect_stage1()
                return True
        if self.connection_stage == 1:
            if not self.endpoints:
                self.connection_stage = 2
        if self.connection_stage == 2:
            self.connection_stage = 3
            self.connect_stage2()
            return True
        if self.connection_stage == 3:
            if not self.endpoints:
                self.connection_stage = 4
                return self.connect_stage3()
        if self.connection_stage == 4:
            if not self.endpoints:
                self.connection_stage = 5
                if not self.use_http_only:
                    return self.connect_stage4()
        if self.connection_stage == 5:
            if not self.endpoints:
                return self.set_disconnected(self.Reasons.CONN_FAIL)
        self._reconnect()

    def connect_stage1(self):
        '''get load balancer info'''
        get_info = callsback(async_get_load_balance_info)
        for server in LOAD_BALANCERS:
            get_info(server, success = self.stage1_lb_success,
                             error   = self.stage1_lb_error,
                             timeout = self.stage1_lb_error) #if ever we do timeouts
    def connect_stage2(self):
        '''get load balancer info'''
        get_info = callsback(async_get_load_balance_info)
        for server in HTTP_LOAD_BALANCERS:
            get_info(server, success = self.stage2_lb_success,
                             error   = self.stage2_lb_error,
                             timeout = self.stage2_lb_error) #if ever we do timeouts

    def stage1_lb_success(self, server):
        self.loadbalance_success_count += 1
        self.loadbalanced_servers.append(server)
        for port in S1_PORTS:
            s = ServerEndpoint(server, port)
            heapq.heappush(self.endpoints, s)
        if len(self.loadbalanced_servers) == 1:
            self.continue_connect()

    def stage1_lb_error(self, error=None):
        self.loadbalance_error_count += 1
        if self.loadbalance_error_count >= len(LOAD_BALANCERS):
            self.continue_connect()

    def stage2_lb_success(self, server):
        self.loadbalance_http_success_count += 1
        self.loadbalanced_http_servers.append(server)
        s = HTTPEndpoint(server)
        heapq.heappush(self.endpoints, s)
        if len(self.loadbalanced_http_servers) == 1:
            self.continue_connect()

    def stage2_lb_error(self, error=None):
        self.loadbalance_http_error_count += 1
        if self.loadbalance_http_error_count >= len(HTTP_LOAD_BALANCERS):
            self.continue_connect()

    def connect_stage3(self):
        '''remaining yahoo servers, remaining ports for initial set'''
        for server in self.loadbalanced_servers:
            for port in S3_PORTS:
                s = ServerEndpoint(server, port)
                heapq.heappush(self.endpoints, s)
        self.continue_connect()

    def connect_stage4(self):
        '''remaining yahoo servers, remaining ports for initial set'''
        for port in ALL_PORTS:
            s = ServerEndpoint('scs.msg.yahoo.com', port)
            heapq.heappush(self.endpoints, s)
        self.continue_connect()

    def _reconnect(self):
        if not self.endpoints:
            return self.continue_connect()
        self.change_state(self.Statuses.CONNECTING)
        self.socket = heapq.heappop(self.endpoints).make_socket(self)
        self.keepalive_timer.start()
        self.ping_timer.start()

    def fix_unknown_statuses(self):
        keys = self.buddies.keys()
        for k in keys:
            if self.buddies[k].status == 'unknown':
                self.buddies[k].status = 'offline'
        for k in keys:
                self.buddies[k].notify()


    @action(lambda self: True if self.state != self.Statuses.OFFLINE else None)
    def Disconnect(self):
        self.set_disconnected()

    def set_disconnected(self, reason = None):
        if self.state in (self.Statuses.CONNECTING,
                          self.Statuses.AUTHENTICATING) and \
               reason in (self.Reasons.CONN_FAIL,
                          self.Reasons.CONN_LOST):
            if not self.endpoints:
                if self.connection_stage == 5:
                    self.set_offline(reason)
                elif self.use_http_only and (self.loadbalance_http_error_count + self.loadbalance_http_success_count) >= len(HTTP_LOAD_BALANCERS):
                    self.set_offline(reason)
        else:
            self.set_offline(reason)
        self.disconnect()

    def disconnect(self):
        try:
            self.socket.close()
        except Exception, e:
            traceback.print_exc()
            #TODO: find better alternative here
            # also...what are the implications of disconnecting while waiting for a
            # return on some data inside a generator?
            pass

        self._clear_timers()

        for peer in self.peertopeers.values():
            try:
                peer.Disconnect()
            except Exception:
                traceback.print_exc()
        common.protocol.Disconnect(self)
        if self.state in (self.Statuses.CONNECTING,
                          self.Statuses.AUTHENTICATING):
            self._reconnect()

    def _clear_timers(self):
        # timers might be deleted by send_keepalive at any time
        kt = getattr(self, 'keepalive_timer', None)
        if kt is not None:
            kt.stop()

        pt = getattr(self, 'ping_timer', None)
        if pt is not None:
            pt.stop()


    #
    #

    def group_for(self, contact):
        group, name = contact.id
        return group.name

    #
    # Buddy Icons
    #

    def set_buddy_icon(self, imgdata):
        'Upload a buddy icon.'

        from .yfiletransfer import set_buddy_icon
        h = hash(imgdata)
        self.picture_checksum = h
        self.self_buddy.cache_icon(imgdata, h)
        set_buddy_icon(self, imgdata)

    def picture_upload_brb(self, to, filename, url, expires):
        log.info('bicon upload success (%s), expires %s', url, expires)

        icon_flags = dict(show = '2')
        selfname   = self.self_buddy.name
        self.picture_url = url

        self.send('picture_checksum', 'available', [
          'frombuddy', selfname,
          '212',       '1',
          'checksum',  self.picture_checksum,])
#        self.send('avatar_update', 'available', ['conf_from', selfname,
#                                                 'avatar_flag', '2'])
#        self.send('picture_update', 'available', [
#                  'icon_flag',  icon_flags['show'],
#                  'to',         selfname,
#                  'frombuddy',  selfname])

    def _open_url_with_cookies(self, url, method='GET'):
        opener = urllib2.build_opener()
        opener.addheaders.append(('Cookie', self.cookie_str))
        request = urllib2.Request(url)
        request.get_method = lambda: method
        resp = opener.open(request)
        return resp

    def _request_icon(self, buddy):
        url = 'http://rest-img.msg.yahoo.com/v1/displayImage/custom/yahoo/%s?src=orion&chksum'
        url = url % buddy.name
        log.info('downloading buddy icon for %r from %r', buddy, url)
        data = self._open_url_with_cookies(url).read()
        buddy.cache_icon(data, buddy.icon_hash)

    def get_buddy_icon(self, buddy):
        "Ask the server for a buddy's icon. Takes a buddy tuple, object, or name."

        if isinstance(buddy, basestring):
            buddy = self.buddies[buddy]

        if _buddy_name(buddy) != self.self_buddy.name:
            self._request_icon(buddy)

    def picture_brb(self, buddy, flag, to, url = None, checksum = None):
        'Server response for a buddy icon.'
        if flag == '2':
            info('picture_brb for %s', buddy)
            info('  flag: %s', flag)
            info('  url: %r', url)
            info('  checksum: %r', checksum)


        elif flag == '1':
            self.send('picture', 'available', [
                      'frombuddy',       to,
                      'to', buddy,
                      'flag', '2',
                      'url', self.picture_url,
                      'checksum',  self.picture_checksum,
                      ])
        else:
            log.warning('unknown flag "%s" in picture_brb', flag)

    def picture_checksum_brb(self, buddy, checksum, url=None):
        "Server is sending you a buddy's icon checksum."

        log.info('picture_checksum_brb gave checksum for %r: %r', buddy, checksum)
        buddy = self.buddies[buddy]
        buddy.setnotifyif('icon_hash', checksum)
        log.info('icon_hash:    %r', buddy.icon_hash)
        log.info('_cached_hash: %r', buddy._cached_hash)

    def picture_update_brb(self, buddy, to, icon_flag):
        'Server is informing you of an icon "enabled" change.'

        log.info("%s's buddy icon_flag: %s", buddy, icon_flag)

        selfname = self.self_buddy.name

        if buddy == selfname and to == selfname:
            # server is informing us that our icon state has been successfully modified...
            # it is our job (the client's) to inform friends on our buddylist.
            self.send('picture_checksum', 'available', [
                      'checksum',  hash(self.self_buddy.icon),
                      '212',       '1',
                      'frombuddy', selfname])

            online_buddies = [b for b in self.buddies.values() if b.online and b is not self.self_buddy]
            log.info('sending picture_checksum updates to %d buddies', len(online_buddies))
            for b in online_buddies:
                self.send('picture_update', 'available',
                    frombuddy = selfname, to = b.name, icon_flag = icon_flag)

        if icon_flag == '0': # zero means don't show icon
            self.buddies[buddy].setnotifyif('icon_disabled', True)
        elif icon_flag == '2':
            self.buddies[buddy].setnotifyif('icon_disabled', False)

    def avatar_update_brb(self, buddy, avatar_flag, checksum=None):
        buddy = self.buddies[buddy]

        if avatar_flag == '0':
            buddy.icon_disabled = True
        elif avatar_flag == '2':
            buddy.icon_disabled = False
        buddy.notify()

    def get_profile(self, name):
        print "Yahoo: get_profile " + name

    #
    # Chat
    #

    def send_chat_req(self, buddy, room_name, message = None):
        buddy = _buddy_name(buddy)
        myname = self.self_buddy.name

        self.send('confinvite', 'available',
            frombuddy = myname,
            confbuddy = myname,
            conf_name = room_name,
            conf_invite_message = message or 'Join My Conference...',
            conf_tobuddy = buddy)

    def chatjoin_brb_raw(self, ydict_iter):
        "Received when you join a chatroom."

        room = None
        for k, v in ydict_iter:
            # room name
            if k == ykeys.room_name:
                if not room:
                    if v not in self.chats:
                        info('creating YahooChat %s', v)
                        self.chats[v] = room = YahooChat(self, name = v)
                        cb = self.callbacks.pop('chatjoin.%s' % v)
                        cb.success(room)
                    else:
                        room = self.chats[v]
            # Topic
            elif k == ykeys.topic:
                info('setting topic %s', v)
                room.topic = v
            # A buddy.
            elif k == ykeys.chat_buddy:
                if room:
                    room.buddy_join( self.buddies[v] )
                else:
                    log.warning( 'got a buddy with no room: %s', v )


    def comment_brb(self, room_name, chat_buddy, chat_message):
        if room_name in self.chats:
            self.chats[room_name].incoming_message(self.buddies[chat_buddy],
                                                   yahooformat.tohtml(chat_message))
        else:
            info('unhandled chat message for room %s...%s: %s',
                     room_name, chat_buddy, chat_message)


    def chatexit_brb(self, room_name, chat_buddy):
        "Received when someone leaves a chatroom."

        if room_name not in self.chats:
            log.error('Got a CHATEXIT for %s in room %s', chat_buddy, room_name)
            log.error('chats: ' + repr(self.chats))
            return

        info('chatexit_brb for %s in %s, calling buddy_leave',
                 chat_buddy, room_name)
        self.chats[room_name].buddy_leave(self.buddies[chat_buddy])

    @callsback
    def join_chat_room(self, room_name, callback = None):
        if room_name is None:
            room_name = 'DigsbyChat%s' % random.randint(0, sys.maxint)

        myname = self.self_buddy.name

        query = {'109': myname,
                 '1':myname,
                 '6':'abcde',
                 '98':'us',
                 '135':'ym8.0.0.505'}
        self.send('chatonline', 'available', query)
        self.send('chatjoin', 'available',{
            'frombuddy':myname,
            'room_name': room_name,
            '62':'2'
        })

        self.callbacks['chatjoin.%s' % room_name] = callback


    def join_in_chat(self, buddy):
        'Finds and joins a chat room a buddy is in.'
        me = self.self_buddy.name

        # Send a chat "online" before requesting the room.
        self.socket.chatlogon('chatgoto', 'available', dict(
            chat_buddy = _buddy_name(buddy),
            frombuddy = me,
            chat_search = '2',
        ))

    def chatgoto_cancel(self):
        '''
        Server error message for "Join in Chat" when the buddy you are joining
        isn't in a chat room.
        '''
        self.hub.on_error(YahooError('User is not in a chat room.'))

    def set_message(self, message, status='away', url = '', format = None):
        'Sets message [and/or status].'

        info('setting status: status=%r url=%r', status, url)
        log.info_s('  message: %r', message)

        avail = status.lower() in ('available', 'online')

        self.status = status
        self._status_message = u''

        if message.lower() in ('available', '') and avail:
            # setting available
            out = ('status', str(statuses['available']))
        elif status == 'idle':
            # setting idle
            self._status_message = message
            out = ('status', str(statuses['idle']),
                   'custom_message', message.encode('utf-8'))
        elif not message:
            # away with no message
            if status in nice_statuses:
                out = ('status', str(nice_statuses[status]))
            else:
                out = ('status', str(statuses['steppedout']) )
        else:
            # custom message
            self._status_message = message
            out = ( 'status',         str( statuses['custom'] ),
                    'away',           '0' if avail else '1',
                    'custom_message', message.encode('utf-8'))

        self.send('yahoo6_status_update', 'available', out)

    #
    # sms
    #

    @callsback
    def send_sms(self, sms_number, message, callback=None):
        'Sends an outgoing SMS message.'

        yahoohttp.send_sms(self, sms_number, message, callback=callback)

    def sms_message_brb(self, buddy, message, sms_carrier = 'unknown carrier'):
        'An incoming SMS message.'

        buddy   = self.buddies[buddy]

        self.convo_for(buddy).received_message(buddy, message, sms = True)

    #
    # Buddy list management
    #

    def addbuddy_brb(self, contact, group, error='0', buddy_service=None, pending_auth=None):
        "Server ack for adding buddies."
        name = contact
        group = getattr(group, 'name', group)

        if error == '2':
            log.info('ignoring "%s" in group "%s" error 2 (already in group?).', name, group)
        elif error != '0':
            self.hub.on_error(YahooError("There was an error in adding "
                                    "buddy %s." % name))
        else:
            # create the group if it doesn't exist
            if group in self.groups:
                group = self.groups[group]
            else:
                log.info('group %s did not exist, creating', group)
                grp = Group(group, self, None)
                grp.id = grp
                self.groups[group] = grp
                group = grp

            buddy = self.buddies[name]
            buddy._service = PROTOCOL_CODES.get(buddy_service, 'yahoo') #is it msn/LCS/sametime?
            log.info('adding "%s" to "%s"', name, group)
            group.append( YahooContact(buddy, group) )
            if buddy.status == 'unknown':
                buddy.setnotify('status', 'offline')
            # Mark this buddy as "pending subscription"
            #TODO: across app runs, this won't stay.
            buddy.setnotifyif('pending_auth', True)
            self.root_group.notify()

    @callsback
    def remove_buddy(self, contact_id, callback = None):
        "Removes a buddy from the indicated group."

        if isinstance(contact_id, basestring):
            contact = self.get_contact(contact_id)
            if not contact:
                callback.error()
                return log.warning('cannot find contact %s', contact_id)
            contact_id = contact

        group     = contact_id.group
        buddyname = _buddy_name(contact_id)
        buddy     = contact_id

        self.callbacks['removebuddy.%s' % buddyname] = callback
        d = dict(frombuddy = self.self_buddy.name,
             contact=   buddyname,
             group=     group.name)

        protocode = PROTOCOL_CODES.get(buddy._service, None)
        if protocode is not None: #is it msn/LCS/sametime?
            d.update(buddy_service=protocode)

        self.send('rembuddy','available', **d)

    def contact_for_name(self, name, root = None):
        if root is None:
            root = self.root_group

        for c in root:
            if isinstance(c, Group):
                contact, group = self.contact_for_name(name, c)
                if contact:
                    return contact, group
            elif isinstance(c, YahooContact) and c.name == name:
                return c, root

        return None, None

    def get_contact(self, buddyname):
        'Returns a contact object for a buddy name.'

        contact, group = self.contact_for_name(buddyname)
        return contact

    def rembuddy_brb(self, contact, group, error='0'):
        'Server ack for buddy removal.'

        name = contact
        contact, g_ = self.contact_for_name(contact, self.groups[group])

        cb = self.callbacks.pop('removebuddy.%s' % contact.name)
        log.info('removing "%s" from "%s"', name, group)
        if error == '0':
            if contact is None:
                return log.warning('server sent rembuddy_brb but there is no '
                                   'contact %s', name)
            self.groups[group].remove( contact )
            self.root_group.notify()
            cb.success()
        else:
            cb.error()
            self.hub.on_error(YahooError("Could not remove buddy " + name))

    def send_buddylist(self, buddy, buddygroup = None):
        buddies = [buddy for group in buddygroup or self.groups.itervalues()
                         for buddy in group]

        #TODO: finish send_buddylist

        self.send('send_buddylist', 'available', [
          'frombuddy', self.self_buddy.name,
          'flag',      '0',
        ])

    def handle_blocklists(self, ignore_list, appear_offline_list):
        '''
        ignore_list - a list of buddies you are permanently blocking

        appear_offline_list - buddies for whom stealth_perm is True, i.e., they
                              are on your buddylist but they can't see you
        '''
        buds = self.buddies

        if ignore_list:
            for buddy in ignore_list.split(','):
                buds[buddy].setnotifyif('blocked', True)

        if appear_offline_list:
            for buddy in appear_offline_list.split(','):
                buds[buddy].setnotifyif('stealth_perm', True)

    def list_notinoffice(self, buddy_list = None, ignore_list = None, appear_offline_list = None):
        self.handle_blocklists(ignore_list, appear_offline_list)

        if not buddy_list:
            return

        self.incoming_list(buddy_list)

    def list_available(self,
                       buddy_list  = None,
                       ignore_list = None,
                       appear_offline_list = None,
                       identity_list = '',
                       login_cookie = None, **kw):
        '''The final packet in receiving a buddy list.

        List comes in as Group:Buddy1,Buddy2\nGroup2:Buddy3'''

        if self.state != self.Statuses.LOADING_CONTACT_LIST:
            self.change_state(self.Statuses.LOADING_CONTACT_LIST)

        self.handle_blocklists(ignore_list, appear_offline_list)

        self.identities = [i.lower() for i in identity_list.split(',')]

        if login_cookie:
            # server sends logon cookies we use later for file transfers
            k = login_cookie[0]

            # For Y, T, grab after the letter/tab, and until the first semicolon
            if k in ('Y', 'T'):
                add_cookie(self.cookies, login_cookie)

                if len(self.cookies) >= 2:
                    self.sync_addressbook()
                    self.root_group.notify()

        if buddy_list:
            self.incoming_list(buddy_list)

    def init_buddylist(self):
        #Buddylist PDA (push down automata)
        self.grp  = None
        self.ct   = None
        self.modes = []
        self.entries = []
        self.group_dict = {}
        self.contact_dict = {}

    def list15_available_raw(self, buddy_list, is_available=True):
        '''YMSG15 incomming buddy list'''
        root = self.root_group
        for k,v in ((ykeys.get(k, k), v) for k, v in buddy_list):
#            if k in LIST_COMMANDS:
#                v = BLIST_ENTRIES[v]
            log.debug((k, v))
            if k == BEGIN_MODE:
                self.modes.insert(0, v)
            elif k == END_MODE:
                m = self.modes.pop(0)
                assert m == v
            elif k == BEGIN_ENTRY:
                self.entries.insert(0, v)
                if v == GROUP:
                    assert self.modes[0] == GROUP
                    self.group_dict = {}
                elif v == CONTACT:
                    self.contact_dict = {}
                elif v == BLOCK_ENTRY:
                    self.contact_dict = {}
            elif k == END_ENTRY:
                m = self.entries.pop(0)
                assert m == v
                if v == GROUP:
                    pass
                elif v == CONTACT:
                    contact_dict = self.contact_dict
                    if 'buddy_service' in self.contact_dict:
                        service_type = PROTOCOL_CODES.get(self.contact_dict['buddy_service'], 'yahoo')
                        self.ct.buddy._service = service_type
                    else:
                        self.ct.buddy._service = 'yahoo'
                    if 'pending_auth' in self.contact_dict:
                        self.ct.buddy.pending_auth = True
                    if 'stealth' in self.contact_dict:
                        self.ct.buddy.stealth_perm = True
                elif v == BLOCK_ENTRY:
                    pass
            elif k == 'group':
                assert self.modes[0] == GROUP
                assert self.entries[0] == GROUP
                self.grp = Group(v, self, None)
                self.grp.id = self.grp
                self.groups[v] = self.grp
                root.append(self.grp)
            elif k == 'contact':
                if self.modes[0] == BLOCK_ENTRY:
                    assert self.entries[0] == BLOCK_ENTRY
                    self.buddies[v].blocked = True
                else:
                    assert self.modes[0] == CONTACT
                    assert self.entries[0] == CONTACT
                    self.ct = YahooContact(self.buddies[v], self.grp)
#                    print self.ct, self.ct.status
                    self.grp.append(self.ct)
            else:
                if self.modes[0] == GROUP:
                    self.group_dict[k] = v
                elif self.modes[0] == CONTACT:
                    self.contact_dict[k] = v
                elif self.modes[0] == BLOCK_ENTRY:
                    self.contact_dict[k] = v
        if is_available and self.state != self.Statuses.ONLINE:
            log.info('setting online in list15_available_raw')
            self.change_state(self.Statuses.ONLINE)
            root.notify()

    def list15_steppedout_raw(self, buddy_list):
        self.list15_available_raw(buddy_list, False)

    def incoming_list(self, buddy_list):

        log.info('incoming_list')

        root = self.root_group

        groups = buddy_list.split('\n')
        for group_str in groups:
            # grab the group name
            group_split = group_str.split(':')
            group_name = group_split.pop(0)
            if not group_name:
                continue

            # grab names
            if group_split:  names = group_split[0].split(',')
            else:            names = []

            # create the group
            if group_name in self.groups:
                grp = self.groups[group_name]
            else:
                grp = Group(group_name, self, None)
                grp.id = grp
                self.groups[group_name] = grp

            log.info('group "%s": %s', group_name, names)

            # add a Contact with a YahooBuddy for each name
            grp.extend([YahooContact(self.buddies[name], grp)
                        for name in names])
            root.append(grp)
        root.notify()

    def listallow_notathome(self, buddy, to, message="", buddy_service=None):
        '''
        Server is asking if you'd like to allow a buddy to add you to his or
        her list.
        '''
        if to.lower() not in self.identities:
            return log.warning("got an auth request for %r, but that name is not in this account's identities: %r."
                               "  Ignoring.", to, self.identities)
        bud = self.buddies[buddy]
        bud._service = PROTOCOL_CODES.get(buddy_service, 'yahoo')
        self.hub.authorize_buddy(self, bud, message, username_added=to)

    def listallow_brb(self, buddy, flag, message=None):
        'Server ack for buddy authorize.'

        if flag == '1':
            log.info('%s has authorized you to add them to your list', buddy)
            self.buddies[buddy].setnotifyif('pending_auth', False)

        elif flag == '2':
            msg = u'Buddy %s has chosen not to allow you as a friend.' % buddy
            if message:
                msg += '\n\n"%s"' % message

            #TODO: this really isn't an error.
            self.hub.on_error(YahooError(msg))

    @callsback
    def move_buddy(self, buddy, new_group, from_group=None, new_position=0, callback = None):
        '''
        If new_group is none, then you are moving the buddy within the same
        group.
        '''

        info('moving %s from %s to %s', buddy, from_group, new_group)

        # yahoo doesn't support ordering within a group.
        if new_group is None:
            return log.warning('no new_group passed to move_buddy')

        # find the parent
        if isinstance(buddy, basestring):
            contact, parent_group = self.contact_for_name( buddy )
        else:
            # Contact's ID are ( group, buddyname )
            parent_group, buddy = buddy.id


        if not parent_group:
            return log.error("Couldn't find a parent group for %s", buddy)

        new_group = getattr(new_group, 'name', new_group)

        self.callbacks['movebuddy.%s' % buddy] = callback
        pkt = ['frombuddy', self.self_buddy.name,
               BEGIN_MODE,       MOVE,
               BEGIN_ENTRY,      MOVE,
               'contact',   buddy]

        protocode = PROTOCOL_CODES.get(self.buddies[buddy]._service, None)
        if protocode is not None: #is it msn/LCS/sametime?
            pkt.extend(['buddy_service', protocode])
        pkt.extend(['fromgroup', parent_group.name,
                   'togroup',   new_group,
                   END_ENTRY,      MOVE,
                   END_MODE,       MOVE,])
        self.send('movebuddy','available', pkt)

    def movebuddy_brb(self, contact, fromgroup, togroup, error='0'):
        'Server ack for moving a buddy between groups.'
        name, err = contact, lambda s: self.hub.on_error(YahooError(s))

        info('movebuddy ACK')

        found_contact = None               # search for the right Contact object
        for c in self.groups[fromgroup]:
            if name == c.name:
                found_contact = c
                break

        if found_contact is None:
            return err('Could not move buddy.')

        cb = self.callbacks.pop('movebuddy.%s' % found_contact.name)
        if error != '0':
            cb.error()
            err('Server indicated an error in moving buddy: %s' % error)
        if fromgroup not in self.groups:
            cb.error()
            return err('%s is not in the list of groups' % fromgroup)

        # Actually do the moving.
        self.groups[fromgroup].remove(found_contact)

        if not togroup in self.groups:
            log.info('group %s did not exist, creating', togroup)
            grp = Group(togroup, self, None)
            grp.id = grp
            self.groups[togroup] = grp

        self.groups[togroup].append(found_contact)

        # Update the Contact's id
        found_contact.id = (self.groups[togroup], found_contact.name)
        found_contact.group = self.groups[togroup]

        cb.success(found_contact.id)
        self.root_group.notify()

    def remove_group_case_insensitive(self, group_name):
        '''
        Removes any groups that match group_name, case insentive.
        '''

        group_name = group_name.lower()

        for name, group in self.groups.items():
            if name.lower() == group_name:
                self.remove_group(group)

    @callsback
    def remove_group(self, group, callback):
        group_name = group.name if hasattr(group, 'name') else str(group)

        log.info('Removing %r.', group)

        oldsuccess = callback.success
        def on_done():
            log.info('deleting group %r', group_name)
            groupobj = self.groups.pop(group_name, None)
            self.root_group.remove(groupobj)
            oldsuccess()

        callback.success = on_done

        groupobj = self.groups[group_name]
        if len(groupobj) > 0:
            ms = []
            for contact in groupobj:
                @callsback
                def do_remove(contact=contact, callback = None):
                    log.info('Removing %r.', contact)
                    self.remove_buddy(contact, callback = callback)

                ms.append(do_remove)

            from util.callbacks import do_cb_na
            do_cb_na(ms, callback = callback) #I know, there are no callback args, but we don't want them
        else:
            on_done()

    def authorize_buddy(self, buddy, allow, username_added):
        assert username_added
        buddy_name = str(buddy)
        bud = self.buddies[buddy_name]
        #HAX: yahoo should become aware of it's multiple screen names
        l = ['frombuddy', username_added,
               'to',        buddy_name]
        protocode = PROTOCOL_CODES.get(bud._service, None)
        if protocode is not None: #is it msn/LCS/sametime?
            l.extend(['buddy_service',protocode])
        if allow:    l.extend(['flag', '1', 334, '0',])
        else:        l.extend(['flag', '2', 334, '0', 'message', 'decline'])

        self.send('listallow', 'available', l)

    @callsback
    def add_group(self, group_name, callback = None):
        '''Add an empty group. This happens immediately, since there is no
        corresponding server operation--groups seem to only be defined by the
        buddies in them.'''

        grp = self.groups[group_name] = Group(group_name, self, None)
        grp.id = grp

        callback.success(grp)
        self.root_group.append(grp)

    @callsback
    def rename_group(self, group_obj, new_name, callback = None):
        'Renames a group.'

        if   hasattr(group_obj, 'name'): group = group_obj.name
        elif isinstance(group_obj, basestring): group = group_obj
        else: raise TypeError('give a group name or object: %s %r' % (type(group_obj), group_obj))

        self.callbacks['grouprename.%s' % new_name] = callback

        self.send('grouprename','available',
           frombuddy = self.self_buddy.name,
           group =     group,
           new_group = new_name.encode('utf-8'),
        )

    def grouprename_brb(self, new_group, group = None, error = '0'):
        'Server ack for group rename.'
        grps = self.groups

        cb = self.callbacks.pop('grouprename.%s' % group, None)

        if error == '1':
            if cb is not None: cb.error()
        else:
            grps[group] = grps[new_group]
            grps[new_group].name = group
            del grps[new_group]
            if cb is not None: cb.success()
            self.root_group.notify()

    def add_contact(self, buddy_name, group, intro_text = None, service = None):
        assert service is not None
        protocode = PROTOCOL_CODES.get(service, 'yahoo')

        if protocode == 'yahoo' and '@yahoo' in buddy_name:
            buddy_name = buddy_name.split('@', 1)[0]

        if buddy_name in self.buddies:
            buddy = self.buddies[buddy_name]
            if buddy.blocked:
                self.unblock_buddy(buddy,
                                   success = lambda: self.add_contact(buddy_name,
                                   group, intro_text=intro_text, service=service))
                return

        if intro_text is None:
            intro_text = _("May I add you to my contact list?")

        group = getattr(group, 'name', group)
        if not isinstance(group, basestring):
            raise TypeError('group must be a Group or a string group name: %s' % type(group))

        pkt = ['message', intro_text,
               'group',    group,
               'frombuddy',  self.self_buddy.name,
               BEGIN_MODE,  CONTACT,
               BEGIN_ENTRY, CONTACT,
               'contact',  buddy_name,
               ]

        if protocode != 'yahoo': #is it msn/LCS/sametime?
            pkt.extend(['buddy_service', protocode])
        pkt.extend([END_ENTRY, CONTACT,
                    END_MODE,  CONTACT])

        self.send('addbuddy', 'available', pkt)


    add_buddy = add_contact # compatibility

    def set_invisible(self, invisible = True):
        'Become or come back from being invisible.'

        log.info('%r: set_invisible(%s)', self, invisible)

        self.send('invisible', 'available',
                  flag = '2' if invisible else '1')

        if invisible:
            # going invisible clears all stealth sessions
            for buddy in self.buddies.values():
                if not buddy.stealth_session:
                    buddy.setnotifyif('stealth_session', True)

    #
    # IGNORECONTACT (133) - adds a buddy to your "block list"
    #

    @callsback
    def block_buddy(self, buddy, callback = None):
        'Block a buddy. (This adds the buddy to your "ignore" list.)'

        self.set_blocked(buddy, True, callback = callback)

    @callsback
    def unblock_buddy(self, buddy, callback = None):
        'Unblock a buddy. (This removes a buddy from your "ignore" list.)'

        self.set_blocked(buddy, False, callback = callback)

    @callsback
    def set_blocked(self, buddy, blocked = True, callback = None):
        'Adds or removes a buddy from the blocklist.'

        buddy = _buddy_name(buddy)
        self.callbacks['ignorecontact.%s' % buddy] = callback

        def send_block(buddy = buddy, blocked = blocked):
            self.send('ignorecontact', 'available',
                      frombuddy = self.self_buddy.name,
                      contact = buddy,
                      flag = '1' if blocked else '2')

        for group in self.groups.values():
            for gbud in group:
                if gbud.name == buddy:
                    log.info('removing buddy %s', buddy)
                    return self.remove_buddy(buddy, success = send_block)

        send_block()

    def ignorecontact_brb(self, away_buddy, flag, error):
        'Server is responding to a block buddy.'

        cb = self.callbacks.pop('ignorecontact.%s' % away_buddy, None)

        if error == '0':
            self.buddies[away_buddy].setnotifyif('blocked', flag == '1')
            if cb: cb.success()
        else:
            log.warning('error blocking buddy %s (err code %s)', away_buddy, error)
            if cb: cb.error()


    #
    # STEALTH_PERM (185) - appearing permanantly invisible to buddies while they
    #                      are still on your buddy list
    #

    @callsback
    def set_stealth_perm(self, buddy, set_blocked = True, callback = None):
        'Set permanent stealth settings for the indicated buddy.'

        log.info('set_stealth_perm %s set_blocked = %s', buddy, set_blocked)

        buddy = _buddy_name(buddy)
        self.callbacks['block_buddy.%s' % buddy] = callback

        self.send('stealth_perm', 'available', [
            'frombuddy',  self.self_buddy.name,
            'block'    , '1' if set_blocked else '2',
            'flag'     , '2',
            BEGIN_MODE , CONTACT,
            BEGIN_ENTRY, CONTACT,
            'contact'  , buddy,
            END_ENTRY  , CONTACT,
            END_MODE   , CONTACT])

    def stealth_perm_brb(self, contact, block, flag, error='0'):
        'Server ack for blocking/unblocking a buddy.'

        cb = self.callbacks.pop('block_buddy.%s' % contact, None)

        if error != '0':
            if cb is not None: cb.error()
            return self.hub.on_error(YahooError('There was an error blocking ' + contact))

        if   block == '1': blocked = True
        elif block == '2': blocked = False
        else:
            if cb is not None: cb.error()
            return log.warning('unknown block flag in stealth_perm_brb packet: %r', block)

        self.buddies[contact].setnotifyif('stealth_perm', blocked)
        if cb is not None: cb.success()

    #
    # STEALTH_SESSION (186) - appearing online to specific buddies while invisible
    #

    @callsback
    def set_stealth_session(self, buddy, appear_online = True, callback = None):
        '''
        Modifies buddy specific visibilty setting. Use to appear online to someone
        while invisible.
        '''
        buddy = _buddy_name(buddy)
        self.callbacks['appear_online.%s' % buddy] = callback

        self.send('stealth_session', 'available', [
                  'frombuddy',  self.self_buddy.name,
                  'block'    , '2' if appear_online else '1',
                  'flag'     , '1',
                  BEGIN_MODE , CONTACT,
                  BEGIN_ENTRY, CONTACT,
                  'contact', buddy,
                  END_ENTRY  , CONTACT,
                  END_MODE   , CONTACT])

    def stealth_session_brb(self, contact, block, flag, error = '0'):
        'Server ack for appearing online to a specific buddy while invisible.'

        cb = self.callbacks.pop('appear_online.%s' % contact, None)

        if error != '0':
            if cb is not None: cb.error()
            return self.hub.on_error(YahooError(_('There was an error modifying stealth settings for {name}.').format(name=contact)))

        if   block == '2': seesme = True
        elif block == '1': seesme = False
        else:
            if cb is not None: cb.error()
            return log.warning('unknown block flag in stealth_session_brb: %r', block)

        log.info('stealth_session_brb for %s: %s (%s)', contact, block, seesme)

        self.buddies[contact].setnotifyif('stealth_session', seesme)
        if cb is not None: cb.success()

    def set_remote_alias(self, buddy, alias):
        buddy = get_bname(buddy)

        if not buddy in self.buddies:
            return self.hub.on_error(YahooError(buddy + ' is not on your '
                                                'contact list'))

        url = UrlQuery('http://address.yahoo.com/us/?', d={'.intl':'us'},
                 v='XM', prog='ymsgr', sync='1', tags='long',
                 noclear='1')

        # Assemble XML necessary to change the address book entry
        data = tag('ab', cc=1, k=self.self_buddy.name)(
            tag('ct', pr=0, yi=buddy, c=1, id=11, nn=alias)
        )

        info('sending:')
        info(data._to_xml())

        def set_remote_done(res):
            if res:
                self.buddies[buddy].update_cinfo(res)
            else:
                self.hub.on_error(YahooError("There was an error in editing "
                                             "contact details."))
        # POST to the address.yahoo.com address
        post_xml(url, data, **{
                 'Cookie' : self.cookie_str,
                 'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 5.5)', 'success' :set_remote_done})

    def get_remotes(self):
        url = UrlQuery('http://address.yahoo.com/', d={'.intl':'us'},
                 v='XM', prog='ymsgr', tags='short')
        post_xml(url, data=tag(''), **{
                 'Cookie' : self.cookie_str,
                 'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 5.5)', 'success':self.finish_get_remotes})

    def finish_get_remotes(self, res):
        cts = res.ct
#        print repr(res._to_xml())
        for ct in cts:
            if 'yi' in ct._attrs:
                self.buddies[str(ct['yi'])].update_cinfo_raw(ct)

    #
    # File Transfer
    #

    def send_file(self, buddy, fileinfo):
        # Since pure p2p is not implemented:

        from .peerfiletransfer import YahooOutgoingPeerFileXfer
        xfer = YahooOutgoingPeerFileXfer(self, buddy, fileinfo)
        xfer.send_offer()
        return xfer

    def filetransfer_brb(self, to, url):
        'A buddy is trying to send you a file.'

        # ask the hub if it's okay to download this file.
        # hub will call accept_file with the URL if okay.
        transfer = YahooHTTPIncoming(self, self.buddies[to], url)
        self.hub.on_file_request( self, transfer )

    def filetransfer_available(self, **opts):
        print opts

    def accept_file(self, filexfer, fileobj):
        'Accept a file transfer.'

        if isinstance(filexfer, basestring):
            # Receive a file from the Yahoo! file transfer server
            url = filexfer
            info('Accepting a file from the Yahoo file xfer server via a HTTP GET')
            result = urlopen(url)

            # Write the HTTP result out to the open file, and close it.
            fileobj.write( result.read() )
            fileobj.close()
        else:
            # Must be a peer to peer file transfer.
            if not isinstance(filexfer, YahooPeerFileTransfer):
                raise TypeError('filexfer must be a YahooPeerFileTransfer object')
            info('Accepting a p2p file transfer')
            filexfer.accept()

    def decline_file(self, filexfer):
        'Decline a file transfer.'
        filexfer.decline()

    def filetransfer_notatdesk(self):
        'Server ack for a file upload.'

        print 'Got ack for file upload!'

    def peertopeer_brb(self, base64ip, buddy, typing_status, **k):
        from struct import pack, unpack
        ip = tuple(reversed(unpack("B"*4, pack('!I', int(base64ip.decode('base64'))))))
        print "ip:", ip
        print "buddy", buddy
        print "status", typing_status
        from pprint import pprint
        pprint(k)
        ip = '.'.join(str(x) for x in ip)
        port = 5101
        if buddy in self.peertopeers:
            return
        self.peertopeers[buddy] = YahooP2P(self, buddy, k['to'], (ip, port), self.socket.session_id)

    def peerrequest_brb(self, buddy, p2pcookie, filename = None, longcookie=None, **k):
        '220: P2P file transfer request. Asks the hub whether or not to accept.'
        mode = k.get('acceptxfer', sentinel)
        if mode == '1':
    #        k.pop('to')
            if filename is None: # Is this a filetransfer cancel? yes.
                try:
                    self.file_transfers.pop((buddy, p2pcookie)).cancel(me=False)
                except AttributeError:
                    info("could not cancel file transfer with %r", buddy)
                return info('%r cancelled a file transfer', buddy)

            filexfer = YahooPeerFileTransfer(self, self.buddies[buddy],
                                    filename = filename,
                                    p2pcookie = p2pcookie,
                                    longcookie = longcookie,
    #                                to = buddy,
    #                                frombuddy = self.self_buddy.name,
                                    buddyname=buddy, **k)
            self.file_transfers[(buddy, p2pcookie)] = filexfer
            self.hub.on_file_request(self, filexfer)
        elif mode == '3':
            #someone accepted our request
            if (buddy, p2pcookie) in self.file_transfers:
                self.file_transfers[(buddy, p2pcookie)].do_setup(buddy, p2pcookie, filename, longcookie, **k)
        elif mode == '4':
            #decline
            try:
                self.file_transfers.pop((buddy, p2pcookie)).cancel(me=False)
            except AttributeError:
                info("could not cancel file transfer with %r", buddy)

    def peersetup_brb(self, buddy, filename, peer_path, p2pcookie, peerip=None, transfertype=None):
        try:
            ft = self.file_transfers[(buddy, p2pcookie)]
            ft.connect(buddy, filename, peer_path, p2pcookie, peerip, transfertype)
        except KeyError:
            pass

    def peersetup_cancel(self, buddy, p2pcookie, **kws):
        ft = self.file_transfers.pop((buddy, p2pcookie), None)
        if ft is not None:
            ft.cancel(me=False)

    def peerinit_brb(self, buddy, p2pcookie, filename, transfertype, peer_path, **k):
        try:
            ft = self.file_transfers[(buddy, p2pcookie)]
            ft.go(buddy, p2pcookie, filename, transfertype, peer_path, **k)
        except KeyError:
            pass

    def peerinit_cancel(self, buddy, p2pcookie, **k):
        ft = self.file_transfers.pop((buddy, p2pcookie), None)
        if ft is not None:
            ft.cancel(me=False)

    #VIDEO chat?

    def skinname_available_raw(self, ydict_iter):
        pass
        #print list(ydict_iter)

    #
    # IM
    #

    def chat_with(self, buddy):
        'Ask to chat with a buddy.'
        self.hub.on_conversation(self.convo_for(buddy))

    def _parse_incoming_message(self, ydict_iter):
        all_messages = []
        ydict_iter = list(ydict_iter)
        print 'i', ydict_iter
        messages = groupify(ydict_iter)
        for d in messages:
            keep = True
            d = yiter_to_dict(d.iteritems())
            if 'message' not in d:
                continue
            if 'buddy' not in d:
                if 'frombuddy' in d:
                    d['buddy'] = d['frombuddy']
                else:
                    continue

            buddy = self.buddies[d['buddy']]

            timestamp = None
            unix_time = d.get('unix_time')
            if unix_time is not None:
                with traceguard:
                    timestamp = datetime.utcfromtimestamp(int(unix_time))
            if 'msgid' in d:
                keep = ack_message(self, d, 'buddy')
            if keep:
                all_messages.append((buddy, d['message'], timestamp))
        return all_messages

    def incoming_message_raw(self, ydict_iter):

        message_info = self._parse_incoming_message(ydict_iter)
        for (buddy, message, timestamp) in message_info:
            self.convo_for(buddy).incoming_message(buddy, message, timestamp = timestamp, content_type = 'text/html')

    message_brb_raw = message_notinoffice_raw = message_offline_raw = incoming_message_raw

#    def message_brb_raw(self, ydict_iter):
#        message_info = self._parse_incoming_message(ydict_iter)
#        for (buddy, message, timestamp) in message_info:
#            self.convo_for(buddy).incoming_message(buddy, message, timestamp = timestamp)

    def audible_brb(self, buddy, audible_message):
        '''
        A buddy has sent you an audible, a small flash animation with a
        message from a character.
        '''

        # Just display the text message:
        buddy = self.buddies[buddy]
        self.convo_for(buddy).incoming_message(buddy, audible_message)

    def notify_brb(self, buddy, typing_status, flag):
        'Typing notifications.'
        from common import pref

        if typing_status == 'TYPING':
            # buddy's typing status has changed
            if flag == '1': state = 'typing'
            else:           state = None

            buddy = self.buddies[buddy]

            # For some reason, the server still sends you typing
            # notifications for buddies on your ignore list.
            if not buddy.blocked:
                if buddy in self.conversations:
                    self.conversations[buddy].typing_status[buddy] = state
                elif pref('messaging.psychic', False):
                    c = self.convo_for(buddy)
                    self.hub.on_conversation(c)
                    c.tingle()

    @threaded
    def sync_addressbook(self):
        times = Storage(f=0, i=0, sy=0, sm=0, c=0, a=0)

        log.info('syncing yahoo! addressbook')
        ab_url = ('http://insider.msg.yahoo.com/ycontent/?'
                  #'filter=%(f)s&'
                  #'imv=%(i)s&'
                  #'system=%(sy)s&'
                  #'sms=%(sm)s&'
                  #'chatcat=%(c)s&'
                  'ab2=%(a)s&'
                  'intl=us&os=win') % times

        req = Request(ab_url, headers = {'Cookie': self.cookie_str})

        try:
            response = urlopen(req)
        except Exception:
            traceback.print_exc()
            return

        xml = response.read()
        log.debug(xml)
        content = tag(xml)

        for record in content.addressbook.record:
            name = record['userid']
            log.debug('updating address book info for %s', name)
            buddy = self.buddies[name]
            buddy.update_cinfo_raw(record)

    #
    # conferences (multi user private chats)
    #

    def _create_conference(self, name):
        if name not in self.conferences:
            info('creating YahooConf %r', name)
            self.conferences[name] = conf = YahooConf(self, name = name)
        else:
            conf = self.conferences[name]

        return conf

    def confaddinvite_brb_raw(self, ydict_iter):
        'You are invited to a conference.'

        log.info('confaddinvite_brb_raw')

        conf, confbuddy, confname = None, None, None
        conf_entering = None
        invite_msg = ''
        tobuddies = []

        from functools import partial

        conf_entering_buddies = []
        for k, v in ydict_iter:
            if k == ykeys['conf_name']:
                conf = self._create_conference(v)
                confname = v
            elif k == ykeys['conf_entering']:
                conf_entering_buddies.append(v)
            elif k == ykeys['conf_buddy']:
                confbuddy = v
            elif k == ykeys['conf_invite_message']:
                invite_msg = v
            elif k == ykeys['conf_tobuddy']:
                tobuddies.append(v)

        for b in conf_entering_buddies:
            conf.buddy_join(self.buddies[b])

        self.callbacks['confinvite.' + confname].success(conf)
        conf.buddy_join(self.buddies[confbuddy])

        from common import profile
        if confbuddy.lower() == self.self_buddy.name.lower():
            return profile.on_entered_chat(conf)

        def invite_answer(accept, confname=confname, confbuddy=confbuddy):
            other_buddies = []
            if confbuddy not in other_buddies:
                tobuddies.insert(0, confbuddy)

            for b in conf_entering_buddies:
                #other_buddies.extend(['conf_entering', b])
                other_buddies.extend(['conf_from', b])

            for bud in tobuddies:
                other_buddies.extend(['conf_from', bud])

            self.send('conflogon' if accept else 'confdecline', 'available',
                    ['frombuddy', self.self_buddy.name,
                     'conf_name', confname] +
                    other_buddies)

            if accept:
                self.conflogon_brb(confname, confbuddy)
                self.conflogon_brb(confname, self.self_buddy.name)

                profile.on_entered_chat(conf)
            else:
                self.conferences.pop(confname, None)

        self.hub.on_invite(self, confbuddy, confname,
                           message = invite_msg,
                           on_yes = partial(invite_answer, accept = True),
                           on_no  = partial(invite_answer, accept = False))

    confinvite_brb_raw = confaddinvite_brb_raw
    confaddinvite_11_raw = confaddinvite_brb_raw

    def confmsg_brb(self, conf_name, conf_from, message):
        'Incoming conference message.'

        buddy = self.buddies[conf_from]
        if conf_name in self.conferences:
            self.conferences[conf_name].incoming_message(buddy, message)
        else:
            log.info_s('conference(%s) - %s: %s', conf_name, conf_from, message)

    def confmsg_cancel(self, error_message):
        msg = 'There was an error in sending a conference message:\n\n%s' \
                % error_message
        self.hub.on_error(YahooError(msg))

    def conflogon_brb(self, conf_name, conf_entering):
        'Incoming conference logon.'

        info('%s entering %s' % (conf_entering, conf_name))
        conf = self._create_conference(conf_name)
        conf.buddy_join(self.buddies[conf_entering])
        if self.self_buddy not in conf:
            conf.buddy_join(self.self_buddy)


    def conflogoff_brb(self, conf_name, conf_leaving):
        'Buddy has left conversation.'

        if conf_name in self.conferences:
            self.conferences[conf_name].buddy_leave(self.buddies[conf_leaving])

            if conf_leaving == self.self_buddy.name:
                del self.conferences[conf_name]
        else:
            log.warning('got conf logoff for %s from room %s, but rooms are %r',
                 conf_leaving, conf_name, self.conferences.keys())

    @callsback
    def make_chat_and_invite(self, buddies_to_invite, convo=None, room_name=None, server=None, notify=False, callback=None):
        if not buddies_to_invite:
            return common.protocol.make_chat_and_invite(self, buddies_to_invite, convo=convo,
                    room_name=room_name, server=server, notify=notify, callback=callback)

        buddynames = [b.name for b in buddies_to_invite]
        self.invite_to_conference(self._gen_room_name(), buddynames, callback=callback)

    @callsback
    def invite_to_conference(self, roomname, buddyname, message=None, callback=None):
        'Invite performed after a "conference logon"'

        myname = self.self_buddy.name

        log.info('inviting %r to %r', buddyname, roomname)

        buddies = [buddyname] if isinstance(buddyname, basestring) else buddyname
        buddies_args = []
        for bud in buddies:
            buddies_args.extend(['conf_tobuddy', bud])

        self.callbacks['confinvite.' + roomname] = callback
        self.send('confinvite', 'available', [
                  'frombuddy', myname,
                  'conf_buddy', myname,
                  'conf_name', roomname,
                  'conf_invite_message', unicode(message or 'Join my conference...').encode('utf8'),
                  'msg_encoding', '1'] +
                  buddies_args +
                 ['flag', '256'])

    def _gen_room_name(self):
        return '%s-%d' % (self.self_buddy.name, random.randint(1, sys.maxint))

    @callsback
    def join_chat(self, room_name = None, convo = None, server = None, notify_profile=True, callback = None):
        '''
        Starts a conference.
        '''

        def success(conf):
            callback.success(conf)
            if notify_profile:
                from common import profile
                profile.on_entered_chat(conf)

        self.socket.conflogon(room_name or self._gen_room_name(), success)

    #
    # Yahoo! 360
    #

    def yahoo360_available(self, to, yahoo360xml):
        yahoo360.handle(self, yahoo360xml)

    def yahoo360update_available(self, to, mingle_xml):
        yahoo360.handle(self, mingle_xml)

    def yahoo360update_brb(self, mingle_xml, unix_time = None, ):
        yahoo360.handle(self, mingle_xml)

    #
    # Status Updates
    #

    def logoff_brb(self, contact):
        "A buddy has logged off."
        self.buddies[contact].signoff()

    def ping_brb(self, **response):
        info("PING: %r", response)

    def lastlogin_brb(self, unix_time):
        'Received at the end of the login process.'

        info('lastlogin: %r', unix_time)

    def newcontact_brb(self, **response):
        print response

    def newmail_brb(self, count):
        self.hub.on_mail(self, count)


    def logoff_cancel(self):
        'Server is informing you that this username is logged on in another location.'

        self.set_disconnected(self.Reasons.OTHER_USER)

    def set_profile(self, msg, profile=None):
        log.warning('TODO: set yahoo profile to %r', msg)

    def update_buddy(self, contact, status = None, custom_message = '', away = '0',
                     idle_seconds = None,
                     idle_duration_privacy = None, login = False,
                     **k):

        buddy     = self.buddies[contact]

        set    = lambda k, v: setattr(buddy, k, v)
        status = int(status) if status is not None else status
        idle   = None

        checksum = k.get('checksum', None)
        if checksum is not None:
            log.warning('login checksum for %r: %r', contact, checksum)
            set('_login_icon_hash', checksum)
            set('icon_hash', checksum)

        # available
        if status == 0:
            set('status', 'available')
            set('status_message', u'')

        # custom message
        elif status == 99 or custom_message:
            set('status', 'away' if away != '0' else 'available')
            set('status_message', custom_message)

        # "normal" busy states like out to lunch
        elif status in nice_statuses:
            nice_status = nice_statuses[status]
            set('status', 'away')
            set('status_message', nice_status)

        # idle
        elif status == 999:
            if not idle_seconds:
                idle_seconds = 0

            if login:
                idle = int(time() - int(idle_seconds))
            else:
                idle = int(time())

            set('status', 'idle')

        elif status == -1:
            set('status', 'offline')

        else:
            log.warning('unknown status %s', status)

        set('idle', idle)
        buddy.notify()

    awaylogin_brb = \
    yahoo6_status_update_brb = \
    update_buddy


    def logon_available_raw(self, ydict_iter):
        y = list(ydict_iter)

        idxs = [i for i, (k, v) in enumerate(y) if k == ykeys['contact']]

        for x in xrange(len(idxs)):
            # split up the packet by contact
            i = idxs[x]
            try: j = idxs[x+1]
            except IndexError: j = len(y)

            opts = yiter_to_dict(y[i:j])
            opts['login'] = True
            self.update_buddy(**opts)

        if self.state != self.Statuses.ONLINE:
            log.info('setting online in logon_available_raw')
            self.change_state(self.Statuses.ONLINE)
        self.get_remotes()

    awaylogin_steppedout_raw = \
    logon_brb_raw = \
    logon_available_raw

    def awaylogin_available_raw(self, ydict_iter):
        self.logon_available_raw(ydict_iter)
        self.fix_unknown_statuses()

    def authresp_cancel(self, **k):
        if self.state == self.Statuses.ONLINE:
            self.set_disconnected(self.Reasons.CONN_FAIL)
        else:
            error = k.get('error', None)
            if error == '1011':
                self.set_disconnected(self.Reasons.CONN_FAIL)
            else:
                self.set_disconnected(self.Reasons.BAD_PASSWORD)

    def send(self, command, status, ydict = None, **kw):
        'Sends a Yahoo dictionary over the network.'

        # to_ydict can either take a mapping or a FLAT list of pairs

        if ydict is None:
            packet = kw
        elif not hasattr(ydict, 'items'):
            # maintain order
            packet = ydict
            for k, v in kw.iteritems():
                packet.extend([k, v])
        else:
            packet = ydict
            packet.update(kw)

        self.socket.ysend(commands[command], statuses[status], data = packet)

    def yahoo_packet(self, command, status, *a, **kw):
        if a:
            assert not kw
            ydict = a
        else: ydict = kw

        return self.socket.make_ypacket(commands[command], statuses[status], data=ydict)

    def yahoo_packet_v(self, version, command, status, *a, **kw):
        assert isinstance(version, int)

        if a:
            assert not kw
            ydict = a
        else: ydict = kw

        return self.socket.make_ypacket(commands[command], statuses[status], version,
                                 data=ydict)

    def yahoo_packet_v_bin(self, version, command, status, *a, **kw):
        assert isinstance(version, int)

        if a:
            assert not kw
            ydict = a
        else: ydict = kw
        ys = YahooSocketBase(self)
        ys.session_id = self.socket.session_id
        return ys.make_ypacket(commands[command], statuses[status], version,
                                 data=ydict)

    def convo_for(self, buddy):
        print self.conversations.keys()

        service = None
        if not isinstance(buddy, basestring):
            service = buddy.service
            buddy = buddy.name

        if not isinstance(buddy, YahooBuddy):
            assert isinstance(buddy, basestring)
            buddy = self.buddies[buddy]

        # This is a hack to change a buddy's service to the one that was asked for via the
        # buddy argument. We have a problem in that self.buddies keys by name, but really
        # you could have an MSN buddy and a Yahoo buddy with the same name.
        if service is not None:
            buddy._service = service

        if buddy in self.conversations:
            convo = self.conversations[buddy]
        else:
            convo = YahooConvo(self, buddy)
            self.conversations[buddy] = convo
        return convo

    def exit_conversation(self, convo):
        '''Conversations call this with themselves as the only argument when
        they are exiting.'''

        for k, v in self.conversations.iteritems():
            if v is convo:
                return self.conversations.pop(k)

    def __repr__(self):
        return '<YahooProtocol (%s)>' % self.username

    @property
    def cookie_str(self):
        ck = 'T=%s; path=/; domain=.yahoo.com; Y=%s; path=/; domain=.yahoo.com' % (self.cookies['T'], self.cookies['Y'])
        return ck


    def set_idle(self, since=0):
        if since:
            self._old_status = self.status
            self.set_message(self._status_message, 'idle')
        else:
            self.set_message(self._status_message, self._old_status)
            self._old_status = 'idle'

    @action()
    def go_mobile(self):
        pass

    @action()
    def send_contact_details(self):
        pass

    @action()
    def send_messenger_list(self):
        pass

    @action()
    def my_account_info(self):
        import wx
        wx.LaunchDefaultBrowser('http://msg.edit.yahoo.com/config/eval_profile')
        # needs token for autologin
        # self.hub.launch_url('...')

    @action()
    def my_web_profile(self):
        import wx
        wx.LaunchDefaultBrowser('http://msg.edit.yahoo.com/config/edit_identity')
        pass # needs token
        # self.hub.launch_url('...')

    def allow_message(self, buddy, mobj):
        '''
        Returns True if messages from this buddy are allowed, False otherwise.
        '''
        super = common.protocol.allow_message(self, buddy, mobj)
        if super in (True, False):
            return super

        if buddy.blocked:
            return False
        elif self.block_unknowns:
            for gname in self.groups:
                if buddy.name.lower() in (b.name.lower() for b in self.groups[gname]):
                    return True
            else:
                return False
        else:
            return True

