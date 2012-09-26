""" Conversation class for MySpaceIM

    Nothing special here except for 'zap' functionality - a zap is an action that can be sent from one user to another.
    """
import logging
import common
import util.callbacks as callbacks
log = logging.getLogger('msim.conversation')


class Zap(object):

    @property
    def name(self):
        raise NotImplementedError

    def received(self, from_who):
        raise NotImplementedError

    def sent(self, to_who):
        raise NotImplementedError

    def nice_name(self):
        raise NotImplementedError


class BasicZap(Zap):

    name = None

    def received(self, from_who):
        return self.recv_msg.format(name=from_who)

    def sent(self, to_who):
        return self.sent_msg.format(name=to_who)

    def nice_name(self):
        return self.nice_name


class ZapZap(BasicZap):

    name = u'zap'
    recv_msg = _(u'{name} zapped you')
    sent_msg = _(u'You zapped {name}')
    nice_name = _(u'Zap')


class ZapWhack(BasicZap):

    name = u'whack'
    recv_msg = _(u'{name} whacked you')
    sent_msg = _(u'You whacked {name}')
    nice_name = _(u'Whack')


class ZapTorch(BasicZap):

    name = u'torch'
    recv_msg = _(u'{name} torched you')
    sent_msg = _(u'You torched {name}')
    nice_name = _(u'Torch')


class ZapSmooch(BasicZap):

    name = u'smooch'
    recv_msg = _(u'{name} smooched you')
    sent_msg = _(u'You smooched {name}')
    nice_name = _(u'Smooch')


class ZapSlap(BasicZap):

    name = u'bslap'
    recv_msg = _(u'{name} slapped you')
    sent_msg = _(u'You slapped {name}')
    nice_name = _(u'Slap')


class ZapGoose(BasicZap):

    name = u'goose'
    recv_msg = _(u'{name} goosed you')
    sent_msg = _(u'You goosed {name}')
    nice_name = _(u'Goose')


class ZapHiFive(BasicZap):

    name = u'hi-five'
    recv_msg = _(u'{name} high-fived you')
    sent_msg = _(u'You high-fived {name}')
    nice_name = _(u'High-Five')


class ZapPunk(BasicZap):

    name = u'punk\'d'
    recv_msg = _(u'{name} punk\'d you')
    sent_msg = _(u'You punk\'d {name}')
    nice_name = _(u'Punk')


class ZapRaspberry(BasicZap):

    name = u'raspberry'
    recv_msg = _(u'{name} raspberry\'d you')
    sent_msg = _(u'You raspberry\'d {name}')
    nice_name = _(u'Raspberry')

AllZapTypes = [
               ZapZap,
               ZapWhack,
               ZapTorch,
               ZapSmooch,
               ZapSlap,
               ZapGoose,
               ZapHiFive,
               ZapPunk,
               ZapRaspberry,
               ]

_zaps = dict((z.name, z) for z in (Z() for Z in AllZapTypes))


def zap_sent_text(zapname, to_who):
    z = _zaps.get(zapname)
    if z is None:
        return u''
    else:
        return z.sent(to_who)


def zap_received_text(zapname, from_who):
    z = _zaps.get(zapname)
    if z is None:
        return u''
    else:
        return z.received(from_who)


class MSIMConversation(common.Conversation):

    ischat = False

    def __init__(self, protocol, contact_id):
        common.Conversation.__init__(self, protocol)
        self.contact_id = contact_id
        self.buddy_join(self.contact)

    def __repr__(self):
        return '<%s for contact %r>' % (type(self).__name__, self.contact_id)

    @property
    def self_buddy(self):
        return self.protocol.self_buddy

    @property
    def contact(self):
        return self.protocol.get_buddy(self.contact_id)

    @property
    def buddy(self):
        return self.contact

    @property
    def name(self):
        return self.buddy.alias

    def send_typing_status(self, status):
        self.protocol.send_typing(who=self.buddy.id, typing=status == 'typing')

    def received_typing(self, buddy, typing):
        self.typing_status[buddy] = ('typing' if typing else None)

    @callbacks.callsback
    def _send_message(self, message, callback=None, **k):

        self.protocol.send_message(self.contact, message.format_as('msim'), callback=callback, **k)

    def buddy_join(self, buddy):
        self.room_list.append(buddy)
        self.typing_status[buddy] = None

    def received_group_message(self, group_id, actor_id, msg_text):

        self.ischat = True
        self.group_id = group_id
        if actor_id is None:
            self.process_system_message(msg_text)
        else:
            buddy = self.protocol.get_buddy(actor_id)
            if buddy is None:
                buddy = self.buddy
            log.info('Group message from %r', buddy)
            self.received_message(buddy, msg_text)

    def process_system_message(self, text):
        log.info('Got chat system message: %r', text)

    def received_message(self, buddy, message):
        if isinstance(message, bytes):
            message = message.decode('utf8')
        common.Conversation.received_message(self, buddy, message, content_type='text/html')
        self.typing_status[buddy] = None

    def received_zap(self, buddy, zaptxt):
        self.system_message(zap_received_text(zaptxt, buddy.alias))

    def exit(self):
        if getattr(self, 'ischat', False):
            self.protocol.send_exitchat(self.contact_id, self.group_id)
        common.Conversation.exit(self)
