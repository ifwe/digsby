import util.Events as Events
import msn.MSNCommands as MSNCommands

import logging
log = logging.getLogger("msn.p21.sb")

import uuid
import hashlib
import sysident

import msn
import msn.MSNCommands as MSNC
from msn.p15 import Switchboard as Super

defcb = dict(trid=True, callback=sentinel)

class MSNP21Switchboard(msn.NSSBAdapter):
    def __init__(self, ns, to_invite = (), **kw):
        raise Exception()
        super(MSNP21Switchboard, self).__init__(ns, to_invite)

    @classmethod
    def incoming(cls, msg):
        log.info("incoming: %r", msg)
        name = msg.name

        for x in cls._instances:
            if x._chatbuddy  == name:
                # match
                break

        else:
            assert False
            x = cls(None)

        x.buddy_join(name)
        x.recv_msg(msg)

    def recv_msg_control_typing(self, msg):
        self.event('typing_info', msg.name, True)

    def recv_msg_unknown(self, msg):
        log.info("Got an unknown message: %r (%r)", msg, str(msg))

    def recv_msg_text(self, msg):
        textmsg = msn.MSNTextMessage.from_net(msg.payload)
        self.event('recv_text_msg', msg.name, textmsg)

