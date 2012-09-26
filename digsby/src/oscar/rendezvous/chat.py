'''

Oscar chat functionality

'''

from oscar.rendezvous.rendezvous import rdv_snac, rdv_types, rendezvous_tlvs as rdv_tlvs
from oscar import capabilities
from oscar.OscarUtil import tlv, s_tflv
import oscar
from util import callsback
from common import profile
from logging import getLogger; log = getLogger('oscar.rdv.chat')
from common.Protocol import ChatInviteException

import hooks
import struct

@callsback
def invite(o, screenname, chatcookie, message = None, callback=None):
    '''
    Given a chat cookie (see OscarConversation) and a screenname, sends an
    invite to the buddy asking them to join the
    '''

    clen = len(chatcookie)
    xdata = struct.pack('!HB%ds' % clen, 4, clen, chatcookie) + '\x00\x00'

    if message is None:
        message = 'Join me in this chat!'

    data = ''.join([
        tlv(0x0a, 2, 1),
        tlv(0x0f),
        tlv(0x0c, message),
        tlv(rdv_tlvs.extended_data, xdata)])

    snac = rdv_snac(screenname = screenname,
                    capability = capabilities.by_name['chat_service'],
                    type = rdv_types.request,
                    data = data)

    def on_error(snac, exc):
        try:
            (fam, fam_name), (errcode, errmsg), (_, _) = exc.args
        except Exception:
            pass
        else:
            if (fam, errcode) == (4, 4): # buddy is offline
                reason = ChatInviteException.REASON_OFFLINE
            elif (fam, errcode) == (4, 9): # buddy doesn't support groupchat
                reason = ChatInviteException.REASON_GROUPCHAT_UNSUPPORTED
            else:
                reason = ChatInviteException.REASON_UNKNOWN

            callback.error(ChatInviteException(reason))
            return True # stops snac error popup

    o.send_snac(*snac, **dict(req=True, cb=callback.success, err_cb=on_error))

def unpack_chat_invite(data):
    fmt = (('rendtlvs', 'named_tlvs', -1, rdv_tlvs),)
    rendtlvs, data = oscar.unpack(fmt, data)
    invite_msg = oscar.decode(rendtlvs.user_message, getattr(rendtlvs, 'encoding', 'ascii'))
    xdata = rendtlvs.extended_data

    cfmt = (('four', 'H'), ('cookie', 'pstring'))
    _four, chatcookie, _extra = oscar.util.apply_format(cfmt, xdata)
    return invite_msg, chatcookie

class OscarChatConnection(object):
    def __init__(self, oscar, inviting_buddy):
        self.oscar = oscar
        self.buddy = inviting_buddy

    def handlech2(self, message_type, data):
        invite_msg, chatcookie = unpack_chat_invite(data)

        def on_yes():
            from common import netcall
            netcall(lambda: self.oscar.join_chat(cookie=chatcookie))

        profile.on_chat_invite(
            protocol = self.oscar,
            buddy = self.buddy,
            message = invite_msg,
            room_name = chatcookie,
            on_yes=on_yes)

def chat_invite_handler(o, screenname, cookie):
    return OscarChatConnection(o, o.get_buddy(screenname))

def initialize():
    log.info('\tloading rendezvous handler: chat service')
    import oscar.rendezvous.peer as peer
    peer.register_rdv_factory('chat_service', chat_invite_handler)

hooks.register('oscar.rdv.load', initialize)

