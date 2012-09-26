import logging

from util.callbacks import callsback
from util.Events import event

import msn
from msn import Message, MSNTextMessage
from msn.p import Switchboard as Super

log = logging.getLogger('msn.p8.sb')

defcb = dict(trid=True, callback=sentinel)

class MSNP8Switchboard(Super):
    events = Super.events | set((
        'recv_text_msg',
        'send_text_msg',
        'typing_info',

    ))

    def connect(self):
        if self.socket is None:
            log.info('Creating %s', self._socktype)
            self.socket = self._socktype()
            self.socket.bind('on_connect', self.on_conn_success)
            self.socket.bind('on_close', self.leave)
            self.socket.bind('on_conn_error', self.conn_failed)
            self.socket.bind('on_message', self.on_message)
            log.info('Bound events to %s', self.socket)
            conn_args = self.socket.connect_args_for('SB', self._server)
            self.socket._connect(*conn_args)

        else:
            log.critical('Connect called on a switchboard that already has a socket')

    @callsback
    def invite(self, bname, callback=None):
        self._invite(bname, callback)

    def conn_failed(self, sck, e = None):
        log.error('Failed to connect!: %r, %r', sck, e)
        self.event('transport_error', e or sck)

    def on_conn_success(self, s):
        log.info('Connection success. Calling authenticate.')
        self.event('on_conn_success', self)
        self.event('needs_auth')
        #self.authenticate()

    def authenticate(self, username):
        if self._session is None:
            log.info('Authenticating for new session.')
            self.socket.send(Message('USR', username, self._cookie), **defcb)
        else:
            log.info('Authenticating for session in progress.')
            self.socket.send(Message('ANS', username, self._cookie, self._session), **defcb)

    def leave(self, sck=None):
        # unbind events
        log.debug('leaving %r', self)
        if self.socket is not None:
            self.socket._disconnect()
        self.on_disconnect()

    def on_disconnect(self):
        del self.principals[:]
        self.event('disconnect')
        self.socket = None
        self._session = None
        #self._cookie = None

    def connected(self):
        return (self.socket is not None)

    def recv_usr(self, msg):
        ok, name, nick = msg.args
        nick = nick.decode('url').decode('utf-8') or None
        self.event('contact_alias', name, nick)
        assert ok == 'OK'
        self._session = self._cookie.split('.',1)[0]
        self.on_authenticate()

    @event
    def on_authenticate(self):
        log.info('Authenticated.')

    def _invite(self, bname, callback):
        self.socket.send(Message('CAL', bname), trid=True, callback=callback)

    def recv_ack(self, msg):
        log.debug('Got ack: %s', str(msg).strip())

    def recv_ans(self, msg):
        '''
        ANS (ANSwer)

        This command is sent by the server after we send our ANS to login.

        @param socket:    the socket the command came from
        @param trid:      trid assocated with this command
        @param status:    the status of our ANS....has to be OK or we would
                          have been disconnected already!
        '''

        status, = msg.args
        assert status == 'OK'
        self.on_authenticate()

    def recv_msg(self, msg):

        try:
            getattr(self, 'recv_msg_%s' % msg.type, self.recv_msg_unknown)(msg)
        except Exception, e:
            import traceback
            traceback.print_exc()
            log.error('Exception handling MSG! error = %r, msg = %r', e, msg)

    def recv_msg_plain(self, msg):
        '''
        msg_plain(msg, src_account, src_display)

        this is called when a msg comes in with type='text/plain'

        @param socket:        the socket it arrived from (better be self.socket!)
        @param msg:           the rfc822 object representing the MIME headers and such
        @param src_account:   the email address/passport this comes from
        @param src_display:   the display name of the buddy who sent it
        @param *params:       more stuff!
        '''

        name, nick = msg.args[:2]
        nick = msn.util.url_decode(nick).decode('utf-8') or None
        msg = MSNTextMessage.from_net(msg.payload)

        self.event('contact_alias', name, nick)
        self.event('recv_text_msg', name, msg)

    def recv_msg_control(self, msg):
        '''
        msg_control(msg, src_account, src_display)

        This is called when a message comes in with type='text/x-msmsgscontrol'
        Generally, these are typing indicators.

        @param msg:           msnmessage
        '''
        name, nick = msg.args[:2]
        nick = msn.util.url_decode(nick).decode('utf-8') or None

        self.event('contact_alias', name, nick)
        self.event('typing_info', name, bool(msg.payload.get('TypingUser', False)))

    def recv_msg_notification(self, msg):
        '''
        msg_notification(msg, src_account, src_display)

        No idea what these are. So, raise for now...

        @param msg:           msnmessage
        '''
        #TODO: find out what this is for.
        name, nick = msg.args[:2]
        self.event('contact_alias', name, nick)

    @event
    def on_buddy_join(self, name):
#        if name in self._to_invite:
#            self._to_invite.remove(name)

        self.principals.append(name)
        return name

    def recv_cal(self, msg):
        ringing, session = msg.args
        # event: on_invite

    def recv_iro (self, msg):
        '''
        IRO (In ROom)

        This is sent to us when we connect to notify us of who is in the room.

        @param socket:        the socket the message arrived from
        @param trid:          the trid associated with this command
        @param rooster:       the 'rooster number' for this buddy
        @param roostercount:  the total number of 'roosters' to expect
        @param passport:      the passport name of the buddy (email address)
        @param buddyname:     the friendly name of the buddy
        @param *args:         more stuff!
        '''

        rooster, roostercount, name, nick= msg.args[:4]
        rooster = int(rooster)
        roostercount = int(roostercount)
        nick = msn.util.url_decode(nick).decode('utf-8') or None

        self.event('contact_alias', name,nick)
        self.on_buddy_join(name)

    def recv_joi (self, msg):
        '''
        JOI (Buddy JOIn)

        A buddy is joining the conversation

        @param socket:    the socket the command came from
        @param trid:      trid assocated with this command
        @param acct:      the email addresss of the joining buddy
        @param fn:        the friendly name (display name) of the buddy
        @param sessid:    the session ID of this session
        '''

        name, nick = msg.args[:2]
        nick = msn.util.url_decode(nick).decode('utf-8') or None

        self.event('contact_alias', name, nick)
        self.on_buddy_join(name)

    def recv_bye (self, msg):
        '''
        BYE (BYE)

        A buddy is leaving the conversation (saying bye!)

        @param socket:    the socket the command came from
        @param trid:      trid assocated with this command
        @param buddy:     the buddyname leaving
        '''

        notify = True
        try:
            name, = msg.args
        except:
            name, reason = msg.args
            if int(reason) == 1:
                self.on_buddy_timeout(name)
                notify = False

        self.on_buddy_leave(name, notify)

    @event
    def on_buddy_leave(self, name, notify=True):
        if name in self.principals:
            self.principals.remove(name)
        return name, notify

    @event
    def on_buddy_timeout(self, name):
        #self._to_invite.append(name)
        return name

    def recv_msg_unknown(self, msg):
        log.error('Unknown message type! %r', msg)

    def recv_msg_invite(self, msg):
        '''
---
Exception handling MSG!
MSG digsby03@hotmail.com digsby%20oh%20threesus 502
MIME-Version: 1.0
Content-Type: text/x-msmsgsinvite; charset=UTF-8

Application-Name: an audio conversation
Application-GUID: {02D3C01F-BF30-4825-A83A-DE7AF41648AA}
Session-Protocol: SM1
Context-Data: Requested:SIP_A,;Capabilities:SIP_A,;
Invitation-Command: INVITE
Avm-Support: 7
Avm-Request: 2
Invitation-Cookie: 24443504
Session-ID: {EE086C37-D672-44C2-9AA9-57151CEB0BEF}
Conn-Type: IP-Restrict-NAT
Sip-Capability: 1
Public-IP: 129.21.160.34
Private-IP: 192.168.1.102
UPnP: FALSE

---
Exception handling MSG!
MSG digsby03@hotmail.com digsby%20oh%20threesus 317
MIME-Version: 1.0
Content-Type: text/x-msmsgsinvite; charset=UTF-8

Invitation-Command: CANCEL
Cancel-Code: TIMEOUT
Invitation-Cookie: 24443504
Session-ID: {EE086C37-D672-44C2-9AA9-57151CEB0BEF}
Conn-Type: IP-Restrict-NAT
Sip-Capability: 1
Public-IP: 129.21.160.34
Private-IP: 192.168.1.102
UPnP: FALSE
        '''
        return log.info('msg invite %s', msg)
        m = Message(msg.body())

        c = m['Invitation-Cookie']
        try:
            a = self.activities[c]
        except KeyError:
            a = self.activities.setdefault(c, msn.slp.SLP(self, name, c))

        a.incoming(m)

    def recv_msg_datacast(self, msg):
        log.info('Received datacast')
        try:
            name, nick = msg.args
            nick = nick.decode('url').decode('utf-8')
            body = msg.payload

            id = int(msg.id)

            if id == 1:
                action_type = 'nudge'
                action_text = None
            elif id == 2:
                action_type = 'wink'
                action_text = None
            elif id == 4:
                action_type = 'custom'
                action_text = msg.data
            else:
                return
                #action_text = 'sent an unknown datacat'

            self.event('recv_action', name, action_type, action_text)
            #self.system_message('%s %s' % (b.alias, action_text))
        except Exception,e :
            import traceback; traceback.print_exc()
            raise e

    def recv_msg_caps(self, msg):
        log.info(msg.name + ' is using gaim/pidgin')

#    def msg_p2p(self, msg, name, nick, len):
#        msg = msg.body()
#
#        h, b, f = msg[:48], \
#                  msg[48:-4],\
#                  msg[-4:]
#
#        sess_id, base_id = struct.unpack('>II', h[:8])
#
#        if not sess_id and base_id not in self.activities:
#            self.activities[base_id] = msn.slp.SLP(self, name, base_id)
#        self.activities[base_id].incoming(h,b,f)
#

    @callsback
    def send_text_message(self, body, callback):
        if not self.connected:
            callback.error('connection lost')
            raise Exception('connection lost')

        if isinstance(body, unicode):
            _body, body = body, body.encode('utf8')

        cmd = msn.MSNCommands.MSG('N', payload = str(body))

        def check_nak(sck, msg):
            if msg.cmd == 'NAK':
                msg.source_message = body
                callback.error(msg)
            else:
                callback.success()

        self.socket.send(cmd, trid=True, success=check_nak, error=lambda sck, emsg: callback.error(emsg))
        #self.event('send_text_msg', body)

    def send_typing_status(self, name, status):
        if not self.connected:
            return

        if status:
            body = "MIME-Version: 1.0\r\n" \
                   "Content-Type: text/x-msmsgscontrol\r\n" \
                   "TypingUser: %s\r\n\r\n\r\n" % name

            self.socket.send(Message('MSG', 'U', payload=body), **defcb)


