""" AsyncSocket subclass for MySpace IM protocol.

    Converts msmsg objects to data for sending, and translates incoming data into msmsg objects. """
import util.Events as Events
import logging
log = logging.getLogger('msim.sock')
# log.setLevel(1)

from common import socket
from MSIMUtil import msmsg


class myspace_socket(socket, Events.EventMixin):
    events = Events.EventMixin.events | set((
         'on_message',
         'on_close',
    ))

    def __init__(self):
        socket.__init__(self)
        Events.EventMixin.__init__(self)
        self.buffer = ''
        self.set_terminator('\\final\\')
        log.info('socket created')

    def found_terminator(self):
        log.debug_s('in : %r %r', self.buffer, self.terminator)
        self.event('on_message', self, msmsg(self.buffer + self.terminator))
        self.buffer = ''
        self.set_terminator(self.terminator)

    def collect_incoming_data(self, data):
        self.buffer += data

    def send_msg(self, msg):
        try:
            bytes = msg.serialize()
            log.debug_s('out: %r', bytes)
            socket.push(self, bytes)
        except Exception, e:
            self.handle_error(e)
            log.error('Error while trying to send this message: %r', msg)

    def handle_close(self):
        log.warning('socket closed: %r', self)
        self.close()

    def handle_error(self, e=None):
        # TODO: test connection
        socket.handle_error(self, e)
        log.warning('error in socket %r: %r', self, e)
        self.close()

    def close(self):
        self.event('on_close', self)
        socket.close(self)
