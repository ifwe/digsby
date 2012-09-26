from decimal import Decimal
from jabber.jabber_util.functions import xpath_eval
from logging import getLogger
from peak.util.addons import AddOn
from pyxmpp.jid import JID
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.utils import from_utf8, to_utf8
from pyxmpp.xmlextra import get_node_ns_uri
import hooks
import libxml2
import sys
import traceback

log = getLogger('plugins.digsby_muc_invitations')

CONFERENCE_NS = 'jabber:x:conference'
MUC_USER_NS   = 'http://jabber.org/protocol/muc#user'

class MUCInvitations(AddOn):
    def __init__(self, subject):
        self.protocol = subject
        super(MUCInvitations, self).__init__(subject)

class DirectMUCInvitations(MUCInvitations):
    def setup(self, stream):
        self.stream = stream
        log.debug('setting up XEP 0249 message handler')
        stream.set_message_handler('normal', self.handle_message,
                              namespace = CONFERENCE_NS,
                              priority = 98)

    def handle_message(self, stanza):
        '''
        <message
            from='crone1@shakespeare.lit/desktop'
            to='hecate@shakespeare.lit'>
          <x xmlns='jabber:x:conference'
             jid='darkcave@macbeth.shakespeare.lit'
             password='cauldronburn'
             reason='Hey Hecate, this is the place for all good witches!'/>
        </message>
        '''
        try:
            fromjid = stanza.get_from()
            x = stanza.xpath_eval('c:x',{'c':CONFERENCE_NS})[0]
            roomjid  = JID(from_utf8(x.prop('jid')))
            roomname = JID(roomjid).node
            password = x.prop('password')
            password = from_utf8(password) if password else None
            reason = x.prop('reason')
            reason = from_utf8(reason) if reason else None
        except Exception:
            traceback.print_exc()
            return False
        else:
            if not all((roomname, fromjid)):
                return False
            self.protocol.hub.on_invite(
                protocol = self.protocol,
                buddy = fromjid,
                room_name = roomname,
                message = reason,
                on_yes = lambda: self.protocol.join_chat_jid(roomjid,
                                    self.protocol.self_buddy.jid.node))
            return True # don't let other message handlers do it

def session_started(protocol, stream, *a, **k):
    DirectMUCInvitations(protocol).setup(stream)
    MediatedMUCInvitations(protocol).setup(stream)

def initialized(protocol, *a, **k):
    protocol.register_feature(CONFERENCE_NS)

class MediatedMUCInvitations(MUCInvitations):
    def setup(self, stream):
        self.stream = stream
        log.debug('setting up MUC invite message handler')
        stream.set_message_handler('normal', self.handle_message,
                              namespace = MUC_USER_NS,
                              priority = 99)

    def handle_message(self, stanza):
        '''
        <message
            from='darkcave@chat.shakespeare.lit'
            to='hecate@shakespeare.lit'>
          <x xmlns='http://jabber.org/protocol/muc#user'>
            <invite from='crone1@shakespeare.lit/desktop'>
              <reason>
                Hey Hecate, this is the place for all good witches!
              </reason>
            </invite>
            <password>cauldronburn</password>
          </x>
        </message>
        '''
        self.stanza = stanza
        try:
            roomjid = JID(stanza.get_from())
            roomname = roomjid.node
        except Exception:
            traceback.print_exc()
            return False
        else:
            if not roomname:
                return False
        for invite in stanza.xpath_eval('user:x/user:invite',
                                        {'user':MUC_USER_NS}):
            frm = invite.prop('from')
            if not frm:
                continue
            try:
                frm = JID(from_utf8(frm))
            except Exception:
                continue
            else:
                break
        else:
            return False

        reason = None
        for rsn in xpath_eval(invite, 'user:reason/text()',
                              {'user':MUC_USER_NS}):
            if rsn:
                reason = reason
        reason = reason or ''
        self.protocol.hub.on_invite(protocol = self.protocol,
               buddy = frm,
               room_name = roomname,
               message = reason,
               on_yes = lambda: self.protocol.join_chat_jid(roomjid,
                                    self.protocol.self_buddy.jid.node))
        return True
