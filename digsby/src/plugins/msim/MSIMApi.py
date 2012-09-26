'''
Handles sending and receiving of protocol messages. Emits events when known message types are received. Generally
speaking, operates on primitives - no buddy objects, etc.
'''
import base64
import logging

import util.net as net
import util.callbacks as callbacks
import util.Events as Events

import MSIMUtil as msim_util
from MSIMUtil import msmsg
from MSIMSocket import myspace_socket

log = logging.getLogger('msim.api')


class MyspaceError(Exception):
    pass


class MyspaceFatalError(MyspaceError):
    pass


def count(i=0, max=0xFFFFFFFF):
    while True:
        i += 1
        i %= max
        yield i


def myspace_auth_challenge_response(username, password, nonce):
    ips = net.myips('')

    numips = len(ips)
    ips = [ord(c) for c in ''.join(ips)]

    import struct
    extra = struct.pack('!I', numips)
    extra += ''.join(chr(x) for x in ips)

    return msim_util.crypt(nonce, password, username + '\0' + extra)


class MSIM_Api(Events.EventMixin):
    PASSWORD_MAX_LENGTH = 10
    LOGINID = 0x30002
    CLIENTVER = 823

    CONNECT_ADDRS = (
        ('im.myspace.akadns.net',  443),
        ('im.myspace.akadns.net', 1863),
        ('im.myspace.akadns.net',   80),
        ('im.myspace.akadns.net', 6660),
        ('im.myspace.akadns.net', 6661),
        ('im.myspace.akadns.net', 6662),
        ('im.myspace.akadns.net', 6665),
        ('im.myspace.akadns.net', 6668),
        ('im.myspace.akadns.net', 6669),
    )

    error_max = 3

    events = Events.EventMixin.events | set((
        'connect_failed',
        'connection_closed',
        'login_success',
        'login_challenge',

        'on_error',

        'got_buddy',
        'got_buddies',
        'got_group',
        'got_groups',

        'got_buddy_presence',
        'got_contact_info',
        'got_group_info',

        'got_webchallenge_info',
        'got_social_alerts',
        'got_server_settings',

        'got_im',
        'got_zap',
        'got_typing',
        'got_groupmsg',

    ))

    def __init__(self):
        Events.EventMixin.__init__(self)

        self.rid = count()
        self.error_count = 0

        self.sesskey = None
        self.proof = None
        self.userid = None
        self.profileid = None
        self.uniquenick = None

        self._callbacks = {}
        self.sock = None

        self.message_handlers = {
                                 'lc': LcMessage,
                                 'error': ErrorMessage,
                                 'bm': BmMessage,
                                 'persistr': PersistrMessage,
                                 }

    ###################################
    #  Socket stuff
    ###################################

    def connect(self, start_server=None):
        self._partial_msgs = {}
        if start_server is None or start_server in self.CONNECT_ADDRS:
            srv = []
        else:
            srv = [start_server]

        self.connect_addrs = iter(srv + list(self.CONNECT_ADDRS))
        self.try_connect()

    def disconnect(self):
        sock, self.sock = self.sock, None
        self._unbind_events(sock)
        if sock is not None:
            sock.close()

        self.connection_closed()

    def try_connect(self):
        if getattr(self, 'sock', None) is not None:
            # If we have a socket, make sure to close it so things get cleaned up
            self.sock.close()
            self.sock = None

        if self.connect_addrs is None:
            return self.connect_failed()

        try:
            addr = self.connect_addrs.next()
        except StopIteration:
            self.connect_addrs = None
            return self.connect_failed()

        # Create a socket, tell it to connect, and to loop back to this function on a failure.
        self.sock = myspace_socket()
        self._bind_events(self.sock)
        self.sock.connect(addr, error=lambda *a: self.try_connect())

    def _bind_events(self, sock=None):
        if sock is None:
            sock = getattr(self, 'sock', None)

        if sock is None:
            return

        sock.bind_event('on_message', self.incoming_command)
        sock.bind_event('on_close', self.connection_closed)

    def _unbind_events(self, sock=None):
        if sock is None:
            sock = getattr(self, 'sock', None)

        if sock is None:
            return

        sock.unbind('on_message', self.incoming_command)
        sock.unbind('on_close', self.connection_closed)

    def _on_closed_socket(self, sock):
        if sock is None:
            sock = self.sock

        if sock is self.sock:
            self.sock = None

        if sock is None:
            return

        self._unbind_events(sock)

        sock.close()
        if self.connect_addrs is not None:
            self.try_connect()
            return Events.Veto

        return ()  # Don't pass socket up to event handlers

    ###################################
    #  Events
    ###################################

    @Events.event
    def login_success(self):
        self.connect_addrs = None

    @Events.event
    def connection_closed(self, sock=None):
        return self._on_closed_socket(sock)

    @Events.event
    def connect_failed(self, sock=None):
        return self._on_closed_socket(sock)

    ###################################
    #  Message Processing
    ###################################

    def finalize_split_msg(self, msg):
        body = self._partial_msgs.pop(msg.get('rid'), None)

        if body is not None:
            msg.get('body', [])[:] = body

        return msg

    def got_split_msg_fragment(self, msg):
        rid = msg.get('rid')
        body = msg.get('body', [])[:]

        if len(body) == 0:
            return

        if rid in self._partial_msgs:
            log.info('Got partial message chunk')
            prev_body = self._partial_msgs.get(rid)
            prev_body.extend(body)
        else:
            self._partial_msgs[rid] = body

    def incoming_command(self, sock, msg):
        mtf = msg.get('mtf', 0)

        self.got_split_msg_fragment(msg)
        if mtf == 0:
            log.info('got finalized message')
            msg = self.finalize_split_msg(msg)
        else:
            return

        rid = msg.get('rid')
        if rid is not None:
            req, callback = self._callbacks.pop(rid, (None, None))
            log.info('Got callback for rid=%r: %r', rid, callback)
            if callback is not None:
                callback.success(req, msg)

        getattr(self, 'handle_%s' % msg.mtype, self.handle_default)(msg)

    def handle_default(self, msg, *a):
        handler = self.message_handlers.get(msg.mtype)
        if handler is not None:
            handler(self).handle(msg)
        else:
            log.debug('Unknown message: %r', str(msg))

    def login_request(self, nc):
        self.event('login_challenge', nc)

    def send_login_response(self, username, password, nonce):
        '''
        Called by protocol in response to a login_challenge event
        '''

        password = password.lower()[:self.PASSWORD_MAX_LENGTH]

        if not isinstance(password, bytes):
            password = password.encode('utf8')

        if not isinstance(username, bytes):
            username = username.encode('utf8')

        res = myspace_auth_challenge_response(username, password, nonce)
        STA = 100
        ID = 1

        res = base64.b64encode(res)

        msg = msmsg((
            ('login2',    self.LOGINID),
            ('username',  username),
            ('response',  res),
            ('clientver', self.CLIENTVER),
            ('reconn',    0),
            ('status',    STA),
            ('id',        ID),
        ))

        self.send_msg(msg)

    def handle_session_start(self, session_info):
        '''
        After a successful login, we get session information with the following keys:
            sesskey           # key for this session
            proof             # ?  sometimes the same as userid
            userid            # unique number identifying this contact
            profileid         # is often same as userid
            uniquenick        # username
        '''

        g = session_info.get
        self.sesskey = g('sesskey')
        self.proof = g('proof')
        self.userid = g('userid')
        self.profileid = g('profileid')
        self.uniquenick = g('uniquenick')

        self.login_success()

    @Events.event
    def on_error(self, reason):
        self._on_closed_socket(self.sock)

    @Events.event
    def got_buddy(self, id, buddy):
        pass

    @Events.event
    def got_buddies(self, buddies):
        pass

    @Events.event
    def got_group(self, group):
        pass

    @Events.event
    def got_groups(self, groups):
        pass

    @Events.event
    def got_buddy_presence(self, buddyid, status, status_message):
        pass

    @Events.event
    def got_webchallenge_info(self, challenges):
        pass

    @Events.event
    def got_social_alerts(self, alerts):
        pass

    @Events.event
    def got_server_settings(self, settings):
        pass

    @Events.event
    def got_contact_info(self, bid, info, info_type):
        pass

    @Events.event
    def got_group_info(self, gid, info):
        pass

    @Events.event
    def got_im(self, bid, message):
        # convert message from short html to real html

        return bid, message

    @Events.event
    def got_group_message(self, source_id, group_id, actor_id, msg_text):
        pass

    @Events.event
    def got_zap(self, bid, zap_txt):
        pass

    @Events.event
    def got_typing(self, bid, typing):
        pass

    ###################################
    #  Message Creation/Sending
    ###################################

    @callbacks.callsback
    def send_msg(self, msg, use_rid=True, sock=None, callback=None):

        if sock is None:
            sock = getattr(self, 'sock', None)

        if sock is None:
            callback.error('not connected')
            return

        if use_rid:
            rid = self.rid.next()
            msg['rid'] = rid

            self._callbacks[rid] = (msg, callback)

        sock.send_msg(msg)

    def logout(self):
        if self.sesskey is None:
            return

        msg = msmsg((
                     ('logout', ''),
                     ('sesskey', self.sesskey),
                     ))

        self.send_msg(msg)

    def addbuddy(self, buddy_id, reason):
        msg = msmsg((
            ('addbuddy', ''),
            ('sesskey', self.sesskey),
            ('newprofileid', buddy_id),
            ('reason', reason),
        ))

        self.send_msg(msg)

    def deletebuddy(self, buddy_id):
        msg = msmsg((
            ('delbuddy', ''),
            ('sesskey', self.sesskey),
            ('delprofileid', buddy_id),
        ))

        self.send_msg(msg)

    def request_webchlg(self):
        msg = msmsg((
            ('webchlg', ''),
            ('sesskey', self.sesskey),
            ('n', 0),
        ))

        self.send_msg(msg)

    def send_typing(self, who, typing):
        msg = msmsg((
            ('bm',        BmMessage.Type.ActionMessage),
            ('sesskey',   self.sesskey),
            ('t',         who),
            ('cv',        self.CLIENTVER),
            ('msg',       '%typing%' if typing else '%stoptyping%'),
        ))
        self.send_msg(msg)

    @callbacks.callsback
    def send_im(self, who, message, callback=None):
        _message, message = message, msim_util.escape(message)

        msg = msmsg((
            ('bm',        BmMessage.Type.InstantMessage),
            ('sesskey',   self.sesskey),
            ('t',         who),
            ('cv',        self.CLIENTVER),
            ('msg',       message),
        ))
        try:
            self.send_msg(msg)
        except Exception, e:
            callback.error(e)
            raise
        else:
            callback.success()

    def request_self_im_info(self):
        self.send_msg(PersistMessage(self, 1, 4).Get())

    def request_self_social_info(self):
        self.send_msg(PersistMessage(self, 4, 5).Get(body=msim_util.msdict(UserID=str(self.userid))))

    def request_contact_general_info(self, uid):
        self.send_msg(PersistMessage(self, 0, 2).Get(body=msim_util.msdict(ContactID=str(uid))))

    def request_contact_im_info(self, uid):
        self.send_msg(PersistMessage(self, 1, 7).Get(body=msim_util.msdict(ContactID=str(uid))))

    def request_contact_social_info(self, uid):
        self.send_msg(PersistMessage(self, 4, 3).Get(body=msim_util.msdict(UserID=str(uid))))

    @callbacks.callsback
    def request_group_list(self, callback=None):
        self.send_msg(PersistMessage(self, 2, 6).Get(),
                      use_rid=True, callback=callback)

    def request_contact_list(self):
        self.send_msg(PersistMessage(self, 0, 1).Get())

    def set_user_prefs(self, prefs_dict):
        self.send_msg(PersistMessage(self, 1, 10).ActionSet(body=msim_util.msdict(**prefs_dict)))

    def add_all_friends(self, GroupName):
        self.send_msg(PersistMessage(self, 14, 21).Set(body=msim_util.msdict(GroupName=GroupName)))

    def add_top_friends(self, GroupName):
        self.send_msg(PersistMessage(self, 15, 22).Set(body=msim_util.msdict(GroupName=GroupName)))

    @callbacks.callsback
    def set_contact_info(self, buddy_id, infodict, callback=None):
        self.send_msg(PersistMessage(self, 0, 9).ActionSet(body=msim_util.msdict(**infodict)),
                      use_rid=True, callback=callback)

    @callbacks.callsback
    def delete_contact_info(self, buddy_id, callback=None):
        self.send_msg(PersistMessage(self, 0, 8).ActionDelete(body=msim_util.msdict(ContactID=buddy_id)),
                      use_rid=True, callback=callback)

    @callbacks.callsback
    def set_group_details(self, infodict=None, id=None, name=None, flag=None, position=None, callback=None):
        if infodict is None:
            infodict = {}
        else:
            infodict = dict(**infodict)

        if id is not None:
            infodict['GroupID'] = str(id)

        if name is not None:
            infodict['GroupName'] = str(name)

        if flag is not None:
            infodict['GroupFlag'] = str(flag)

        if position is not None:
            infodict['Position'] = str(position)

        self.send_msg(PersistMessage(self, 2, 16).Set(body=msim_util.msdict(**infodict)),
                      use_rid=True, callback=callback)

    @callbacks.callsback
    def delete_group(self, group_id, callback=None):
        self.send_msg(PersistMessage(self, 2, 16).Delete(body=msim_util.msdict(GroupID=str(group_id))),
                      use_rid=True, callback=callback)

    def delete_buddy(self, buddy_id):
        pass

    @callbacks.callsback
    def user_search(self, username, email, callback=None):
        if username is email is None:
            return

        if username is None:
            body = msim_util.msdict(Email=email)
        elif email is None:
            body = msim_util.msdict(UserName=username)

        self.send_msg(PersistMessage(self, 5, 7).Get(body=body),
                      use_rid=True, callback=callback)

    def set_status(self, status_int, status_string, locstring):
        msg = msmsg((
            ('status',     status_int),
            ('sesskey',    self.sesskey),
            ('statstring', status_string),
            ('locstring',  locstring),
        ))

        self.send_msg(msg)

    def request_social_alerts(self):
        self.send_msg(PersistMessage(self, 7, 10).Get())

#    def get_info(self, userid):
#        # Purpose of this message is unknown
#        msg = msmsg((
#                    ('getinfo',''),
#                    ('sesskey', self.sesskey),
#                    ('uid', str(userid)),
#                    ))
#
#        self.send_msg(msg)

    def edit_privacy_list(self,
                          add_to_block=None,
                          add_to_allow=None,
                          remove_from_block=None,
                          remove_from_allow=None,
                          presence_vis=None,
                          contact_vis=None,
                          ):

        idlist = msim_util.pipe_list()

        for (c, vis) in (('w', presence_vis), ('c', contact_vis)):
            if vis is None:
                continue

            if vis == 'anyone':
                idlist.append(c + '0')
            elif vis == 'list':
                idlist.append(c + '1')
            elif vis in (0, 1):
                idlist.append(c + str(vis))
            else:
                raise Exception('Invalid value for %r visibility: %r. valid values are ("anyone", "list", 0, 1).', c, vis)

        for (sym, val) in (('b+', add_to_block), ('a+', add_to_allow), ('b-', remove_from_block), ('a-', remove_from_allow)):
            if val is None:
                continue

            idlist.append(sym)
            if val == 'all':
                idlist.append('*')
            else:
                idlist.extend((str(x) for x in val))

        msg = msim_util.msmsg((
            ('blocklist', ''),
            ('sesskey', self.sesskey),
            ('idlist', str(idlist)),
        ))

        self.send_msg(msg)

    def send_exitchat(self, who, gid):
        msg = msmsg((
            ('bm',        BmMessage.Type.ActionMessage),
            ('sesskey',   self.sesskey),
            ('t',         who),
            ('cv',        self.CLIENTVER),
            ('gid',       gid),
            ('msg',       '!!!ExitChat'),
        ))
        self.send_msg(msg)
    ## --------------------------------


class MyspaceMessageHandler(object):
    def __init__(self, api):
        self.api = api

    def handle(self, msg):
        raise NotImplementedError


class LcMessage(MyspaceMessageHandler):

    def handle(self, msg):
        lc_count = msg.get('lc')
        if lc_count == 1:
            self.initial_lc(msg)
        elif lc_count == 2:
            self.login_response(msg)

    def initial_lc(self, msg):
        nc = msg.get('nc')
        self.api.login_request(nc)

    def login_response(self, msg):
        session_info = dict((k, msg.get(k)) for k in
                            ('sesskey', 'proof', 'userid', 'profileid', 'uniquenick'))

        self.api.handle_session_start(session_info)


class ErrorMessage(MyspaceMessageHandler):
    # Examples:
    # r'\error\\err\2\fatal\\errmsg\This request cannot be processed because you are not logged in.\final\ '
    # '\\error\\\\err\\1\\fatal\\\\errmsg\\There was a missing backslash parsing an incoming request.\\final\\'

    def handle(self, msg):
        if msg.get('fatal') is not None:
            self.handle_fatal(msg)
        else:
            log.error('Non-fatal Myspace error: %r', msg)

    def handle_fatal(self, msg):
        # we need to disconnect
        if msg.get('err', 0) == 6:
            # other user signed in
            self.api.on_error('other_user')
        elif msg.get('err', 0) in (259, 260):
            # 259 = invalid email (not sent anymore for security reasons)
            # 260 = incorrect password
            self.api.on_error('auth_error')
        elif msg.get('err', 0) in (2, 3):
            # 2 = 'Not logged in'
            # 3 = 'Invalid session key'
            self.api.on_error('session_expired')
        else:
            self.api.on_error('connection_lost')

        log.info('%s (%r)', repr(msg.get('err', 0)), msg)


class BmMessage(MyspaceMessageHandler):
    zap_id_str = '!!!ZAP_SEND!!!=RTE_BTN_ZAPS_'
    zap_strings = ['zap', 'whack', 'torch', 'smooch', 'hug', 'bslap', 'goose', 'hi-five', 'punk\'d', 'raspberry']

    class Type:
        Status = 100
        ActionMessage = 121
        UserInfo = 124
        InstantMessage = 1

    def handle(self, msg):

        bm_type = msg.get('bm')

        if bm_type == self.Type.Status:
            self.handle_status(msg)
        elif bm_type == self.Type.ActionMessage:
            self.handle_action_message(msg)
        elif bm_type == self.Type.UserInfo:
            self.handle_user_info(msg)
        elif bm_type == self.Type.InstantMessage:
            self.handle_im(msg)
        else:
            log.info('unknown bm message: %r', msg)

    def handle_im(self, msg):

        sender_id = msg.get('f')
        msg_text = msg.get('msg')
        gid = msg.get('gid')

        if gid is not None:
            msg_type = 'group'
        else:
            msg_type = self.im_type(msg_text)

        if msg_type == 'zap':
            zap_id = int(msg_text[len(self.zap_id_str):])
            self.api.got_zap(sender_id, self.zap_strings[zap_id])

        elif msg_type == 'typing':
            self.api.got_typing(sender_id, {'%typing%': True, '%stoptyping%': False}.get(msg_text, False))

        elif msg_type == 'im':
            self.api.got_im(sender_id, msim_util.minihtml_to_html(msg_text))

        elif msg_type == 'group':
            source_id = sender_id
            group_id = gid
            actor_id = msg.get('aid')

            self.api.got_groupmsg(source_id, group_id, actor_id, msg_text)

        else:
            log.info('unknown IM type: %r', msg)

    def im_type(self, msg):
        if msg.startswith(self.zap_id_str):
            return 'zap'

        elif msg in ('%typing%', '%stoptyping%'):
            return 'typing'

        elif msg.startswith('!!!'):
            return 'unknown'

        return 'im'

    def handle_status(self, msg):
        '''
        buddy status message
        example: '\\bm\\100\\f\\20075341\\fg\\0\\msg\\|s|0|ss|Offline\\final\\'
        '''

        body = msim_util.pipe_list(msg.get('msg', ''))
        body.pop(0)
        body = msim_util.pipe_dict(body)

        source_id = msg.get('f')
        status_int = int(body.get('s'))
        status_message = body.get('ss')  # status message?

        # other keys:
        # ('ls', '')   - ??
        # ('ip', '170402424')   - ip address?
        # ('p', '0')   - ??
        # ('caps', '0')   - capabilities?
        # ('ts', '1250263988')   - timestamp

        status = {
                  0: 'offline',
                  1: 'available',
                  2: 'idle',
                  5: 'away',
                  }.get(status_int, 'available')

        self.api.got_buddy_presence(source_id, status, status_message)

        log.info('got bm_100 message: %r', body)

    def handle_action_message(self, msg):
        '''
        action message: zap or typing notification

        also IMs from the web client:
         '\\bm\\121\\f\\258249087\\cv\\745\\fg\\0\\msg\\<p>test</1p>\\final\\'
        '''
        log.info('Got action message: %r', msg)
        self.handle_im(msg)

    def handle_user_info(self, msg):
        '''
        user profile dictionary
        '''
        log.info('Got user info message: %r', msg)


class PersistMessage(object):
    def __init__(self, proto, dsn, lid, sesskey=True, uid=True):
        self.proto = proto
        self.dsn = dsn
        self.lid = lid
        self.use_sesskey = sesskey
        self.use_uid = uid

    def _do_command(self, cmd, body):
        parts = [('persist', '1')]

        if self.use_sesskey:
            parts.append(('sesskey', self.proto.sesskey))

        parts.append(('cmd', cmd))
        parts.append(('dsn', self.dsn))

        if self.use_uid:
            parts.append(('uid', self.proto.userid))

        parts.append(('lid', self.lid))
        parts.append(('body', body))

        msg = msmsg(parts)

        return msg

    def Get(self, body=''):
        return self._do_command(msmsg.CMD.Get, body)

    def Set(self, body=''):
        return self._do_command(msmsg.CMD.Set, body)

    def Delete(self, body=''):
        return self._do_command(msmsg.CMD.Delete, body)

    def ActionSet(self, body=''):
        return self._do_command(msmsg.CMD.Action | msmsg.CMD.Set, body)

    def ActionDelete(self, body=''):
        return self._do_command(msmsg.CMD.Action | msmsg.CMD.Delete, body)


#-------

class PersistrMessage(MyspaceMessageHandler):
    def handle(self, msg):
        cmd = msg.get('cmd', 0)
        lowbits = cmd & 0xFF

        action = {msg.CMD.Get: 'get',
                  msg.CMD.Set: 'set',
                  msg.CMD.Delete: 'delete'}.get(lowbits, 'unknown')

        cmd_info = [action]
        if cmd & msg.CMD.Reply:
            cmd_info.append('reply')
        else:
            cmd_info.append('request')

        if cmd & msg.CMD.Action:
            cmd_info.append('action')
        else:
            cmd_info.append('query')

        if cmd & msg.CMD.Error:
            cmd_info.append('error')
        else:
            cmd_info.append('normal')

        dsn = msg.get('dsn')
        lid = msg.get('lid')

        cmd_info.append(dsn)
        cmd_info.append(lid)

        log.info('got persistr command: dsn = %r, lid = %r, cmd = %r = %r', dsn, lid, cmd, cmd_info)

        dlc = (dsn, lid, cmd)

        GetReply = msg.CMD.Get | msg.CMD.Reply

        body = msg.get('body', {})

        if   dlc == (0, 1, GetReply):
            self.handle_im_buddylist(msg, body)
        elif dlc == (0, 2, GetReply):
            self.handle_contact_info_basic(msg, body)
        elif dlc == (1, 4, GetReply):
            self.handle_self_info_im(msg, body)
        elif dlc == (1, 7, GetReply):
            self.handle_contact_info_im(msg, body)
        elif dlc == (2, 6, GetReply):
            self.handle_group_list(msg, body)
        elif dlc == (4, 3, GetReply):
            self.handle_contact_social_info(msg, body)
        elif dlc == (4, 5, GetReply):
            self.handle_self_social_info(msg, body)
        elif dlc == (5, 7, GetReply):
            self.handle_usersearch_response(msg, body)
        elif dlc == (7, 10, GetReply):
            self.handle_social_alerts(msg, body)
        elif dlc == (17, 26, GetReply):
            self.handle_webchallenges(msg, body)
        elif dlc == (101, 20, GetReply):
            self.handle_server_settings(msg, body)
        elif dlc == (2, 16, msg.CMD.Set | msg.CMD.Reply):
            self.handle_group_info_set(msg, body)
#        elif dlc == (512, 20, GetReply):
#            ad settings? chatroom uids? dunno. more server settings maybe
        else:
            self.handle_unknown(msg, body)

    def handle_unknown(self, msg, body):
        log.info('Got unknown persistr message: %r', msg)

    def handle_im_buddylist(self, msg, body):
        '''
        list of buddies
        '''
        buddies = msim_util.obj_list_from_msdict(body)

        log.info('got %r buddies!', len(buddies))

        for i, buddy in enumerate(buddies):
            id = buddy.get('ContactID', buddy.get('UserID'))
            if id is None:
                log.error('This info has no ID! %r', buddy)
                log.info('buddy #%r skipped (info = %r)', i, buddy)
                continue

            self.api.got_buddy(id, buddy)

        self.api.got_buddies(buddies)

    def handle_contact_info_basic(self, msg, body):
        bid = body.get('ContactID')

        if bid is not None:
            self.api.got_contact_info(bid, body, 'general')

    def handle_self_info_im(self, msg, body):
        '''
        {
        'lid': 4,
        'body': [['UserID', '77232795'],
                 ['Sound', 'True'],
                 ['PrivacyMode', '0'],
                 ['ShowOnlyToList', 'False'],
                 ['OfflineMessageMode', '0'],
                 ['Headline', 'my myspace IM status'],
                 ['AvatarUrl', ''],
                 ['ShowAvatar', 'False'],
                 ['Alert', '1'],
                 ['IMName', ''],
                 ['LastLogin', '128956033800000000'],
                 ['ClientVersion', '673'],
                 ['AllowBrowse', 'True'],
                 ['IMLang', ''],
                 ['LangID', '0'],
                 ['OfflineMsg', ''],
                 ['SkyStatus', '1'],
                 ['OsVersion', '']],
         'uid': 77232795,
         'persistr': '',
         'cmd': 257,
         'dsn': 1,
         'rid': 1616944}
        '''
        self.api.got_buddy(body.get('UserID'), body)
        self.handle_contact_info_im(msg, body)

    def handle_contact_info_im(self, msg, body):
        '''
        response to _request_contact_im_info
        body:
         UserID=77232795
         Sound=True
         PrivacyMode=0
         ShowOnlyToList=False
         OfflineMessageMode=0
         Headline=my myspace IM status
         AvatarUrl=
         ShowAvatar=False
         Alert=1
         IMName=
         LastLogin=128950852200000000
         ClientVersion=673
         AllowBrowse=True
         IMLang=
         LangID=0
         OfflineMsg=
         SkyStatus=1
         OsVersion=
        '''
        bid = body.get('UserID')

        if bid is None:
            return

        self.api.got_contact_info(bid, body, 'im')

    def handle_group_list(self, msg, body):
        groups = msim_util.obj_list_from_msdict(body)

        for group in groups:
            self.api.got_group(group)

        self.api.got_groups(groups)

    def handle_contact_social_info(self, msg, body):
        '''
        reply to _request_contact_social_info

        body:
         [['UserID', '20075341'],
          ['UserName', 'leftonredryan'],
          ['DisplayName', 'Sir Psycho Sexy (that is me)'],
          ['RealName', ''],
          ['ImageURL', 'http://c4.ac-images.myspacecdn.com/images01\\5/m_c1fbe305c005d2abbdad082f943c1c9b.jpg'],
          ['LastImageUpdated', '128290124400000000'],
          ['BandName', ''],
          ['SongName', ''],
          ['Age', '25'],
          ['Gender', 'M'],
          ['Location', 'Providence, Rhode Island, US'],
          ['TotalFriends', '0']]
        '''

        bid = body.get('UserID')

        if bid is None:
            return

        self.api.got_contact_info(bid, body, 'social')

    def handle_self_social_info(self, msg, body):
        '''
        {
         'lid': 5,
         'body': [['UserID', '77232795'],
                  ['UserName', 'synae00'],
                  ['DisplayName', 'Michael'],
                  ['RealName', 'Michael Dougherty'],
                  ['ImageURL', 'http://c4.ac-images.myspacecdn.com/images01/59/m_3116840be2b986062219d0bd5f39d5fb.jpg'],
                  ['LastImageUpdated', '128486984400000000'],
                  ['BandName', ''],
                  ['SongName', ''],
                  ['Age', '24'],
                  ['Gender', 'M'],
                  ['Location', 'Rochester, New York, US'],
                  ['TotalFriends', '0']],
         'uid': 77232795,
         'persistr': '',
         'cmd': 257,
         'dsn': 4,
         'rid': 1616946}
        '''
        self.handle_contact_social_info(msg, body)

    def handle_usersearch_response(self, msg, body):
        log.info('got usersearch response: %r', body)
        self.api.got_buddy(body.get('ContactID', body.get('UserID')), body)
        #self.handle_contact_info_im(msg, body)

    def handle_social_alerts(self, msg, body):
        '''
         \\persistr\\\\cmd\\257\\dsn\\7\\uid\\90302818\\lid\\10\\rid\\1\\body\\PictureComment=On\\final\\
        '''

        if '\xc2\x80=' in str(body):
            # myspace sends a weird message every once in a while that messes with our alerts
            # we need to ignore it.
            return

        log.info('got alert update: %r', body)
        self.api.got_social_alerts(body)

    def handle_webchallenges(self, msg, body):
        challenge_info = msim_util.obj_list_from_msdict(body)

        self.api.got_webchallenge_info(challenge_info)

    def handle_server_settings(self, msg, body):
        '''
        Mostly settings for the app governing how it interacts with the server.
        e.g. AlertPollInterval is how often to poll for alert changes.
        '''
        self.api.got_server_settings(body)

    def handle_group_info_set(self, msg, body):
        log.info('set group info: %r', msg)
        if 'GroupID' in body.keys():
            self.api.got_group_info(body['GroupID'], body)
        else:
            log.info('No GroupID in group info')
