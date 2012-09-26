from logging import getLogger
log = getLogger('msn.nssb')

import msn

from msn import MSNTextMessage

from util import callsback
from util.primitives.funcs import get
from util.Events import EventMixin

class NSSBAdapter(EventMixin):
    '''
    Chatting with federated (yahoo) buddies happens over the NS protocol, but
    MSNConversations are made to work with Switchboard protocol implementations.

    This class exists to provide a switchboard interface to the NS.
    '''

    _instances = []

    events = EventMixin.events | set ((
        'on_buddy_join',
        'on_buddy_leave',
        'on_buddy_timeout',
        'on_conn_success',
        'on_authenticate',
        'disconnect',
        'contact_alias',
        'needs_auth',
        'recv_error',
        'recv_text_msg',
        'send_text_msg',
        'typing_info',
        'recv_action',

        'recv_p2p_msg',
        'transport_error',
    ))

    def __init__(self, ns, to_invite=()):

        self.ns = ns
        # bind events to NS
        self.principals = []
        self.to_invite = to_invite

        self.__chatbuddy = get(to_invite, 0, None)

        EventMixin.__init__(self)

    @property
    def _chatbuddy(self):
        return self.__chatbuddy

    @property
    def _closed(self):
        return not self.connected

    @property
    def self_buddy(self):
        return self.ns.self_buddy

    @callsback
    def invite(self, bname, callback=None):
        self.buddy_join(bname)
        callback.success()

    def buddy_join(self, bname):
        if self.__chatbuddy is None:
            self.__chatbuddy = bname
        else:
            assert self.__chatbuddy == bname

        if bname not in self.principals:
            self.principals.append(bname)
            self.event('on_buddy_join', bname)

    def send_text_message(self, message):

        #payload = MSNTextMessage(message)
        payload = message

        netid = 32
        msg = msn.Message('UUM', self.__chatbuddy, netid, 1, payload = str(payload))

        self.ns.socket.send(msg, trid=True, callback=sentinel)
        self.event('send_text_msg', payload)

    def on_send_message(self, msg):
        return NotImplemented

    def leave(self):
        if self in self._instances:
            self._instances.remove(self)
        self.event('disconnect')

    @callsback
    def connect(self, callback=None):
        log.info('NSSB.connect()')
        self._instances.append(self)

        self.event('on_conn_success', self)
        log.info('NSSB.on_conn_success()')

        for bname in self.to_invite:
            self.buddy_join(bname)

        self.event('on_authenticate')
        log.info('NSSB.on_authenticate()')
        callback.success()

    def connected(self):
        return self.ns.connected()

    def disconnect(self):
        self.event('disconnect')

    def close_transport(self):
        pass

    def on_conn_fail(self):
        self.event('recv_error')

    def authenticate(self, bname):
        self.event('on_authenticate')

    def send_typing_status(self, name, status):
        '''
        UUM 0 bob@yahoo.com 32 2 87\r\n
        MIME-Version: 1.0\r\n
        Content-Type: text/x-msmsgscontrol\r\n
        TypingUser: alice@live.com\r\n
        \r\n
        '''

        payload = []
        line = lambda k,v: '%s: %s' % (k,v)
        add = payload.append
        add(line('MIME-Version', '1.0'))
        add(line('Content-Type', 'text/x-msmsgscontrol'))
        add(line('TypingUser', name))
        add('')
        add('')

        payload = '\r\n'.join(payload)

        netid = 32

        msg = msn.Message('UUM', self.__chatbuddy, netid, 2, payload = payload)

        self.ns.socket.send(msg, trid=True, callback=sentinel)

    def on_error(self, msg):
        pass

    def recv_msg(self, msg):
        #type = msg.type

        try:
            getattr(self, 'recv_msg_%s' % msg.type, self.recv_msg_unknown)(msg)
        except Exception, e:
            import traceback
            traceback.print_exc()

            log.error('Exception handling MSG: %r, msg = %r', e, msg)

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
        msg = MSNTextMessage.from_net(msg.payload)

#        self.event('contact_alias', name, nick)
        self.event('recv_text_msg', name, msg)

    def recv_msg_control(self, msg):
        '''
        msg_control(msg, src_account, src_display)

        This is called when a message comes in with type='text/x-msmsgscontrol'
        Generally, these are typing indicators.

        @param msg:           msnmessage
        '''
        name = msg.args[0]

        self.event('typing_info', name, bool(msg.payload.get('TypingUser', False)))

    def recv_msg_unknown(self, msg):
        log.error("ohnoes don't know this message type: %r, %r", msg.type, msg)

    @classmethod
    def incoming(cls, msg):
        name = msg.args[0]

        for x in cls._instances:
            if x.__chatbuddy  == name:
                # match
                break

        else:
            x = cls(None)

        x.buddy_join(name)
        x.recv_msg(msg)
