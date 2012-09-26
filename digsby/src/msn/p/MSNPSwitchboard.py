import util.Events as Events

from msn import CommandProcessor

import logging
log = logging.getLogger('msn.p.sb')


class MSNSwitchboard(Events.EventMixin, CommandProcessor):

    events = Events.EventMixin.events | set ((
        'on_buddy_join',
        'on_buddy_leave',
        'on_buddy_timeout',
        'on_conn_success',
        'on_authenticate',
        'disconnect',
        'contact_alias',
        'needs_auth',
        'recv_error',
        'recv_action',
        'transport_error',
    ))

    def __init__(self, SckCls_or_sck, to_invite=(),
                 server=('',0),cookie=None, sessionid=None):

        Events.EventMixin.__init__(self)
        CommandProcessor.__init__(self, log)

        self._cookie = cookie
        self._session = sessionid

        self.has_connected = False

        self.principals = []

        if type(SckCls_or_sck) is type:
            self.socket    = None
            self._socktype = SckCls_or_sck
            self._server   = server
        else:
            self.socket    = SckCls_or_sck
            self._socktype = type(self.socket)
            self._server   = self.socket.getpeername()

        self._p2p_transport = None

        self.bind('on_conn_success', lambda this: setattr(this, 'has_connected', True))

    @property
    def _closed(self):
        return self.has_connected and ((not self.socket) or self.socket._closed)

    @property
    def self_buddy(self):
        return NotImplemented

    def invite(self, bname):
        #cal
        return NotImplemented

    def send_text_message(self, message, callback):
        #msg
        return NotImplemented

    def on_send_message(self, msg):
        return NotImplemented

    def leave(self):
        #out
        return NotImplemented

    def send(self, msg):
        # For transport. NOT for protocol
        return NotImplemented

    def connect(self):
        return NotImplemented
    def disconnect(self):
        return NotImplemented
    def close_transport(self):
        return NotImplemented
    def on_conn_fail(self):
        return NotImplemented
    def on_conn_success(self):
        return NotImplemented
    def on_complete_auth(self):
        return NotImplemented
    def close_connection(self):
        return NotImplemented


    def on_error(self, msg):
        CommandProcessor.on_error(self, msg)
        self.event('recv_error', msg)


